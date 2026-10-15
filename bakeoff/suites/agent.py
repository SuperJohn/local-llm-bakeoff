import json, re, time
from ..scoring import score_agent


def tools_schema(tools):
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
             "parameters": {"type": "object", "properties": t["params"], "required": t.get("required", [])}}}
            for t in tools]


def mock(fixtures, name, args):
    """Deterministic fake tool backend driven by fixtures in the suite file."""
    f = fixtures.get(name)
    if f is None:
        return {"error": "unknown tool"}
    if isinstance(f, dict) and "by" in f:
        return f["values"].get(str(args.get(f["by"], "")).lower(), f.get("default", []))
    if isinstance(f, dict) and f.get("echo"):
        return {**f.get("extra", {}), **args}
    return f


def run(cl, model, suite, seed, base, think=None, max_steps=6):
    d = suite["data"]; tools = tools_schema(d["tools"]); res = []
    for task in d["tasks"]:
        msgs = [{"role": "system", "content": d["system"]}, {"role": "user", "content": task["prompt"]}]
        calls = []; bad = 0; final = ""; t = time.time()
        for _ in range(max_steps):
            body = {"model": model, "stream": False, "messages": msgs, "tools": tools,
                    "options": {"temperature": 0, "seed": seed}}
            if think is not None:
                body["think"] = think
            try:
                msg = cl.chat(body)["message"]
            except Exception as e:
                final = f"ERROR {e}"; break
            tc = msg.get("tool_calls") or []
            if not tc:
                final = msg.get("content", ""); break
            msgs.append({"role": "assistant", "content": msg.get("content", ""), "tool_calls": tc})
            for x in tc:
                a = x["function"].get("arguments")
                if isinstance(a, str):
                    try: a = json.loads(a)
                    except Exception: bad += 1; a = {}
                if not isinstance(a, dict): bad += 1; a = {}
                n = x["function"]["name"]; calls.append((n, a))
                msgs.append({"role": "tool", "tool_name": n, "content": json.dumps(mock(d["fixtures"], n, a))})
        if not calls and re.search(r'"name"\s*:\s*"\w+_', final):
            bad += 1
        s = score_agent(task, calls, final)
        res.append({"id": task["id"], **s, "json_ok": bad == 0, "sec": time.time() - t,
                    "calls": [[n, a] for n, a in calls], "final": final[:300]})
    return res
