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


class _Resp:
    def __init__(self, code, text="", data=None):
        self.status_code, self.text, self._data = code, text, data or {}

    def json(self):
        return self._data


def test_graphql_post_retries_on_5xx_then_succeeds(monkeypatch):
    answers = [_Resp(502, "<html>502</html>"), _Resp(503), _Resp(200, data={"data": {}})]
    calls, naps = [], []
    monkeypatch.setattr(today.requests, "post", lambda *a, **k: (calls.append(k), answers.pop(0))[1])
    monkeypatch.setattr(today.time, "sleep", naps.append)
    r = today.graphql_post("query {}", {})
    assert r.status_code == 200 and len(calls) == 3
    assert naps == sorted(naps) and len(naps) == 2        # backed off before each retry, growing


def test_graphql_post_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr(today.requests, "post", lambda *a, **k: _Resp(502))
    monkeypatch.setattr(today.time, "sleep", lambda s: None)
    r = today.graphql_post("query {}", {}, attempts=3)
    assert r.status_code == 502


def test_graphql_post_does_not_retry_4xx(monkeypatch):
    n = []
    monkeypatch.setattr(today.requests, "post", lambda *a, **k: (n.append(1), _Resp(401))[1])
    monkeypatch.setattr(today.time, "sleep", lambda s: None)
    assert today.graphql_post("query {}", {}).status_code == 401 and len(n) == 1
