import base64, pathlib, time
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
        t = time.time(); txt = cl.chat(body)["message"]["content"]; dt = time.time() - t
        obj, valid = parse_json_reply(txt)
        res.append({"image": img["path"], "sec": dt, "valid": valid and caption_ok(obj), "raw": txt})
    return [r for r in res if "sec" in r] or res
