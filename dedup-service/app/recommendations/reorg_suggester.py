def suggest_action(duplicate_type: str, member_count: int, average_similarity: float) -> tuple[str, str]:
    if duplicate_type == "file_exact":
        return "归档重复文件", "high"
    if duplicate_type == "text_exact":
        return "保留主版本，归档正文重复文件", "high"
    if duplicate_type == "chunk_exact" and member_count >= 3:
        return "抽取公共章节", "medium"
    if duplicate_type == "chunk_near" and average_similarity >= 0.9:
        return "合并近重复章节", "medium"
    return "人工复核或保留观察", "low"
