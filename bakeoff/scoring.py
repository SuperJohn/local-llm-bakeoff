"""Pure scoring functions (no Ollama needed)."""
from __future__ import annotations
import json, re, statistics
from decimal import Decimal, ROUND_HALF_UP


def r1(x, nd=1):
    """Round half-up (Python's round() is binary/banker's: round(40.65, 1) == 40.6)."""
    q = Decimal(1).scaleb(-nd)
    return float(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))


def parse_json_reply(txt: str):
    """Strip code fences and parse; returns (obj|None, valid)."""
    t = re.sub(r"^```(json)?|```$", "", (txt or "").strip()).strip()
    try:
        return json.loads(t), True
    except Exception:
        return None, False


def caption_ok(obj, required=("description", "activity", "people", "pets")) -> bool:
    return isinstance(obj, dict) and all(k in obj for k in required) \
        and isinstance(obj.get("people"), int) and isinstance(obj.get("pets"), int)


def has_call(calls, name, **kw) -> bool:
    for n, a in calls:
        if n == name and all(str(v).lower() in str(a.get(k, "")).lower() for k, v in kw.items()):
            return True
    return False


def score_agent(task: dict, calls, final: str) -> dict:
    """task['expect'] = {select: [tool..], args: [{tool, args}], final_contains: [..], no_tools: bool}"""
    e = task.get("expect", {})
    if e.get("no_tools"):
        sel = len(calls) == 0
        args = True
    else:
        sel = all(has_call(calls, t) for t in e.get("select", []))
        args = all(has_call(calls, x["tool"], **x.get("args", {})) for x in e.get("args", []))
    fc = e.get("final_contains", [])
    comp = (not fc) or any(s.lower() in (final or "").lower() for s in fc)
    if e.get("complete_requires_args"):
        comp = comp and args
    return {"sel": sel, "args": args, "complete": comp}


def summarize(results: dict) -> dict:
    """Aggregate a per-model result dict into table metrics."""
    out = {}
    v = results.get("vision")
    if v:
        out["vision_n"] = len(v)
        out["vision_valid_pct"] = round(100 * sum(x["valid"] for x in v) / len(v))
        out["vision_med_s"] = r1(statistics.median(x["sec"] for x in v), 2)
    vo = results.get("voice")
    if vo:
        out["voice_ttft_med_s"] = r1(statistics.median(x["ttft"] for x in vo), 2)
        out["voice_tps_med"] = r1(statistics.median(x["tps"] for x in vo), 1)
    for lvl, a in (results.get("agent") or {}).items():
        n = len(a)
        out[f"agent_{lvl}"] = {k: f"{sum(x[k] for x in a)}/{n}" for k in ("sel", "args", "complete", "json_ok")}
    return out
