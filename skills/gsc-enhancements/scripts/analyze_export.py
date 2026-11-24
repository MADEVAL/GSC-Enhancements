#!/usr/bin/env python3
"""Offline analysis of Google Search Console Performance exports.

Stdlib only. Reads CSV or tab-separated files, never touches the network.

Modes:
    analyze          rank striking-distance queries and snippet gaps
    cannibalization  find queries shared by several pages and decide an owner
    verify           compare a before and after export for the same rows

Examples:
    python scripts/analyze_export.py analyze --input queries.csv
    python scripts/analyze_export.py cannibalization --input query-page.tsv --json
    python scripts/analyze_export.py verify --before before.csv --after after.csv
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import sys
from pathlib import Path

CTR_CURVE = {
    1: 0.28,
    2: 0.15,
    3: 0.11,
    4: 0.08,
    5: 0.06,
    6: 0.045,
    7: 0.035,
    8: 0.028,
    9: 0.024,
    10: 0.02,
    11: 0.01,
}
CTR_FLOOR_POSITION = 0.005

HEADER_ALIASES = {
    "query": {
        "query",
        "queries",
        "top queries",
        "search query",
        "популярные запросы",
        "запросы",
        "поисковый запрос",
        "популярні запити",
        "запити",
    },
    "page": {
        "page",
        "pages",
        "top pages",
        "landing page",
        "url",
        "популярные страницы",
        "страницы",
        "целевая страница",
        "популярні сторінки",
        "сторінки",
    },
    "clicks": {"clicks", "click", "клики", "kлики", "кліки"},
    "impressions": {"impressions", "impression", "показы", "покази"},
    "ctr": {"ctr", "click through rate", "click-through rate", "кликабельность"},
    "position": {
        "position",
        "average position",
        "avg position",
        "позиция",
        "средняя позиция",
        "позиція",
        "середня позиція",
    },
}
TOTAL_LABELS = {"total", "totals", "sum", "filtered", "summary"}
MIN_UPSIDE_CLICKS = 3

EFFORT = {
    "rewrite-snippet": "30 min",
    "strengthen-page": "2 h",
    "consolidate": "1 h",
    "refresh": "2 h",
    "retarget": "2 h",
    "redirect": "30 min",
}
EFFORT_HOURS = {
    "rewrite-snippet": 0.5,
    "strengthen-page": 2.0,
    "consolidate": 1.0,
    "refresh": 2.0,
    "retarget": 2.0,
    "redirect": 0.5,
}


class ExportError(Exception):
    """Raised when a file cannot be read as a Search Console export."""


def read_text(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise ExportError(f"file not found: {path}") from exc
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExportError(f"{path.name}: not UTF-8, re-export the file") from exc


def detect_delimiter(text: str) -> str:
    candidates = ("\t", ";", ",")
    for line in text.splitlines()[:30]:
        if not line.strip():
            continue
        for delimiter in candidates:
            cells = {normalize_header(item) for item in line.split(delimiter)}
            has_impressions = "impressions" in cells or "impression" in cells
            has_dimension = bool(
                cells
                & {"query", "queries", "top queries", "search query", "page", "pages", "top pages", "landing page", "url"}
            )
            if has_impressions and has_dimension:
                return delimiter
    sample = "\n".join(line for line in text.splitlines()[:20] if line.strip())
    tabs = sample.count("\t")
    commas = sample.count(",")
    semicolons = sample.count(";")
    if tabs >= commas and tabs >= semicolons and tabs > 0:
        return "\t"
    if semicolons > commas:
        return ";"
    return ","


def normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip('"').lower())


def map_headers(row: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, cell in enumerate(row):
        name = normalize_header(cell)
        for key, aliases in HEADER_ALIASES.items():
            if name in aliases and key not in mapping:
                mapping[key] = index
    return mapping


def parse_number(value: str, *, percent: bool = False, integer: bool = False) -> float | None:
    text = (value or "").strip().strip('"').replace("\u00a0", " ").replace(" ", "")
    if text in {"", "-", "~", "n/a", "N/A"}:
        return None
    had_percent = text.endswith("%")
    if had_percent:
        text = text[:-1]
    text = text.replace("'", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        parts = text.split(",")
        if len(parts) == 2 and 1 <= len(parts[1]) <= 2:
            text = text.replace(",", ".")
        elif integer:
            text = text.replace(",", "")
        else:
            text = text.replace(",", ".")
    elif "." in text and integer and re.fullmatch(r"\d{1,3}(\.\d{3})+", text):
        text = text.replace(".", "")
    try:
        number = float(text)
    except ValueError:
        return None
    if had_percent:
        return number / 100
    if percent and number > 1:
        return number / 100
    return number


def cell(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def load_export(path: Path) -> tuple[list[dict], dict | None]:
    text = read_text(path)
    delimiter = detect_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        raise ExportError(f"{path.name}: empty file")

    header_index = None
    mapping: dict[str, int] = {}
    for index, row in enumerate(rows):
        candidate = map_headers(row)
        if "impressions" in candidate and ("query" in candidate or "page" in candidate):
            header_index, mapping = index, candidate
            break
    if header_index is None:
        raise ExportError(
            f"{path.name}: no header with impressions and query or page columns"
        )

    records: list[dict] = []
    totals: dict | None = None
    for row in rows[header_index + 1 :]:
        if not any(cell.strip() for cell in row):
            continue
        first = row[0].strip().lower() if row else ""
        if first in TOTAL_LABELS:
            totals = {
                "clicks": parse_number(cell(row, mapping.get("clicks")), integer=True),
                "impressions": parse_number(
                    cell(row, mapping.get("impressions")), integer=True
                ),
            }
            continue
        clicks = parse_number(cell(row, mapping.get("clicks")), integer=True)
        if clicks is not None:
            clicks = round(clicks)
        record = {
            "query": cell(row, mapping.get("query")),
            "page": cell(row, mapping.get("page")),
            "clicks": clicks,
            "impressions": parse_number(
                cell(row, mapping.get("impressions")), integer=True
            ),
            "ctr": parse_number(cell(row, mapping.get("ctr")), percent=True),
            "position": parse_number(cell(row, mapping.get("position"))),
        }
        if not record["query"] and not record["page"]:
            continue
        if record["impressions"] is None:
            continue
        if record["position"] == 0.0:
            record["position"] = None
        records.append(record)

    if not records:
        raise ExportError(f"{path.name}: no data rows found")
    return records, totals


def load_curve(path: Path | None) -> dict[int, float]:
    if path is None:
        return dict(CTR_CURVE)
    text = read_text(path)
    curve: dict[int, float] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith(("position", "#")):
            continue
        parts = re.split(r"[,;\t]", line)
        if len(parts) < 2:
            continue
        position = parse_number(parts[0])
        ctr = parse_number(parts[1], percent=True)
        if position is not None and ctr is not None:
            curve[int(position)] = ctr
    if not curve:
        raise ExportError(f"{path.name}: no curve rows found")
    return curve


def curve_value(position: float | None, curve: dict[int, float]) -> float | None:
    if position is None:
        return None
    key = min(max(round(position), 1), 20)
    return curve.get(key, CTR_FLOOR_POSITION)


def calibrate(records: list[dict], curve: dict[int, float]) -> dict | None:
    """Scale the generic curve to the observed CTR of this export.

    A site that earns 1.5 percent CTR while the generic curve predicts 3 percent
    at its average position is not full of broken snippets; it is a low-CTR site.
    Without calibration every row is flagged and the queue stops discriminating.
    """
    clicks = 0.0
    impressions = 0.0
    weighted = 0.0
    positioned = 0.0
    for record in records:
        if record["clicks"] is None or record["position"] is None:
            continue
        if not record["impressions"]:
            continue
        clicks += record["clicks"]
        impressions += record["impressions"]
        weighted += record["position"] * record["impressions"]
        positioned += record["impressions"]
    if impressions <= 0 or positioned <= 0 or clicks <= 0:
        return None
    observed = clicks / impressions
    average_position = weighted / positioned
    expected = curve_value(average_position, curve)
    if not expected:
        return None
    factor = min(1.5, max(0.25, observed / expected))
    return {
        "factor": round(factor, 3),
        "observed_ctr": round(observed, 4),
        "expected_ctr": round(expected, 4),
        "average_position": round(average_position, 2),
    }


def scaled_curve(curve: dict[int, float], factor: float | None) -> dict[int, float]:
    if not factor:
        return curve
    return {position: value * factor for position, value in curve.items()}


def row_floor(position: float | None, curve: dict[int, float]) -> int:
    """Impressions needed for the row to be able to yield MIN_UPSIDE_CLICKS.

    A query at position 18 can only gain a few clicks per thousand impressions,
    so the floor rises with the distance from the target position. This keeps
    the queue free of rows where no realistic edit can produce measurable change.
    """
    if position is None:
        return 10
    target = max(3, round(position) - 3)
    expected = curve_value(target, curve) or CTR_FLOOR_POSITION
    return max(10, math.ceil(MIN_UPSIDE_CLICKS / expected))


def action_for(record: dict, curve: dict[int, float]) -> str:
    position = record["position"]
    if position is None:
        return "unknown"
    observed = record["ctr"]
    expected = curve_value(position, curve)
    if position <= 10 and observed is not None and expected and observed < 0.6 * expected:
        return "rewrite-snippet"
    if position >= 11:
        return "strengthen-page"
    return "refresh"


def brand_terms(value: str | None) -> list[str]:
    if not value:
        return []
    return [term.strip().casefold() for term in value.split(",") if term.strip()]


def is_brand(record: dict, terms: list[str]) -> bool:
    if not terms:
        return False
    query = record["query"].casefold()
    return any(term in query for term in terms)


def analyze(records: list[dict], args, curve: dict[int, float]) -> dict:
    terms = brand_terms(args.brand)
    calibration = None if args.no_calibration else calibrate(records, curve)
    effective = scaled_curve(curve, calibration["factor"] if calibration else None)
    candidates = []
    floors: list[int] = []
    for record in records:
        if is_brand(record, terms):
            continue
        position = record["position"]
        if position is None:
            continue
        if not (args.min_position <= position <= args.max_position):
            continue
        floor = (
            args.min_impressions
            if args.min_impressions is not None
            else row_floor(position, effective)
        )
        floors.append(floor)
        if record["impressions"] < floor:
            continue
        target = max(3, round(position) - 3)
        expected = curve_value(target, effective) or CTR_FLOOR_POSITION
        clicks = record["clicks"]
        estimate = None
        upside = None
        if clicks is not None:
            estimate = round(record["impressions"] * expected, 1)
            upside = round(max(0.0, estimate - clicks), 1)
        action = action_for(record, effective)
        score = None
        if upside is not None:
            score = round(upside / EFFORT_HOURS.get(action, 1.0), 1)
        candidates.append(
            {
                "action": action,
                "query": record["query"],
                "page": record["page"],
                "impressions": int(record["impressions"]),
                "clicks": clicks,
                "ctr": record["ctr"],
                "position": round(position, 1),
                "target_position": target,
                "est_clicks": estimate,
                "upside": upside,
                "score": score,
                "effort": EFFORT.get(action, "unknown"),
            }
        )

    candidates.sort(
        key=lambda item: (
            item["score"] is None,
            -(item["score"] or 0),
            -(item["upside"] or 0),
            -item["impressions"],
        )
    )
    for priority, item in enumerate(candidates[: args.limit], start=1):
        item["priority"] = priority
    return {
        "mode": "analyze",
        "impression_floor": args.min_impressions,
        "min_upside_clicks": None if args.min_impressions is not None else MIN_UPSIDE_CLICKS,
        "row_floor_range": [min(floors), max(floors)] if floors else None,
        "brand_excluded": terms,
        "ctr_calibration": calibration,
        "rows": candidates[: args.limit],
        "rows_matched": len(candidates),
    }


def cannibalization(records: list[dict], args, curve: dict[int, float]) -> dict:
    terms = brand_terms(args.brand)
    grouped: dict[str, list[dict]] = {}
    for record in records:
        if not record["query"] or not record["page"]:
            continue
        if is_brand(record, terms):
            continue
        grouped.setdefault(record["query"], []).append(record)

    decisions = []
    floors: list[int] = []
    for query, pages in grouped.items():
        unique = {}
        for record in pages:
            key = record["page"]
            current = unique.get(key)
            if current is None or record["impressions"] > current["impressions"]:
                unique[key] = record
        if len(unique) < 2:
            continue
        total = sum(item["impressions"] for item in unique.values())
        ranked = sorted(unique.values(), key=lambda item: (-item["impressions"], item["page"]))
        owner = ranked[0]
        floor = (
            args.min_impressions
            if args.min_impressions is not None
            else row_floor(owner["position"], curve)
        )
        floors.append(floor)
        if total < floor:
            continue
        others = []
        for record in ranked[1:]:
            share = record["impressions"] / total if total else 0
            if share < 0.1:
                action = "redirect"
            elif share >= 0.4:
                action = "consolidate"
            else:
                action = "retarget"
            others.append(
                {
                    "page": record["page"],
                    "impressions": int(record["impressions"]),
                    "share": round(share, 3),
                    "action": action,
                }
            )
        decisions.append(
            {
                "query": query,
                "owner": owner["page"],
                "owner_impressions": int(owner["impressions"]),
                "total_impressions": int(total),
                "pages": len(unique),
                "others": others,
            }
        )

    decisions.sort(key=lambda item: -item["total_impressions"])
    return {
        "mode": "cannibalization",
        "impression_floor": args.min_impressions,
        "min_upside_clicks": None if args.min_impressions is not None else MIN_UPSIDE_CLICKS,
        "row_floor_range": [min(floors), max(floors)] if floors else None,
        "brand_excluded": terms,
        "rows": decisions[: args.limit],
        "rows_matched": len(decisions),
    }


def index_key(record: dict) -> tuple[str, str]:
    return (record["query"], record["page"])


def verify(before: list[dict], after: list[dict], args) -> dict:
    before_map = {index_key(row): row for row in before if row["query"] or row["page"]}
    after_map = {index_key(row): row for row in after if row["query"] or row["page"]}
    pairs = []
    for key in sorted(set(before_map) & set(after_map)):
        old, new = before_map[key], after_map[key]
        old_clicks = old["clicks"] or 0
        new_clicks = new["clicks"] or 0
        delta = new_clicks - old_clicks
        if args.weeks < 4:
            verdict = "too early"
        elif old_clicks == 0 and new_clicks == 0:
            verdict = "no data"
        elif delta >= 5 and (delta / max(old_clicks, 1)) >= 0.2:
            verdict = "improved"
        elif delta <= -5 and (delta / max(old_clicks, 1)) <= -0.2:
            verdict = "declined"
        else:
            verdict = "flat"
        pairs.append(
            {
                "query": key[0],
                "page": key[1],
                "before_clicks": old_clicks,
                "after_clicks": new_clicks,
                "delta_clicks": delta,
                "before_impressions": old["impressions"],
                "after_impressions": new["impressions"],
                "verdict": verdict,
            }
        )
    pairs.sort(key=lambda item: -abs(item["delta_clicks"]))
    return {
        "mode": "verify",
        "weeks": args.weeks,
        "rows": pairs[: args.limit],
        "rows_matched": len(pairs),
    }


def stats_block(records: list[dict], totals: dict | None) -> dict:
    missing_position = sum(1 for row in records if row["position"] is None)
    gap = None
    inconsistent = False
    if totals and totals.get("impressions"):
        visible = sum(row["impressions"] for row in records)
        if totals["impressions"] > 0:
            if visible > totals["impressions"]:
                inconsistent = True
            else:
                gap = round(1 - visible / totals["impressions"], 4)
    return {
        "rows_read": len(records),
        "missing_position": missing_position,
        "anonymized_gap": gap,
        "totals_inconsistent": inconsistent,
    }


def render_table(rows: list[dict], mode: str) -> str:
    if not rows:
        return "No rows matched the filters. Report why instead of lowering every threshold."
    if mode == "analyze":
        header = (
            "| Priority | Action | Query | Page | Impressions | Position | Est. gain | Effort |\n"
            "|---|---|---|---|---|---|---|---|"
        )
        body = []
        for row in rows:
            gain = row["upside"] if row["upside"] is not None else "unknown"
            body.append(
                f"| {row['priority']} | {row['action']} | {row['query'] or '-'} | "
                f"{row['page'] or '-'} | {row['impressions']} | {row['position']} | "
                f"{gain} | {row['effort']} |"
            )
        return "\n".join([header, *body])
    if mode == "cannibalization":
        header = "| Query | Owner | Other pages and actions | Total impressions |\n|---|---|---|---|"
        body = []
        for row in rows:
            others = ", ".join(f"{item['page']} ({item['action']})" for item in row["others"])
            body.append(
                f"| {row['query']} | {row['owner']} | {others} | {row['total_impressions']} |"
            )
        return "\n".join([header, *body])
    header = (
        "| Query | Page | Before | After | Delta | Verdict |\n"
        "|---|---|---|---|---|---|"
    )
    body = [
        f"| {row['query'] or '-'} | {row['page'] or '-'} | {row['before_clicks']} | "
        f"{row['after_clicks']} | {row['delta_clicks']:+d} | {row['verdict']} |"
        for row in rows
    ]
    return "\n".join([header, *body])


def find_header_index(rows: list[list[str]]) -> tuple[int, dict[str, int]] | None:
    for index, row in enumerate(rows):
        mapping = map_headers(row)
        if "impressions" in mapping and "clicks" in mapping:
            return index, mapping
    return None


def load_totals(path: Path) -> dict:
    """Read any dimension export and return site totals.

    Country, device and chart exports all sum to the same site totals. Files with
    query or page columns are rejected: they are samples, not totals.
    """
    text = read_text(path)
    delimiter = detect_delimiter(text)
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    header = find_header_index(rows)
    if header is None:
        raise ExportError(f"{path.name}: no clicks and impressions columns")
    header_index, mapping = header
    if "query" in mapping or "page" in mapping:
        raise ExportError(f"{path.name}: has query or page columns, not a totals file")

    summed_clicks = 0.0
    summed_impressions = 0.0
    total_row = None
    for row in rows[header_index + 1 :]:
        if not any(value.strip() for value in row):
            continue
        first = row[0].strip().lower() if row else ""
        clicks = parse_number(cell(row, mapping.get("clicks")), integer=True)
        impressions = parse_number(cell(row, mapping.get("impressions")), integer=True)
        if first in TOTAL_LABELS:
            total_row = (clicks, impressions)
            continue
        if clicks is None or impressions is None:
            continue
        summed_clicks += clicks
        summed_impressions += impressions

    if total_row and total_row[1]:
        clicks, impressions = total_row
    else:
        clicks, impressions = summed_clicks, summed_impressions
    if not impressions:
        raise ExportError(f"{path.name}: totals are zero or unreadable")
    return {
        "clicks": int(clicks or 0),
        "impressions": int(impressions),
        "source": path.name,
    }


def discover_totals(input_path: Path, totals_arg: Path | None) -> dict | None:
    if totals_arg is not None:
        return load_totals(totals_arg)
    best = None
    for candidate in sorted(input_path.parent.iterdir()):
        if not candidate.is_file():
            continue
        if candidate.suffix.lower() not in {".csv", ".tsv", ".txt"}:
            continue
        if candidate.resolve() == input_path.resolve():
            continue
        try:
            totals = load_totals(candidate)
        except ExportError:
            continue
        if best is None or totals["impressions"] > best["impressions"]:
            best = totals
    return best


def attach_coverage(result: dict, records: list[dict], totals: dict | None) -> None:
    if not totals:
        return
    sample_clicks = sum(row["clicks"] for row in records if row["clicks"] is not None)
    sample_impressions = sum(row["impressions"] for row in records)
    if not totals["impressions"]:
        return
    clicks_pct = round(100 * sample_clicks / max(totals["clicks"], 1), 1)
    impressions_pct = round(100 * sample_impressions / totals["impressions"], 1)
    coverage = {
        "clicks_pct": clicks_pct,
        "impressions_pct": impressions_pct,
        "source": totals["source"],
        "site_clicks": totals["clicks"],
        "site_impressions": totals["impressions"],
    }
    if clicks_pct < 50:
        coverage["warning"] = "sample covers less than half of site clicks"
    result["coverage"] = coverage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze Google Search Console Performance exports offline."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    def common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--limit", type=int, default=10, help="Rows in the queue (default 10).")
        sub.add_argument("--min-impressions", type=int, default=None, help="Override the adaptive floor.")
        sub.add_argument("--json", action="store_true", help="Machine-readable output.")
        sub.add_argument("--curve", type=Path, default=None, help="CSV with position,ctr overrides.")
        sub.add_argument(
            "--totals",
            type=Path,
            default=None,
            help="Country, device or chart export used to compute sample coverage.",
        )
        sub.add_argument(
            "--brand",
            default=None,
            help="Comma-separated brand terms to exclude, for example 'acme,acme inc'.",
        )

    analyze_parser = subparsers.add_parser("analyze", help="Rank opportunities.")
    analyze_parser.add_argument("--input", type=Path, required=True)
    analyze_parser.add_argument("--min-position", type=float, default=4.0)
    analyze_parser.add_argument("--max-position", type=float, default=20.0)
    analyze_parser.add_argument(
        "--no-calibration",
        action="store_true",
        help="Use the generic CTR curve as is, without scaling it to this export.",
    )
    common(analyze_parser)

    cannibal_parser = subparsers.add_parser("cannibalization", help="Decide query owners.")
    cannibal_parser.add_argument("--input", type=Path, required=True)
    common(cannibal_parser)

    verify_parser = subparsers.add_parser("verify", help="Compare before and after exports.")
    verify_parser.add_argument("--before", type=Path, required=True)
    verify_parser.add_argument("--after", type=Path, required=True)
    verify_parser.add_argument("--weeks", type=float, default=4.0)
    common(verify_parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        if args.mode == "analyze":
            records, totals = load_export(args.input)
            result = analyze(records, args, load_curve(args.curve))
            result["input"] = str(args.input)
        elif args.mode == "cannibalization":
            records, totals = load_export(args.input)
            if not any(row["query"] for row in records) or not any(
                row["page"] for row in records
            ):
                raise ExportError(
                    "cannibalization needs a query+page export: the Performance UI "
                    "exports one dimension at a time. Combine query and page with the "
                    "Search Console API (dimensions query,page), BigQuery bulk export, "
                    "or let seo-google pull it."
                )
            result = cannibalization(records, args, load_curve(args.curve))
            result["input"] = str(args.input)
        else:
            before, totals = load_export(args.before)
            after, _ = load_export(args.after)
            result = verify(before, after, args)
            result["input"] = f"{args.before} -> {args.after}"
            records = before
        result.update(stats_block(records, totals))
        if args.mode != "verify":
            try:
                site_totals = discover_totals(args.input, args.totals)
            except ExportError as exc:
                print(f"warning: {exc}", file=sys.stderr)
                site_totals = None
            attach_coverage(result, records, site_totals)
    except ExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"GSC Enhancements: {args.mode}")
    print(f"File: {result['input']}")
    if args.mode == "verify":
        filter_text = "filter: matched query and page pairs only"
    elif result.get("impression_floor") is not None:
        filter_text = f"impressions >= {result['impression_floor']}"
    else:
        filter_text = f"min upside {result.get('min_upside_clicks')} clicks per row"
    print(
        f"Rows read: {result['rows_read']} | {filter_text} "
        f"| missing position: {result['missing_position']}"
    )
    if result["anonymized_gap"] is not None:
        print(f"Anonymized gap: {result['anonymized_gap'] * 100:.1f}% of impressions")
    calibration = result.get("ctr_calibration")
    if calibration:
        observed = calibration["observed_ctr"] * 100
        expected = calibration["expected_ctr"] * 100
        print(
            f"CTR calibration: x{calibration['factor']} (observed {observed:.2f}% vs "
            f"expected {expected:.2f}% at position {calibration['average_position']})"
        )
    coverage = result.get("coverage")
    if coverage:
        print(
            f"Sample coverage: {coverage['clicks_pct']}% of clicks, "
            f"{coverage['impressions_pct']}% of impressions "
            f"(site totals from {coverage['source']})"
        )
        if coverage.get("warning"):
            print(f"Warning: {coverage['warning']}; treat the queue as a sample.")
    print()
    print(render_table(result["rows"], args.mode))
    print()
    if args.mode == "analyze":
        print("Est. gain = estimated clicks at the target position minus current clicks.")
        print("All gains use the illustrative CTR curve; label them as estimates.")
        print("Queue is sorted by estimated clicks per hour of effort.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
