"""Run configured suites against pinned Ollama models. Usage: python -m bakeoff.run configs/default.yaml"""
import argparse, json, pathlib, platform, random, time
from . import config
from .ollama import Ollama
from .suites import vision, voice, agent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config"); ap.add_argument("--models"); ap.add_argument("--suites")
    ap.add_argument("--out", default="results/runs")
    a = ap.parse_args()
    cfg = config.load(a.config); base = pathlib.Path(a.config).parent.parent
    random.seed(cfg["seed"]); cl = Ollama(cfg["ollama_url"])
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    want_m = set(a.models.split(",")) if a.models else None
    want_s = set(a.suites.split(",")) if a.suites else set(cfg["suites"])
    for m in cfg["models"]:
        tag = m["tag"]
        if want_m and tag not in want_m: continue
        caps = cl.caps(tag); dig = cl.digest(tag)
        if m.get("digest") and dig and not dig.startswith(m["digest"]):
            print(f"WARN {tag}: digest {dig[:12]} != pinned {m['digest']}")
        r = {"model": tag, "digest": dig, "caps": caps, "seed": cfg["seed"],
             "host": platform.platform(), "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        S = cfg["suites"]
        if "vision" in want_s and "vision" in S and "vision" in caps:
            r["vision"] = vision.run(cl, tag, S["vision"], cfg["seed"], base)
        if "voice" in want_s and "voice" in S:
            r["voice"] = voice.run(cl, tag, S["voice"], cfg["seed"], base, "thinking" in caps)
        if "agent" in want_s and "agent" in S and "tools" in caps:
            levels = m.get("think_levels") or [None]
            r["agent"] = {str(l if l is not None else "default"): agent.run(cl, tag, S["agent"], cfg["seed"], base, l) for l in levels}
        cl.unload(tag)
        p = out / (tag.replace(":", "_").replace("/", "_") + ".json")
        p.write_text(json.dumps(r, indent=1)); print("done", tag, "->", p, flush=True)


if __name__ == "__main__":
    main()
