"""Render PNG charts from result JSONs. Usage: python scripts/charts.py results/runs [out_dir]"""
import glob, json, pathlib, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bakeoff.scoring import summarize

src = sys.argv[1] if len(sys.argv) > 1 else "results/runs"
out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "charts"); out.mkdir(exist_ok=True)
R = []
for f in sorted(glob.glob(f"{src}/*.json")):
    r = json.load(open(f)); R.append((r["model"], summarize(r)))


def bar(fname, title, ylabel, items, fmt="{:.1f}"):
    if not items: return
    lab, val = zip(*items)
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    b = ax.bar(lab, val, color="#3b6ea5")
    for x, v in zip(b, val): ax.text(x.get_x() + x.get_width() / 2, v, fmt.format(v), ha="center", va="bottom", fontsize=9)
    ax.set_title(title); ax.set_ylabel(ylabel); ax.spines[["top", "right"]].set_visible(False)
    plt.xticks(rotation=15, ha="right"); fig.tight_layout(); fig.savefig(out / fname); plt.close(fig)
    print("wrote", out / fname)


bar("voice_tps.png", "Voice: decode tokens/s (median, higher is better)", "tok/s",
    [(m, s["voice_tps_med"]) for m, s in R if "voice_tps_med" in s])
bar("voice_ttft.png", "Voice: time to first token (median, lower is better)", "seconds",
    [(m, s["voice_ttft_med_s"]) for m, s in R if "voice_ttft_med_s" in s], "{:.2f}")
bar("vision_latency.png", "Vision: seconds per image (median, lower is better)", "seconds",
    [(m, s["vision_med_s"]) for m, s in R if "vision_med_s" in s], "{:.2f}")
ag = []
for m, s in R:
    for k, v in s.items():
        if k.startswith("agent_"):
            a, n = map(int, v["complete"].split("/")); lvl = k[6:]
            ag.append((m if lvl == "default" else f"{m} ({lvl})", 100 * a / n))
bar("agent_complete.png", "Agent: tasks completed (% of suite, higher is better)", "%", ag, "{:.0f}%")
