import pathlib, pytest
from bakeoff import config

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_default_config_loads():
    cfg = config.load(ROOT / "configs/default.yaml")
    assert cfg["seed"] == 42
    assert len(cfg["models"]) >= 5
    assert len(cfg["suites"]["agent"]["data"]["tasks"]) >= 30
    assert len(cfg["suites"]["voice"]["data"]["prompts"]) == 10


def test_vision_images_are_public_urls():
    cfg = config.load(ROOT / "configs/default.yaml")
    for im in cfg["suites"]["vision"]["data"]["images"]:
        assert im["url"].startswith("https://upload.wikimedia.org/")


@pytest.mark.parametrize("bad", [
    {"models": []},
    {"models": [{"tag": "llama3.2:latest"}]},
    {"models": [{"tag": "gemma4"}]},
    {"models": [{"tag": "a:1b"}], "seed": "x"},
    {"models": [{"tag": "a:1b"}], "suites": {"bogus": {}}},
])
def test_invalid_configs(bad):
    with pytest.raises(config.ConfigError):
        config.validate(bad)


def test_task_ids_unique():
    cfg = config.load(ROOT / "configs/default.yaml")
    ids = [t["id"] for t in cfg["suites"]["agent"]["data"]["tasks"]]
    assert len(ids) == len(set(ids))


def test_agent_tasks_well_formed():
    cfg = config.load(ROOT / "configs/default.yaml")
    d = cfg["suites"]["agent"]["data"]; names = {t["name"] for t in d["tools"]}
    for t in d["tasks"]:
        e = t["expect"]
        assert t["prompt"].strip()
        for n in e.get("select", []): assert n in names, (t["id"], n)
        for a in e.get("args", []): assert a["tool"] in names, t["id"]
        if e.get("no_tools"): assert not e.get("select")
