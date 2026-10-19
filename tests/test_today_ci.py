import datetime, today


def test_cache_builder_creates_missing_cache_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / "cache").exists()
    result = today.cache_builder([], 7, False)
    assert (tmp_path / "cache").is_dir() and list((tmp_path / "cache").glob("*.txt"))
    assert result[:3] == [0, 0, 0]


def test_now_utc_is_timezone_aware():
    assert today.now_utc().tzinfo is not None


def test_events_getter_reports_non_200(monkeypatch, capsys):
    class R:
        status_code = 403
    monkeypatch.setattr(today.requests, "get", lambda *a, **k: R())
    assert today.events_getter() == []
    assert "403" in capsys.readouterr().out


def test_languages_from_edges_tolerates_null_languages():
    edges = [{"node": {"languages": None}}, {"node": {"languages": {"edges": [{"size": 10, "node": {"name": "Go"}}]}}}]
    assert today.languages_from_edges(edges) == [{"name": "Go", "pct": 100}]
