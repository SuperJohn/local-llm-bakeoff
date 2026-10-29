#!/usr/bin/env python3
"""Generate the Local LLM bake-off demo dataset under demo/data (seeded, deterministic).

- tasks.json / models.json: suite catalog and pinned models, read from configs/ and results/.
- measured_items.json: per-item rows flattened from the committed results/ files (real runs; replies dropped).
- synthetic_trials.json / synthetic_rollup.json: SYNTHETIC repeat trials sampled around the measured medians,
  labelled provenance=synthetic. They are for demo charts only and are not benchmark results.

    python3 demo/generate_data.py      # needs pyyaml (requirements.txt); never touches summary.json or site/
"""
import hashlib, json
from pathlib import Path


def _enc(o, level=0):
    """Pretty JSON where arrays of objects/arrays put one compact record per line (small, diff-friendly)."""
    pad, pad1 = " " * level, " " * (level + 1)
    if isinstance(o, dict):
        if not o:
            return "{}"
        items = [f'{pad1}{json.dumps(k, ensure_ascii=False)}: {_enc(v, level + 1)}' for k, v in o.items()]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(o, list) and o and all(isinstance(x, (dict, list)) for x in o):
        rows = [pad1 + json.dumps(x, ensure_ascii=False, separators=(", ", ": ")) for x in o]
        return "[\n" + ",\n".join(rows) + "\n" + pad + "]"
    return json.dumps(o, ensure_ascii=False)


def write(path: Path, obj) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _enc(obj) + "\n"
    json.loads(text)  # must round-trip
    path.write_text(text, encoding="utf-8")
    b = text.encode()
    return {"name": path.name, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
# ---------------------------------------------------------------------------------------------------------------
import argparse
import glob
import random
import statistics as st

import yaml

ROOT = Path(__file__).resolve().parents[1]
SEED = 42
TRIALS = 5
SYN_DATES = ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"]
VOICE_TOKENS = (28, 70)  # plausible spoken-reply length range


def _tasks():
    agent = yaml.safe_load((ROOT / "configs/suites/agent.yaml").read_text())
    voice = yaml.safe_load((ROOT / "configs/suites/voice.yaml").read_text())
    vision = yaml.safe_load((ROOT / "configs/suites/vision.yaml").read_text())
    tasks = []
    for t in agent["tasks"]:
        e = t.get("expect", {})
        tasks.append({"suite": "agent", "id": t["id"], "prompt": t["prompt"], "expected_tools": e.get("select", []),
                      "no_tools": bool(e.get("no_tools")), "n_expected_calls": len(e.get("args", []))})
    for i, p in enumerate(voice["prompts"]):
        tasks.append({"suite": "voice", "id": f"voice_{i:02d}", "prompt": p})
    for im in vision["images"]:
        tasks.append({"suite": "vision", "id": Path(im["path"]).stem, "image_url": im["url"], "license": im["license"]})
    tools = [{"name": t["name"], "description": t["description"]} for t in agent["tools"]]
    return tasks, tools


def _measured():
    """Flatten the committed result files into per-item rows (measured; model replies/finals dropped)."""
    rows, models = [], []
    for kind in ("runs", "legacy"):
        for f in sorted(glob.glob(str(ROOT / f"results/{kind}/*.json"))):
            r = json.loads(Path(f).read_text())
            m = r["model"]
            if kind == "runs":
                models.append({"tag": m, "digest": r.get("digest", "")[:12], "caps": r.get("caps", []), "think_levels": list(r.get("agent", {}))})
            base = {"provenance": "measured", "set": kind, "model": m, "started": r.get("started")}
            for v in r.get("vision", []):
                rows.append({**base, "suite": "vision", "item": Path(v["image"]).stem if "image" in v else None,
                             "latency_s": round(v["sec"], 3), "json_valid": v["valid"]})
            for i, v in enumerate(r.get("voice", [])):
                rows.append({**base, "suite": "voice", "item": f"voice_{v.get('prompt_idx', i):02d}", "ttft_s": round(v["ttft"], 3),
                             "tok_s": round(v["tps"], 1)})
            for think, items in r.get("agent", {}).items():
                for a in items:
                    rows.append({**base, "suite": "agent", "think": think, "item": a["id"], "latency_s": round(a["sec"], 3) if a.get("sec") else None,
                                 "tool_selected": a["sel"], "args_correct": a["args"], "task_complete": a["complete"], "valid_json": a["json_ok"],
                                 "tools_called": [c[0] for c in a.get("calls", [])] if a.get("calls") is not None else None})
    return rows, models


def _synthetic(measured, tasks, seed):
    """Synthetic repeat trials around the measured medians (clearly labelled; NOT real results)."""
    rng = random.Random(seed)
    cur = [r for r in measured if r["set"] == "runs"]
    out = []
    by = {}
    for r in cur:
        by.setdefault((r["model"], r["suite"], r.get("think")), []).append(r)
    agent_tasks = [t for t in tasks if t["suite"] == "agent"]
    for (model, suite, think), rows in sorted(by.items(), key=lambda x: (x[0][0], x[0][1], x[0][2] or "")):
        for trial in range(1, TRIALS + 1):
            base = {"provenance": "synthetic", "model": model, "trial": trial, "date": SYN_DATES[trial - 1]}
            if suite == "vision":
                med = st.median(r["latency_s"] for r in rows)
                for r in rows:
                    lat = max(0.3, rng.lognormvariate(0, 0.18) * med)
                    out.append({**base, "suite": "vision", "item": r["item"], "latency_s": round(lat, 3), "json_valid": rng.random() > 0.02,
                                "tokens_out": rng.randint(45, 80)})
            elif suite == "voice":
                ttft = st.median(r["ttft_s"] for r in rows if r["ttft_s"] < 5)  # skip cold-load outliers
                tps = st.median(r["tok_s"] for r in rows)
                for r in rows:
                    toks = rng.randint(*VOICE_TOKENS)
                    t_s = max(5.0, rng.gauss(tps, tps * 0.08))
                    t_ttft = max(0.03, rng.lognormvariate(0, 0.25) * ttft)
                    out.append({**base, "suite": "voice", "item": r["item"], "ttft_s": round(t_ttft, 3), "tok_s": round(t_s, 1),
                                "tokens_out": toks, "total_s": round(t_ttft + toks / t_s, 3)})
            else:
                item = {r["item"]: r for r in rows}
                for t in agent_tasks:
                    m = item.get(t["id"])
                    p_ok = 0.97 if (m is None or m["task_complete"]) else 0.55
                    lat0 = (m["latency_s"] if m and m["latency_s"] else 3.0)
                    lat = max(0.4, rng.lognormvariate(0, 0.2) * lat0)
                    complete = rng.random() < p_ok
                    sel = complete or rng.random() < 0.8
                    calls = t["n_expected_calls"] if not t["no_tools"] else 0
                    out.append({**base, "suite": "agent", "think": think, "item": t["id"], "latency_s": round(lat, 3),
                                "ttft_s": round(lat * rng.uniform(0.08, 0.2), 3), "tool_calls": calls + (1 if not complete and rng.random() < 0.5 else 0),
                                "tokens_in": rng.randint(620, 980) + 140 * calls, "tokens_out": rng.randint(40, 260) * (3 if think == "high" else 1),
                                "tool_selected": sel, "args_correct": complete or (sel and rng.random() < 0.5), "task_complete": complete,
                                "valid_json": rng.random() > 0.01})
    return out


def _rollup(rows):
    g = {}
    for r in rows:
        g.setdefault((r["model"], r["suite"], r.get("think")), []).append(r)
    res = []
    for (m, s, th), rs in sorted(g.items(), key=lambda x: (x[0][0], x[0][1], x[0][2] or "")):
        o = {"model": m, "suite": s, "think": th, "n": len(rs)}
        for k in ("latency_s", "ttft_s", "tok_s"):
            v = sorted(r[k] for r in rs if r.get(k) is not None)
            if v:
                o[f"{k}_p50"] = round(st.median(v), 3)
                o[f"{k}_p95"] = round(v[min(len(v) - 1, int(0.95 * len(v)))], 3)
        if s == "agent":
            o["task_complete_pct"] = round(100 * sum(r["task_complete"] for r in rs) / len(rs), 1)
        res.append(o)
    return res


def main():
    ap = argparse.ArgumentParser(description="Generate the Local LLM bake-off demo dataset (seeded, deterministic).")
    ap.add_argument("--out", default=str(ROOT / "demo/data"))
    ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args()
    out = Path(a.out)
    tasks, tools = _tasks()
    measured, models = _measured()
    syn = _synthetic(measured, tasks, a.seed)
    files = [
        write(out / "tasks.json", {"note": "Suite catalog from configs/suites/*.yaml (fictional planner/calendar fixtures; public images).",
                                   "tools": tools, "tasks": tasks}),
        write(out / "models.json", {"hardware": "Mac Studio M3 Ultra, 256 GB unified memory", "models": models}),
        write(out / "measured_items.json", {"provenance": "measured", "note": "Per-item rows flattened from results/runs and results/legacy "
                                            "(same runs as summary.json). Model replies are dropped; legacy vision frames were private and are not included.",
                                            "count": len(measured), "items": measured}),
        write(out / "synthetic_trials.json", {"provenance": "synthetic", "synthetic": True, "seed": a.seed,
                                              "note": f"SYNTHETIC repeat trials ({TRIALS} per item) sampled around the measured medians to demo per-run charts "
                                                      "(variance bands, pass-rate by trial). Not real benchmark results; do not cite these numbers.",
                                              "count": len(syn), "trials": syn}),
        write(out / "synthetic_rollup.json", {"provenance": "synthetic", "synthetic": True,
                                              "note": "p50/p95 over synthetic_trials.json only. Real medians are in summary.json.",
                                              "rows": _rollup(syn)}),
    ]
    counts = {"tasks": len(tasks), "models": len(models), "measured_items": len(measured), "synthetic_trials": len(syn)}
    write(out / "manifest.json", {"app": "local-llm-bakeoff", "generator": "demo/generate_data.py", "seed": a.seed, "rows": counts,
                                  "unchanged": ["summary.json (real aggregate medians; served as site/data/summary.json)"], "files": files})
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
