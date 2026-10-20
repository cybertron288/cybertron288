import json, pathlib, subprocess, sys
from lxml import etree
ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_render_only_writes_both_svgs(tmp_path):
    data = json.loads((ROOT / "fixtures/sample.json").read_text())
    import today
    paths = today.write_hero(data, portrait_path=str(ROOT / "assets/portrait.json"), out_dir=str(tmp_path))
    assert sorted(pathlib.Path(p).name for p in paths) == sorted(
        f"{name}-{theme}.svg" for name in ("tmux", "card-zango", "card-igris", "activity") for theme in ("dark", "light"))
    for p in paths:
        etree.parse(p)


def test_cli_render_only(tmp_path):
    r = subprocess.run([sys.executable, "today.py", "--render-only", "fixtures/sample.json", "--out", str(tmp_path)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "tmux-dark.svg").exists() and (tmp_path / "tmux-light.svg").exists()
