"""Import the 2026-10-12/14 legacy run (private ~/bakeoff) as SANITIZED aggregates.
Drops: image files/ids, captions, raw model output, tool-call args, final answers.
Keeps: timings, validity flags, scores. Usage: python scripts/import_legacy.py ~/bakeoff"""
import glob, json, os, pathlib, sys
IDS = ["planner_read", "calendar_read", "create_urgent", "move_gym", "resolve_overlap",
       "weather", "no_tool_math", "relative_due_date", "multi_step"]
src = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/bakeoff")
out = pathlib.Path("results/legacy"); out.mkdir(parents=True, exist_ok=True)
for f in sorted(glob.glob(f"{src}/*_*.json")):
    d = json.load(open(f)); stem = pathlib.Path(f).stem; model = stem.replace("_", ":", 1)
    r = {"model": model, "caps": d.get("caps", []), "source": "legacy run 2026-10-12/14 (private frames; captions withheld)"}
    if d.get("vision"):
        r["vision"] = [{"sec": round(x["sec"], 3), "valid": x["valid"]} for x in d["vision"]]
    if d.get("voice"):
        r["voice"] = [{"prompt_idx": i, "ttft": round(x["ttft"], 3), "tps": round(x["tps"], 1), "tokens": x.get("tokens")} for i, x in enumerate(d["voice"])]
    if d.get("agent"):
        r["agent"] = {k: [{"id": IDS[i], **{m: x[m] for m in ("sel", "args", "complete", "json_ok")}, "sec": round(x["sec"], 2)}
                          for i, x in enumerate(v)] for k, v in d["agent"].items()}
    (out / f"{stem}.json").write_text(json.dumps(r, indent=1)); print("imported", model)
