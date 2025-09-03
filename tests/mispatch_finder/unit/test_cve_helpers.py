from mispatch_finder.infra.cve import _normalize_repo_url, _choose_commit


def test_normalize_repo_url_variants():
    assert _normalize_repo_url("owner/name") == "https://github.com/owner/name"
    assert _normalize_repo_url("https://github.com/owner/name") == "https://github.com/owner/name"
    assert _normalize_repo_url("https://github.com/owner/name.git") == "https://github.com/owner/name"
    assert _normalize_repo_url("git@github.com:owner/name") == "https://github.com/owner/name"
    assert _normalize_repo_url("git@github.com:owner/name.git") == "https://github.com/owner/name"


def test_choose_commit_prefers_longest_valid():
    commits = ["abc1234", "abcd1234ef", "zzzz", "123"]
    assert _choose_commit(commits) == "abcd1234ef"


def test_choose_commit_none_if_no_valid():
    assert _choose_commit(["xxx", "!!!"]) is None

