"""Download the public images listed in configs/suites/vision.yaml."""
import pathlib, urllib.request, yaml
cfg = yaml.safe_load(open("configs/suites/vision.yaml"))
for im in cfg["images"]:
    p = pathlib.Path(im["path"]); p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists(): continue
    req = urllib.request.Request(im["url"], headers={"User-Agent": "local-llm-bakeoff/0.1"})
    p.write_bytes(urllib.request.urlopen(req, timeout=60).read()); print("fetched", p)
