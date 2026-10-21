import datetime, today
import pytest


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


def _push(repo, head, commits=None):
    payload = {"head": head} if commits is None else {"head": head, "commits": commits}
    return {"type": "PushEvent", "actor": {"login": "cybertron288"}, "repo": {"name": repo},
            "created_at": "2026-10-19T20:00:00Z", "payload": payload}


def test_fill_push_commits_looks_up_head_when_payload_has_no_commits(monkeypatch):
    seen = []

    def fake_get(url, **k):
        seen.append(url)
        return _Resp(200, data={"sha": "abc1234def", "commit": {"message": "feat: real message\n\nbody"}})
    monkeypatch.setattr(today.requests, "get", fake_get)
    events = [_push("cybertron288/igris", "abc1234def")]
    today.fill_push_commits(events, "cybertron288")
    assert seen == ["https://api.github.com/repos/cybertron288/igris/commits/abc1234def"]
    assert events[0]["payload"]["commits"] == [{"sha": "abc1234def", "message": "feat: real message\n\nbody"}]


def test_fill_push_commits_keeps_existing_commits_and_skips_failed_lookups(monkeypatch):
    monkeypatch.setattr(today.requests, "get", lambda url, **k: _Resp(404))
    kept = [{"sha": "1111111", "message": "already here"}]
    events = [_push("a/b", "1111111", kept), _push("a/c", "2222222")]
    today.fill_push_commits(events, "cybertron288")
    assert events[0]["payload"]["commits"] == kept
    assert "commits" not in events[1]["payload"]


def test_fill_push_commits_caps_lookups(monkeypatch):
    calls = []
    monkeypatch.setattr(today.requests, "get", lambda url, **k: (calls.append(url), _Resp(404))[1])
    today.fill_push_commits([_push("a/b", f"{i:07d}") for i in range(20)], "cybertron288", max_lookups=5)
    assert len(calls) == 5


def test_commits_from_events_skips_merge_commits():
    events = [_push("a/b", "m", [{"sha": "m000000", "message": "Merge pull request #5 from x/y"}]),
              _push("a/b", "f", [{"sha": "f000000", "message": "fix: real work"}])]
    out = today.commits_from_events(events, "cybertron288", today._parse_iso("2026-10-20T20:00:00Z"))
    assert [c["sha"] for c in out] == ["f000000"]


def test_graphql_post_retries_on_timeout(monkeypatch):
    answers = [today.requests.exceptions.ReadTimeout(), _Resp(200, data={"data": {}})]

    def post(*a, **k):
        assert k["timeout"] == today.REQUEST_TIMEOUT
        item = answers.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
    monkeypatch.setattr(today.requests, "post", post)
    monkeypatch.setattr(today.time, "sleep", lambda s: None)
    assert today.graphql_post("query {}", {}).status_code == 200


def test_graphql_post_retries_connection_errors(monkeypatch):
    answers = [today.requests.exceptions.ConnectionError("reset"), _Resp(200, data={"data": {}})]

    def post(*a, **k):
        item = answers.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
    monkeypatch.setattr(today.requests, "post", post)
    monkeypatch.setattr(today.time, "sleep", lambda s: None)
    assert today.graphql_post("query {}", {}).status_code == 200


def test_graphql_post_raises_connection_error_after_last_attempt(monkeypatch):
    def post(*a, **k):
        raise today.requests.exceptions.ConnectionError("down")
    monkeypatch.setattr(today.requests, "post", post)
    monkeypatch.setattr(today.time, "sleep", lambda s: None)
    try:
        today.graphql_post("query {}", {}, attempts=2)
    except today.requests.exceptions.ConnectionError:
        return
    raise AssertionError("expected ConnectionError")


def test_cache_builder_keeps_finished_repos_when_crawl_dies(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    edges = [{"node": {"nameWithOwner": f"o/r{i}", "defaultBranchRef": {"target": {"history": {"totalCount": 5}}}}} for i in range(2)]
    calls = []

    def fake_loc(owner, repo, data, comment, deadline=None):
        calls.append(repo)
        if repo == "r1":
            raise today.requests.exceptions.ConnectionError("reset")
        return (10, 2, 5)
    monkeypatch.setattr(today, "recursive_loc", fake_loc)
    try:
        today.cache_builder(edges, 0, False)
    except today.requests.exceptions.ConnectionError:
        pass
    lines = next((tmp_path / "cache").glob("*.txt")).read_text().splitlines()
    assert lines[0].split()[1:] == ["5", "5", "10", "2"]    # r0 survived the crash
    assert lines[1].split()[1:] == ["0", "0", "0", "0"]     # r1 retried next run


def _edge(name, total):
    return {"node": {"nameWithOwner": name, "defaultBranchRef": {"target": {"history": {"totalCount": total}}}}}


def test_cache_builder_stops_at_budget_and_keeps_stale_lines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    crawled = []

    def fake_loc(owner, repo_name, data, cache_comment, deadline=None):
        if crawled:  # first repo eats the whole budget
            raise today.LocBudgetExceeded(repo_name)
        crawled.append(repo_name)
        return 10, 4, 3
    monkeypatch.setattr(today, "recursive_loc", fake_loc)
    edges = [_edge("me/a", 5), _edge("me/b", 7)]
    add, dele, net, cached = today.cache_builder(edges, 0, False)
    assert (add, dele, net, cached) == (10, 4, 6, False)
    lines = next((tmp_path / "cache").glob("*.txt")).read_text().splitlines()
    assert lines[0].split()[1:] == ["5", "3", "10", "4"]
    assert lines[1].split()[1:] == ["0", "0", "0", "0"]   # untouched, so the next run crawls it


def test_recursive_loc_raises_once_past_deadline(monkeypatch):
    monkeypatch.setattr(today.requests, "post", lambda *a, **k: pytest.fail("no request past the deadline"))
    with pytest.raises(today.LocBudgetExceeded):
        today.recursive_loc("me", "a", [], [], deadline=today.time.monotonic() - 1)
