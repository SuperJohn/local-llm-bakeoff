import base64, pathlib, time, urllib.error
from ..scoring import parse_json_reply, caption_ok


def run(cl, model, suite, seed, base):
    res = []
    for img in suite["data"]["images"]:
        p = pathlib.Path(base) / img["path"]
        if not p.exists():
            res.append({"image": img["path"], "skipped": "missing (run `make images`)"}); continue
        b = base64.b64encode(p.read_bytes()).decode()
        body = {"model": model, "stream": False, "format": "json", "think": False,
                "messages": [{"role": "user", "content": suite["data"]["prompt"], "images": [b]}],
                "options": {"temperature": suite.get("temperature", 0.2), "seed": seed}}
        fallback = False
        t = time.time()
        try:
            txt = cl.chat(body)["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code != 501:  # Ollama 0.40: "structured output is unavailable" for some models
                raise
            body.pop("format"); fallback = True; t = time.time()
            txt = cl.chat(body)["message"]["content"]
        dt = time.time() - t
        obj, valid = parse_json_reply(txt)
        res.append({"image": img["path"], "sec": dt, "valid": valid and caption_ok(obj), "format_fallback": fallback, "raw": txt})
    return [r for r in res if "sec" in r] or res
