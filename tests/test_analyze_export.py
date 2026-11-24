#!/usr/bin/env python3
"""Behaviour tests for the offline analyzer."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "gsc-enhancements" / "scripts" / "analyze_export.py"
FIXTURES = ROOT / "tests" / "fixtures"


def run(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        cwd=ROOT,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


def run_error(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        cwd=ROOT,
    )


def run_text(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        cwd=ROOT,
    )


class AnalyzeTests(unittest.TestCase):
    def test_analyze_returns_queue(self) -> None:
        data = run("analyze", "--input", str(FIXTURES / "queries.csv"), "--min-impressions", "100")
        self.assertEqual(data["mode"], "analyze")
        self.assertEqual(data["impression_floor"], 100)
        self.assertGreater(len(data["rows"]), 0)
        self.assertEqual(data["missing_position"], 0)
        actions = {row["action"] for row in data["rows"]}
        self.assertTrue(actions.issubset({"rewrite-snippet", "strengthen-page", "refresh"}))
        self.assertIn("rewrite-snippet", actions)
        self.assertTrue(all(row["upside"] is not None for row in data["rows"]))

    def test_analyze_excludes_top_positions(self) -> None:
        data = run("analyze", "--input", str(FIXTURES / "queries.csv"), "--min-impressions", "100")
        queries = {row["query"] for row in data["rows"]}
        self.assertNotIn("brand name", queries)

    def test_cannibalization_decides_owner(self) -> None:
        data = run(
            "cannibalization",
            "--input",
            str(FIXTURES / "query-page.csv"),
            "--min-impressions",
            "100",
        )
        self.assertEqual(data["mode"], "cannibalization")
        by_query = {row["query"]: row for row in data["rows"]}
        self.assertIn("gsc export limit", by_query)
        record = by_query["gsc export limit"]
        self.assertEqual(record["owner"], "/blog/gsc-limits")
        actions = {item["page"]: item["action"] for item in record["others"]}
        self.assertEqual(actions["/tools/export"], "redirect")
        self.assertEqual(actions["/docs/exports"], "retarget")

    def test_cannibalization_consolidates_close_pages(self) -> None:
        data = run(
            "cannibalization",
            "--input",
            str(FIXTURES / "query-page.csv"),
            "--min-impressions",
            "100",
        )
        by_query = {row["query"]: row for row in data["rows"]}
        record = by_query["seo audit checklist"]
        self.assertEqual(record["owner"], "/blog/seo-audit")
        self.assertEqual(record["others"][0]["action"], "consolidate")

    def test_verify_labels_improvement(self) -> None:
        data = run(
            "verify",
            "--before",
            str(FIXTURES / "before.csv"),
            "--after",
            str(FIXTURES / "after.csv"),
            "--weeks",
            "4",
        )
        verdicts = {row["page"]: row["verdict"] for row in data["rows"]}
        self.assertEqual(verdicts["/blog/seo-audit"], "improved")
        self.assertEqual(verdicts["/blog/technical-audit"], "improved")

    def test_verify_refuses_early_verdict(self) -> None:
        data = run(
            "verify",
            "--before",
            str(FIXTURES / "before.csv"),
            "--after",
            str(FIXTURES / "after.csv"),
            "--weeks",
            "2",
        )
        self.assertTrue(all(row["verdict"] == "too early" for row in data["rows"]))

    def test_tab_separated_input(self) -> None:
        data = run("analyze", "--input", str(FIXTURES / "queries.tsv"), "--min-impressions", "100")
        queries = {row["query"] for row in data["rows"]}
        self.assertIn("seo audit checklist", queries)

    def test_queue_is_ordered_by_clicks_per_hour(self) -> None:
        data = run("analyze", "--input", str(FIXTURES / "queries.csv"), "--min-impressions", "100")
        scores = [row["score"] for row in data["rows"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(data["rows"][0]["action"], "rewrite-snippet")

    def test_default_rule_uses_min_upside(self) -> None:
        data = run("analyze", "--input", str(FIXTURES / "queries.csv"))
        self.assertIsNone(data["impression_floor"])
        self.assertEqual(data["min_upside_clicks"], 3)
        self.assertIsNotNone(data["row_floor_range"])
        low, high = data["row_floor_range"]
        self.assertGreaterEqual(low, 10)
        self.assertLess(low, high)

    def test_brand_terms_are_excluded(self) -> None:
        data = run(
            "analyze",
            "--input",
            str(FIXTURES / "queries.csv"),
            "--min-impressions",
            "100",
            "--brand",
            "brand",
        )
        queries = {row["query"] for row in data["rows"]}
        self.assertNotIn("brand name", queries)
        self.assertEqual(data["brand_excluded"], ["brand"])

    def test_missing_position_is_reported(self) -> None:
        data = run(
            "analyze",
            "--input",
            str(FIXTURES / "no-position.csv"),
            "--min-impressions",
            "10",
        )
        self.assertEqual(data["missing_position"], 1)

    def test_missing_clicks_keeps_upside_unknown(self) -> None:
        data = run(
            "analyze",
            "--input",
            str(FIXTURES / "no-clicks.csv"),
            "--min-impressions",
            "10",
        )
        self.assertGreater(len(data["rows"]), 0)
        self.assertTrue(all(row["upside"] is None for row in data["rows"]))
        self.assertTrue(all(row["est_clicks"] is None for row in data["rows"]))

    def test_cannibalization_requires_query_and_page(self) -> None:
        result = run_error(
            "cannibalization",
            "--input",
            str(FIXTURES / "queries.csv"),
            "--min-impressions",
            "100",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("query+page", result.stderr)

    def test_non_export_file_is_rejected(self) -> None:
        result = run_error("analyze", "--input", str(ROOT / "README.md"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("README.md", result.stderr)
        self.assertTrue(
            "no header" in result.stderr or "no data rows" in result.stderr,
            result.stderr,
        )


    def test_european_format_and_preamble(self) -> None:
        data = run(
            "analyze",
            "--input",
            str(FIXTURES / "european.csv"),
            "--min-impressions",
            "100",
        )
        self.assertEqual(len(data["rows"]), 2)
        row = data["rows"][0]
        self.assertEqual(row["query"], "seo аудит")
        self.assertEqual(row["impressions"], 1840)
        self.assertEqual(row["position"], 9.4)
        self.assertEqual(data["anonymized_gap"], 0.0)
        self.assertFalse(data["totals_inconsistent"])

    def test_localized_headers_are_recognized(self) -> None:
        data = run(
            "analyze",
            "--input",
            str(FIXTURES / "ru-queries.csv"),
            "--min-impressions",
            "100",
        )
        self.assertEqual(data["rows_read"], 5)
        queries = {row["query"] for row in data["rows"]}
        self.assertNotIn("куда жаловаться на больницу горячая линия украина", queries)
        self.assertIn("як передати майно у спадок", queries)
        self.assertEqual(data["anonymized_gap"], 0.0)

    def test_coverage_uses_explicit_totals(self) -> None:
        data = run(
            "analyze",
            "--input",
            str(FIXTURES / "queries.csv"),
            "--min-impressions",
            "100",
            "--totals",
            str(FIXTURES / "coverage" / "totals.csv"),
        )
        coverage = data["coverage"]
        self.assertEqual(coverage["source"], "totals.csv")
        self.assertEqual(coverage["site_clicks"], 10000)
        self.assertEqual(coverage["site_impressions"], 100000)
        self.assertAlmostEqual(coverage["clicks_pct"], 8.3, places=1)
        self.assertIn("warning", coverage)

    def test_coverage_is_discovered_next_to_input(self) -> None:
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            shutil.copy(FIXTURES / "queries.csv", workdir / "queries.csv")
            shutil.copy(FIXTURES / "coverage" / "totals.csv", workdir / "totals.csv")
            data = run(
                "analyze",
                "--input",
                str(workdir / "queries.csv"),
                "--min-impressions",
                "100",
            )
            self.assertEqual(data["coverage"]["source"], "totals.csv")
            self.assertAlmostEqual(data["coverage"]["clicks_pct"], 8.3, places=1)

    def test_text_output_renders_for_every_mode(self) -> None:
        cases = [
            (("analyze", "--input", str(FIXTURES / "queries.csv"), "--min-impressions", "100"), "Priority"),
            (("cannibalization", "--input", str(FIXTURES / "query-page.csv"), "--min-impressions", "100"), "Owner"),
            (
                ("verify", "--before", str(FIXTURES / "before.csv"), "--after", str(FIXTURES / "after.csv")),
                "Verdict",
            ),
        ]
        for args, marker in cases:
            result = run_text(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(marker, result.stdout)


if __name__ == "__main__":
    unittest.main()
