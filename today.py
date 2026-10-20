"""Daily data + render pipeline for the profile README's tmux hero.

The GitHub GraphQL stats and LOC-cache machinery (user_getter, loc_query, cache_builder,
recursive_loc, graph_repos_stars, ...) is adapted from Andrew6rant/Andrew6rant (today.py).
The tmux hero data sources and rendering hooks at the bottom are specific to this profile.
"""
import datetime
from dateutil import relativedelta
import requests
import os
import time
import hashlib
import argparse
import json

import render_cards
import render_tmux

# Fine-grained personal access token with All Repositories access:
# Account permissions: read:Followers, read:Starring, read:Watching
# Repository permissions: read:Commit statuses, read:Contents, read:Metadata, read:Pull Requests
HEADERS = {'authorization': 'token ' + os.environ.get('ACCESS_TOKEN', '')}
USER_NAME = os.environ.get('USER_NAME', 'cybertron288')
QUERY_COUNT = {'user_getter': 0, 'follower_getter': 0, 'graph_repos_stars': 0, 'recursive_loc': 0, 'graph_commits': 0, 'loc_query': 0, 'languages_getter': 0, 'events_getter': 0, 'calendar_getter': 0, 'cards_getter': 0}


def format_plural(unit):
    return 's' if unit != 1 else ''


def graphql_post(query, variables, attempts=5):
    """POST to the GraphQL API, retrying 5xx (gateway timeouts on heavy queries) with backoff."""
    for i in range(attempts):
        request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables': variables}, headers=HEADERS)
        if request.status_code < 500 or i == attempts - 1:
            return request
        wait = 2 ** (i + 1)
        print(f'GraphQL returned {request.status_code}; retry {i + 1}/{attempts - 1} in {wait}s')
        time.sleep(wait)
    return request


def simple_request(func_name, query, variables):
    request = graphql_post(query, variables)
    if request.status_code == 200:
        return request
    raise Exception(func_name, ' has failed with a', request.status_code, request.text, QUERY_COUNT)


def graph_commits(start_date, end_date):
    query_count('graph_commits')
    query = '''
    query($start_date: DateTime!, $end_date: DateTime!, $login: String!) {
        user(login: $login) {
            contributionsCollection(from: $start_date, to: $end_date) {
                contributionCalendar {
                    totalContributions
                }
            }
        }
    }'''
    variables = {'start_date': start_date, 'end_date': end_date, 'login': USER_NAME}
    request = simple_request(graph_commits.__name__, query, variables)
    return int(request.json()['data']['user']['contributionsCollection']['contributionCalendar']['totalContributions'])


def graph_repos_stars(count_type, owner_affiliation, cursor=None):
    query_count('graph_repos_stars')
    query = '''
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: $owner_affiliation) {
                totalCount
                edges {
                    node {
                        ... on Repository {
                            nameWithOwner
                            stargazers {
                                totalCount
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }'''
    variables = {'owner_affiliation': owner_affiliation, 'login': USER_NAME, 'cursor': cursor}
    request = simple_request(graph_repos_stars.__name__, query, variables)
    if request.status_code == 200:
        if count_type == 'repos':
            return request.json()['data']['user']['repositories']['totalCount']
        elif count_type == 'stars':
            return stars_counter(request.json()['data']['user']['repositories']['edges'])


def recursive_loc(owner, repo_name, data, cache_comment, addition_total=0, deletion_total=0, my_commits=0, cursor=None):
    query_count('recursive_loc')
    query = '''
    query ($repo_name: String!, $owner: String!, $cursor: String) {
        repository(name: $repo_name, owner: $owner) {
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: 100, after: $cursor) {
                            totalCount
                            edges {
                                node {
                                    ... on Commit {
                                        committedDate
                                    }
                                    author {
                                        user {
                                            id
                                        }
                                    }
                                    deletions
                                    additions
                                }
                            }
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                        }
                    }
                }
            }
        }
    }'''
    variables = {'repo_name': repo_name, 'owner': owner, 'cursor': cursor}
    request = graphql_post(query, variables)
    if request.status_code == 200:
        if request.json()['data']['repository']['defaultBranchRef'] is not None:
            return loc_counter_one_repo(owner, repo_name, data, cache_comment, request.json()['data']['repository']['defaultBranchRef']['target']['history'], addition_total, deletion_total, my_commits)
        else:
            return 0
    force_close_file(data, cache_comment)
    if request.status_code == 403:
        raise Exception('Too many requests in a short amount of time!\nYou\'ve hit the non-documented anti-abuse limit!')
    raise Exception('recursive_loc() has failed with a', request.status_code, request.text, QUERY_COUNT)


def loc_counter_one_repo(owner, repo_name, data, cache_comment, history, addition_total, deletion_total, my_commits):
    for node in history['edges']:
        if node['node']['author']['user'] == OWNER_ID:
            my_commits += 1
            addition_total += node['node']['additions']
            deletion_total += node['node']['deletions']

    if history['edges'] == [] or not history['pageInfo']['hasNextPage']:
        return addition_total, deletion_total, my_commits
    else:
        return recursive_loc(owner, repo_name, data, cache_comment, addition_total, deletion_total, my_commits, history['pageInfo']['endCursor'])


def loc_query(owner_affiliation, comment_size=0, force_cache=False, cursor=None, edges=[]):
    query_count('loc_query')
    query = '''
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 60, after: $cursor, ownerAffiliations: $owner_affiliation) {
            edges {
                node {
                    ... on Repository {
                        nameWithOwner
                        defaultBranchRef {
                            target {
                                ... on Commit {
                                    history {
                                        totalCount
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }'''
    variables = {'owner_affiliation': owner_affiliation, 'login': USER_NAME, 'cursor': cursor}
    request = simple_request(loc_query.__name__, query, variables)
    if request.json()['data']['user']['repositories']['pageInfo']['hasNextPage']:
        edges += request.json()['data']['user']['repositories']['edges']
        return loc_query(owner_affiliation, comment_size, force_cache, request.json()['data']['user']['repositories']['pageInfo']['endCursor'], edges)
    else:
        return cache_builder(edges + request.json()['data']['user']['repositories']['edges'], comment_size, force_cache)


def cache_builder(edges, comment_size, force_cache, loc_add=0, loc_del=0):
    cached = True
    os.makedirs('cache', exist_ok=True)  # fresh CI checkouts have no cache dir yet
    filename = 'cache/' + hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest() + '.txt'
    try:
        with open(filename, 'r') as f:
            data = f.readlines()
    except FileNotFoundError:
        data = []
        if comment_size > 0:
            for _ in range(comment_size):
                data.append('This line is a comment block. Write whatever you want here.\n')
        with open(filename, 'w') as f:
            f.writelines(data)

    if len(data) - comment_size != len(edges) or force_cache:
        cached = False
        flush_cache(edges, filename, comment_size)
        with open(filename, 'r') as f:
            data = f.readlines()

    cache_comment = data[:comment_size]
    data = data[comment_size:]
    for index in range(len(edges)):
        repo_hash, commit_count, *__ = data[index].split()
        if repo_hash == hashlib.sha256(edges[index]['node']['nameWithOwner'].encode('utf-8')).hexdigest():
            try:
                if int(commit_count) != edges[index]['node']['defaultBranchRef']['target']['history']['totalCount']:
                    owner, repo_name = edges[index]['node']['nameWithOwner'].split('/')
                    loc = recursive_loc(owner, repo_name, data, cache_comment)
                    data[index] = repo_hash + ' ' + str(edges[index]['node']['defaultBranchRef']['target']['history']['totalCount']) + ' ' + str(loc[2]) + ' ' + str(loc[0]) + ' ' + str(loc[1]) + '\n'
            except TypeError:
                data[index] = repo_hash + ' 0 0 0 0\n'
    with open(filename, 'w') as f:
        f.writelines(cache_comment)
        f.writelines(data)
    for line in data:
        loc = line.split()
        loc_add += int(loc[3])
        loc_del += int(loc[4])
    return [loc_add, loc_del, loc_add - loc_del, cached]


def flush_cache(edges, filename, comment_size):
    with open(filename, 'r') as f:
        data = []
        if comment_size > 0:
            data = f.readlines()[:comment_size]
    with open(filename, 'w') as f:
        f.writelines(data)
        for node in edges:
            f.write(hashlib.sha256(node['node']['nameWithOwner'].encode('utf-8')).hexdigest() + ' 0 0 0 0\n')


def force_close_file(data, cache_comment):
    filename = 'cache/' + hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest() + '.txt'
    with open(filename, 'w') as f:
        f.writelines(cache_comment)
        f.writelines(data)
    print('There was an error while writing to the cache file. The file,', filename, 'has had the partial data saved and closed.')


def stars_counter(data):
    total_stars = 0
    for node in data:
        total_stars += node['node']['stargazers']['totalCount']
    return total_stars


def commit_counter(comment_size):
    total_commits = 0
    filename = 'cache/' + hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest() + '.txt'
    with open(filename, 'r') as f:
        data = f.readlines()
    data = data[comment_size:]
    for line in data:
        total_commits += int(line.split()[2])
    return total_commits


def user_getter(username):
    query_count('user_getter')
    query = '''
    query($login: String!){
        user(login: $login) {
            id
            createdAt
        }
    }'''
    variables = {'login': username}
    request = simple_request(user_getter.__name__, query, variables)
    return {'id': request.json()['data']['user']['id']}, request.json()['data']['user']['createdAt']


def follower_getter(username):
    query_count('follower_getter')
    query = '''
    query($login: String!){
        user(login: $login) {
            followers {
                totalCount
            }
        }
    }'''
    request = simple_request(follower_getter.__name__, query, {'login': username})
    return int(request.json()['data']['user']['followers']['totalCount'])


# ───────────────────────── tmux hero data sources ─────────────────────────
MSG_MAX = 58


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def _parse_iso(iso):
    return datetime.datetime.strptime(iso, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)


def format_uptime(created_at, now):
    """GitHub account age, e.g. '6 years, 2 months, 11 days'."""
    diff = relativedelta.relativedelta(now, _parse_iso(created_at))
    return '{} {}, {} {}, {} {}'.format(
        diff.years, 'year' + format_plural(diff.years),
        diff.months, 'month' + format_plural(diff.months),
        diff.days, 'day' + format_plural(diff.days))


def languages_from_edges(repo_edges, top=4):
    """Sum language bytes across repos -> [{'name', 'pct'}] (top N, integer percent of total)."""
    totals = {}
    for edge in repo_edges:
        for lang in (edge['node'].get('languages') or {}).get('edges', []):
            totals[lang['node']['name']] = totals.get(lang['node']['name'], 0) + lang['size']
    grand = sum(totals.values())
    if grand == 0:
        return []
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:top]
    return [{'name': name, 'pct': size * 100 // grand} for name, size in ranked]


def relative_age(iso, now):
    seconds = (now - _parse_iso(iso)).total_seconds()
    if seconds < 3600:
        return '<1h'
    if seconds < 86400:
        return f'{int(seconds // 3600)}h'
    days = int(seconds // 86400)
    if days < 14:
        return f'{days}d'
    if days < 60:
        return f'{days // 7}w'
    return f'{days // 30}mo'


def commits_from_events(events, login, now, limit=2):
    """Newest commits by `login` from the public events feed (PushEvent payloads list commits oldest-first)."""
    out = []
    for event in events:
        if event.get('type') != 'PushEvent' or event.get('actor', {}).get('login') != login:
            continue
        for commit in reversed(event['payload'].get('commits', [])):
            msg = commit['message'].split('\n', 1)[0]
            if len(msg) > MSG_MAX:
                msg = msg[:MSG_MAX - 1] + '…'
            out.append({'sha': commit['sha'][:7], 'msg': msg, 'repo': event['repo']['name'],
                        'age': relative_age(event['created_at'], now)})
            if len(out) == limit:
                return out
    return out


def languages_getter(cursor=None, edges=None):
    query_count('languages_getter')
    edges = [] if edges is None else edges
    query = '''
    query ($login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
                edges {
                    node {
                        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
                            edges { size node { name } }
                        }
                    }
                }
                pageInfo { endCursor hasNextPage }
            }
        }
    }'''
    request = simple_request(languages_getter.__name__, query, {'login': USER_NAME, 'cursor': cursor})
    repos = request.json()['data']['user']['repositories']
    edges += repos['edges']
    if repos['pageInfo']['hasNextPage']:
        return languages_getter(repos['pageInfo']['endCursor'], edges)
    return languages_from_edges(edges)


def events_getter():
    query_count('events_getter')
    request = requests.get(f'https://api.github.com/users/{USER_NAME}/events/public?per_page=100', headers=HEADERS)
    if request.status_code != 200:
        print(f'events_getter: GitHub returned {request.status_code}; recent-commit rows will be blank')
        return []
    return request.json()


def activity_from_calendar(weeks):
    """GraphQL contributionCalendar weeks -> {'weekly', 'total', 'start', 'end'} (None when empty)."""
    days = [d for w in weeks for d in w['contributionDays']]
    if not days:
        return None
    weekly = [sum(d['contributionCount'] for d in w['contributionDays']) for w in weeks]
    return {'weekly': weekly, 'total': sum(weekly), 'start': days[0]['date'], 'end': days[-1]['date']}


def calendar_getter():
    query_count('calendar_getter')
    query = '''
    query ($login: String!) {
        user(login: $login) {
            contributionsCollection {
                contributionCalendar { weeks { contributionDays { date contributionCount } } }
            }
        }
    }'''
    request = simple_request(calendar_getter.__name__, query, {'login': USER_NAME})
    weeks = request.json()['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
    return activity_from_calendar(weeks)


def cards_getter():
    """Stars and forks for every repo-backed project card (render_cards.PROJECTS entries with a `repo`)."""
    query_count('cards_getter')
    repos = {key: proj['repo'] for key, proj in render_cards.PROJECTS.items() if 'repo' in proj}
    parts = []
    for i, (key, full) in enumerate(repos.items()):
        owner, name = full.split('/')
        parts.append(f'r{i}: repository(owner: "{owner}", name: "{name}") {{ stargazerCount forkCount }}')
    data = simple_request(cards_getter.__name__, 'query { ' + ' '.join(parts) + ' }', {}).json()['data']
    return {key: {'stars': data[f'r{i}']['stargazerCount'], 'forks': data[f'r{i}']['forkCount']} for i, key in enumerate(repos)}


def query_count(funct_id):
    global QUERY_COUNT
    QUERY_COUNT[funct_id] += 1


def perf_counter(funct, *args):
    start = time.perf_counter()
    funct_return = funct(*args)
    return funct_return, time.perf_counter() - start


def formatter(query_type, difference, funct_return=False, whitespace=0):
    print('{:<23}'.format('   ' + query_type + ':'), sep='', end='')
    print('{:>12}'.format('%.4f' % difference + ' s ')) if difference > 1 else print('{:>12}'.format('%.4f' % (difference * 1000) + ' ms'))
    if whitespace:
        return f"{'{:,}'.format(funct_return): <{whitespace}}"
    return funct_return


OWNER_ID = None


def build_data(now=None):
    """Run every GitHub query and return the dict render_tmux.render consumes."""
    global OWNER_ID
    now = now or now_utc()
    print('Calculation times:')
    user_data, user_time = perf_counter(user_getter, USER_NAME)
    OWNER_ID, acc_date = user_data
    formatter('account data', user_time)
    total_loc, loc_time = perf_counter(loc_query, ['OWNER', 'COLLABORATOR', 'ORGANIZATION_MEMBER'], 7)
    formatter('LOC (cached)', loc_time) if total_loc[-1] else formatter('LOC (no cache)', loc_time)
    commit_data, commit_time = perf_counter(commit_counter, 7)
    formatter('commit counter', commit_time)
    star_data, star_time = perf_counter(graph_repos_stars, 'stars', ['OWNER'])
    formatter('star counter', star_time)
    repo_data, repo_time = perf_counter(graph_repos_stars, 'repos', ['OWNER'])
    formatter('my repositories', repo_time)
    contrib_data, contrib_time = perf_counter(graph_repos_stars, 'repos', ['OWNER', 'COLLABORATOR', 'ORGANIZATION_MEMBER'])
    formatter('contributed repos', contrib_time)
    follower_data, follower_time = perf_counter(follower_getter, USER_NAME)
    formatter('follower counter', follower_time)
    languages, lang_time = perf_counter(languages_getter)
    formatter('languages', lang_time)
    events, events_time = perf_counter(events_getter)
    formatter('public events', events_time)
    activity, cal_time = perf_counter(calendar_getter)
    formatter('contribution calendar', cal_time)
    cards, cards_time = perf_counter(cards_getter)
    formatter('project cards', cards_time)
    print('Total GitHub API calls:', '{:>3}'.format(sum(QUERY_COUNT.values())))
    for funct_name, count in QUERY_COUNT.items():
        print('{:<28}'.format('   ' + funct_name + ':'), '{:>6}'.format(count))
    return {
        'login': USER_NAME, 'name': 'Ravi Patel', 'generated': now.strftime('%Y-%m-%d'),
        'uptime': format_uptime(acc_date, now),
        'commits': commit_data, 'stars': star_data, 'repos': repo_data, 'contrib_repos': contrib_data,
        'followers': follower_data,
        'loc': {'add': total_loc[0], 'del': total_loc[1], 'net': total_loc[2]},
        'languages': languages,
        'commits_recent': commits_from_events(events, USER_NAME, now),
        'activity': activity,
        'cards': cards,
    }


def write_hero(data, portrait_path='assets/portrait.json', out_dir='assets'):
    """Render dark + light hero, project cards and activity strip; returns the written paths."""
    with open(portrait_path) as f:
        portrait = json.load(f)
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for theme in ('dark', 'light'):
        pal = render_tmux.PALETTES[theme]
        outputs = {
            'tmux': render_tmux.render(data, pal, portrait),
            'activity': render_cards.render_activity(data, pal),
            **{f'card-{key}': render_cards.render_card(key, data, pal) for key in render_cards.PROJECTS},
        }
        for name, svg in outputs.items():
            path = os.path.join(out_dir, f'{name}-{theme}.svg')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(svg)
            written.append(path)
    return written


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate the hero, project-card and activity SVGs for the profile README.')
    parser.add_argument('--render-only', metavar='DATA_JSON', help='skip GitHub queries; render from this data file')
    parser.add_argument('--out', default='assets', help='output directory (default: assets)')
    parser.add_argument('--portrait', default='assets/portrait.json')
    args = parser.parse_args()
    if args.render_only:
        with open(args.render_only) as f:
            hero_data = json.load(f)
    else:
        hero_data = build_data()
    for written_path in write_hero(hero_data, args.portrait, args.out):
        print('wrote', written_path)
