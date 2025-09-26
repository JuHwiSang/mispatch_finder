from mispatch_finder.core.toolset import describe_available_tools


def test_describe_available_tools_matrix():
    m = describe_available_tools(True, False)
    assert m == {"previous/repo": True, "current/repo": False}
    m2 = describe_available_tools(False, True)
    assert m2 == {"previous/repo": False, "current/repo": True}

