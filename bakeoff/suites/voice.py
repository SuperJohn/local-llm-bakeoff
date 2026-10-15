import time


def run(cl, model, suite, seed, base, think_ok=False):
    d = suite["data"]; res = []
    for p in d["prompts"]:
        body = {"model": model, "stream": True,
                "messages": [{"role": "system", "content": d["system"]}, {"role": "user", "content": p}],
                "options": {"temperature": suite.get("temperature", 0.6), "num_predict": 200, "seed": seed}}
        if think_ok:
            body["think"] = "low" if model.startswith("gpt-oss") else False
        t = time.time(); ttft = None; txt = ""; last = {}
        for c in cl.stream_chat(body):
            s = c.get("message", {}).get("content", "")
            if s and ttft is None:
                ttft = time.time() - t
            txt += s; last = c
        tps = last.get("eval_count", 0) / (last.get("eval_duration", 1) / 1e9)
        res.append({"prompt": p, "ttft": ttft or time.time() - t, "tps": tps, "reply": txt.strip()})
    return res
