from sarangbang import clean_reply


def test_plain_text():
    assert clean_reply("좋네요") == ("좋네요", None, False, [])


def test_reply_mark_and_pass():
    t, r, p, _ = clean_reply("(#3에 답장) 맞아요", "마포", ["마포", "은평"])
    assert (t, r, p) == ("맞아요", 3, False)
    assert clean_reply("(넘어감)")[2] is True


def test_copied_log_line_dropped():
    t, _, p, fixes = clean_reply("#2 은평: 걱정이네요\n저는 반가워요", "마포", ["마포", "은평"])
    assert t == "저는 반가워요" and not p
    assert any("옮겨 적은" in f for f in fixes)


def test_other_name_prefix_is_pass():
    assert clean_reply("은평: 그렇죠", "마포", ["마포", "은평"])[2] is True


def test_think_tags_removed():
    assert clean_reply("<think>음</think>좋아요")[0] == "좋아요"
