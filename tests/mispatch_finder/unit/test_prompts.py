from mispatch_finder.app.prompts import build_prompt


def test_build_prompt_includes_core_fields():
    prompt = build_prompt(
        ghsa="GHSA-1234-5678-9012",
        meta={"repo_url": "https://github.com/owner/repo", "commit": "deadbeef"},
        has_pre=True,
        has_post=False,
        diff_text="diff --git a/x b/x\n+1\n-2",
    )
    assert "GHSA-1234-5678-9012" in prompt
    assert "https://github.com/owner/repo" in prompt
    assert "deadbeef" in prompt
    assert "Pre-state tools: available" in prompt
    assert "Post-state tools: unavailable" in prompt
    assert "--- DIFF (unified) ---" in prompt

