from bakeoff import scoring
from bakeoff.suites.agent import mock


def test_parse_json_fenced():
    obj, ok = scoring.parse_json_reply('```json\n{"description":"x","activity":"y","people":1,"pets":0}\n```')
    assert ok and scoring.caption_ok(obj)


def test_parse_json_bad():
    assert scoring.parse_json_reply("not json") == (None, False)
    assert not scoring.caption_ok({"description": "x"})


def test_score_agent_full_credit():
    task = {"expect": {"select": ["move_block"], "args": [{"tool": "move_block", "args": {"block_id": "b2", "new_start": "17:00"}}]}}
    s = scoring.score_agent(task, [("get_plan_blocks", {"date": "2026-10-13"}), ("move_block", {"block_id": "b2", "new_start": "17:00"})], "Done")
    assert s == {"sel": True, "args": True, "complete": True}


def test_score_agent_wrong_args():
    task = {"expect": {"select": ["move_block"], "args": [{"tool": "move_block", "args": {"block_id": "b2"}}], "final_contains": ["moved"]}}
    s = scoring.score_agent(task, [("move_block", {"block_id": "b1"})], "ok")
    assert s == {"sel": True, "args": False, "complete": False}


def test_no_tools_task():
    task = {"expect": {"no_tools": True, "final_contains": ["391"]}}
    assert scoring.score_agent(task, [], "It's 391.") == {"sel": True, "args": True, "complete": True}
    assert scoring.score_agent(task, [("get_weather", {})], "391")["sel"] is False


def test_mock_fixtures():
    fx = {"get_events": {"by": "date", "values": {"2026-10-14": [1]}}, "move_block": {"echo": True, "extra": {"ok": True}}}
    assert mock(fx, "get_events", {"date": "2026-10-14"}) == [1]
    assert mock(fx, "get_events", {"date": "x"}) == []
    assert mock(fx, "move_block", {"block_id": "b1"}) == {"ok": True, "block_id": "b1"}
    assert mock(fx, "nope", {}) == {"error": "unknown tool"}


def test_summarize():
    r = {"vision": [{"sec": 1, "valid": True}, {"sec": 3, "valid": False}],
         "voice": [{"ttft": 0.1, "tps": 50}, {"ttft": 0.3, "tps": 70}],
         "agent": {"low": [{"sel": True, "args": True, "complete": False, "json_ok": True}]}}
    s = scoring.summarize(r)
    assert s["vision_valid_pct"] == 50 and s["vision_med_s"] == 2
    assert s["voice_tps_med"] == 60.0
    assert s["agent_low"]["complete"] == "0/1"


def test_round_half_up_resolves_40_65():
    # legacy qwen3.8 voice median tok/s is (40.4 + 40.9) / 2 = 40.65
    assert scoring.r1(40.65) == 40.7
    assert scoring.summarize({"voice": [{"ttft": 0.2, "tps": 40.4}, {"ttft": 0.2, "tps": 40.9}]})["voice_tps_med"] == 40.7
