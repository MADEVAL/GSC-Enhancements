# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-24

### Added

- Offline analyzer for Google Search Console Performance exports (CSV and tab-separated).
- `analyze` mode: upside-based queue entry (at least 3 clicks), striking-distance band, snippet gap detection,
  estimated click gain, effort per action, ROI ordering by clicks per hour.
- `cannibalization` mode: owner selection per query with retarget and redirect actions, hard refusal on exports without pages.
- `verify` mode: before and after comparison with improved, declined, flat, too early and no data verdicts.
- Limits reporting: rows read, missing position, anonymized gap against totals, inconsistent totals detection.
- Sample coverage from a sibling country, device or chart export, with a warning below 50 percent of site clicks.
- Input tolerance: UTF-8 with or without BOM, comma, semicolon and tab delimiters, preamble lines,
  US and European number formats, percent and decimal CTR.
- Brand filter via `--brand`, custom CTR curve via `--curve`.
- CTR calibration to the export itself (`ctr_calibration` in JSON, `--no-calibration` to disable).
- Localized headers: Russian and Ukrainian exports are accepted as the interface produces them.
- References: export format, GSC limits, CTR curve, cannibalization tree, verification protocol.
- Validator with a deliberately broken fixture, 20 unit tests, installer round-trip tests and CI with ruff.

### Known gaps

- Decay detection across two periods is described in `docs/SPEC.md` but not implemented yet.
- BigQuery export input is not parsed yet; only CSV and tab-separated files.
- Live Search Console API is not part of this skill; `seo-google` owns that handoff.
