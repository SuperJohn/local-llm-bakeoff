# Demo data (Local LLM bake-off)

Public-safe metrics from the HOU-90 bake-off runs, plus clearly labelled **synthetic** per-trial records for demo charts.
No raw model replies, API keys or private paths. Prompts and tool fixtures are the fictional planner/calendar suite in
`configs/suites/`; vision images are public Wikimedia Commons files.

| File | Provenance | What it is | Rows |
|---|---|---|---|
| `summary.json` | measured | Medians and agent scores (unchanged). Pages-served copy: `site/data/summary.json`. | 4 runs + legacy |
| `tasks.json` | config | Suite catalog: 30 agent tasks (expected tools, call counts), 10 voice prompts, 2 vision images, 5 tool definitions. | 42 tasks |
| `models.json` | measured | Pinned models from `results/runs` (tag, digest prefix, capabilities, think levels). | 4 |
| `measured_items.json` | measured | Per-item rows flattened from `results/runs` + `results/legacy` (latency, TTFT, tok/s, tool selected / args correct / task complete / valid JSON, tools called). | 419 |
| `synthetic_trials.json` | **synthetic** | 5 repeat trials per item sampled around the measured medians: latency, TTFT, tokens in/out, tok/s, pass/fail. For variance bands and per-trial charts only; **not benchmark results**. | 1,130 |
| `synthetic_rollup.json` | **synthetic** | p50/p95 and pass rate over `synthetic_trials.json` only. | 13 |
| `manifest.json` | | Row counts, byte sizes and sha256. | |

Every synthetic row carries `"provenance": "synthetic"`. Real numbers live only in `summary.json`, `measured_items.json`,
`RESULTS.md` and `results/`.

Regenerate (seeded, byte-identical): `python3 demo/generate_data.py` (needs `pyyaml`). It never touches `summary.json` or `site/`.

**Local override.** On the Studio, point tooling at a fresh local run with `HL_DATASET_URI`
(e.g. `HL_DATASET_URI=file://…/demo/data/summary.json`); full runs stay local.

Charts under `site/assets/` are generated from the same runs.
