from collections import Counter


TOP_N = 5

def parse_text_metrics(text: str) -> dict:
    lines = text.splitlines()
    words = text.split()
    cleaned_words = [
        word.strip(".,;:!?()[]{}\"'").lower() for word in words if word.strip()
    ]

    return {
        "total_words": len(words),
        "total_lines": len(lines),
        "total_chars": len(text),
        "word_counter": Counter(cleaned_words),
    }


def aggregate_results(documents: list[dict], top_n: int = TOP_N) -> dict:
    total_words = 0
    total_lines = 0
    total_chars = 0
    merged_counter = Counter()
    files_processed: list[str] = []

    for document in documents:
        metrics = parse_text_metrics(document["content"])
        total_words += metrics["total_words"]
        total_lines += metrics["total_lines"]
        total_chars += metrics["total_chars"]
        merged_counter.update(metrics["word_counter"])
        files_processed.append(document["name"])

    most_frequent_words = [word for word, _ in merged_counter.most_common(top_n)]

    return {
        "total_words": total_words,
        "total_lines": total_lines,
        "total_chars": total_chars,
        "most_frequent_words": most_frequent_words,
        "files_processed": files_processed,
    }
