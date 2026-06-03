from app.recommendations.reorg_suggester import suggest_action


def test_file_exact_suggestion() -> None:
    assert suggest_action("file_exact", 2, 1.0)[0] == "归档重复文件"


def test_text_exact_suggestion() -> None:
    assert suggest_action("text_exact", 2, 1.0)[0] == "保留主版本，归档正文重复文件"


def test_chunk_exact_many_members_suggestion() -> None:
    assert suggest_action("chunk_exact", 3, 1.0)[0] == "抽取公共章节"


def test_chunk_near_high_similarity_suggestion() -> None:
    assert suggest_action("chunk_near", 2, 0.93)[0] == "合并近重复章节"
