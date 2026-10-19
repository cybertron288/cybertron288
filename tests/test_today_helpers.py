import datetime, today

NOW = datetime.datetime(2026, 10, 19, 21, 0, 0, tzinfo=datetime.timezone.utc)


def test_format_uptime():
    assert today.format_uptime("2020-08-08T10:00:00Z", NOW) == "6 years, 2 months, 11 days"


def test_languages_from_edges_percentages_and_order():
    edges = [{"node": {"languages": {"edges": [{"size": 460, "node": {"name": "Python"}}, {"size": 310, "node": {"name": "TypeScript"}}]}}},
             {"node": {"languages": {"edges": [{"size": 140, "node": {"name": "JavaScript"}}, {"size": 90, "node": {"name": "CSS"}}, {"size": 1, "node": {"name": "Shell"}}]}}}]
    out = today.languages_from_edges(edges, top=4)
    assert [l["name"] for l in out] == ["Python", "TypeScript", "JavaScript", "CSS"]
    assert out[0]["pct"] == 45 and sum(l["pct"] for l in out) <= 100


def test_languages_empty():
    assert today.languages_from_edges([]) == []
    assert today.languages_from_edges([{"node": {"languages": {"edges": []}}}]) == []


def test_relative_age():
    assert today.relative_age("2026-10-19T20:30:00Z", NOW) == "<1h"
    assert today.relative_age("2026-10-19T15:00:00Z", NOW) == "6h"
    assert today.relative_age("2026-10-17T15:00:00Z", NOW) == "2d"
    assert today.relative_age("2026-09-10T15:00:00Z", NOW) == "5w"
    assert today.relative_age("2026-06-10T15:00:00Z", NOW) == "4mo"


def test_commits_from_events_truncates_and_limits():
    long = "feat(igris): " + "x" * 80
    events = [
        {"type": "WatchEvent", "actor": {"login": "cybertron288"}, "repo": {"name": "a/b"}, "created_at": "2026-10-19T20:00:00Z", "payload": {}},
        {"type": "PushEvent", "actor": {"login": "cybertron288"}, "repo": {"name": "igris/policy-engine"}, "created_at": "2026-10-17T20:00:00Z",
         "payload": {"commits": [{"sha": "c3333333333", "message": "third (oldest)", "author": {"name": "Ravi Patel", "email": "x@y"}},
                                 {"sha": "b2222222222", "message": "second", "author": {"name": "Ravi Patel", "email": "x@y"}},
                                 {"sha": "a1f3c2e9999", "message": long + "\n\nbody", "author": {"name": "Ravi Patel", "email": "x@y"}}]}},
    ]
    out = today.commits_from_events(events, "cybertron288", NOW, limit=2)
    assert len(out) == 2
    assert out[0]["sha"] == "a1f3c2e" and out[0]["age"] == "2d" and out[0]["repo"] == "igris/policy-engine"
    assert len(out[0]["msg"]) == 58 and out[0]["msg"].endswith("…")
    assert out[1]["msg"] == "second"


def test_commits_from_events_empty():
    assert today.commits_from_events([], "cybertron288", NOW) == []
