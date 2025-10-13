from mispatch_finder.core.domain.prompt import build_prompt


def test_build_prompt_includes_all_fields():
    prompt = build_prompt(
        ghsa="GHSA-1234-5678-9012",
        repo_url="https://github.com/owner/repo",
        commit="deadbeef",
        has_previous=True,
        has_current=False,
        diff_text="diff --git a/x b/x\n+1\n-2",
    )
    assert "GHSA-1234-5678-9012" in prompt
    assert "https://github.com/owner/repo" in prompt
    assert "deadbeef" in prompt
    assert "Previous-state tools: available" in prompt
    assert "Current-state tools: unavailable" in prompt
    assert "--- DIFF (unified) ---" in prompt


def test_build_prompt_handles_missing_diff():
    prompt = build_prompt(
        ghsa="GHSA-xxxx-xxxx-xxxx",
        repo_url="https://github.com/test/test",
        commit="abc123",
        has_previous=False,
        has_current=True,
        diff_text="",
    )
    assert "GHSA-xxxx-xxxx-xxxx" in prompt
    assert "unavailable (no parent commit)" in prompt
    assert "Current-state tools: available" in prompt
    assert "--- DIFF (unified) ---" not in prompt


def test_build_prompt_json_structure():
    prompt = build_prompt(
        ghsa="GHSA-TEST",
        repo_url="https://github.com/test/repo",
        commit="abc123",
        has_previous=True,
        has_current=True,
        diff_text="",
    )
    
    # JSON schema should be present
    assert '"patch_risk"' in prompt
    assert '"current_risk"' in prompt
    assert '"reason"' in prompt
    assert '"poc"' in prompt
    # Risk levels should be documented
    assert "good" in prompt
    assert "low" in prompt
    assert "medium" in prompt
    assert "high" in prompt


def test_build_prompt_both_unavailable():
    prompt = build_prompt(
        ghsa="GHSA-9999",
        repo_url="https://github.com/test/repo",
        commit="xyz789",
        has_previous=False,
        has_current=False,
        diff_text="",
    )
    
    assert "unavailable" in prompt
    # Should mention both states
    assert "Previous-state tools" in prompt
    assert "Current-state tools" in prompt
