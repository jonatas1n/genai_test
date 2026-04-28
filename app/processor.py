import logging
from collections import Counter

logger = logging.getLogger(__name__)

TOP_N = 5
SUMMARY_WORD_LIMIT = 50


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


def generate_summary(text: str, word_limit: int = SUMMARY_WORD_LIMIT) -> str:
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    summary = ""
    for sentence in sentences:
        candidate = f"{summary}{sentence}. " if summary else f"{sentence}. "
        if len(candidate.split()) > word_limit:
            break
        summary = candidate
    return summary.strip() if summary else " ".join(text.split()[:word_limit])


def aggregate_results(documents: list[dict], top_n: int = TOP_N) -> dict:
    logger.debug("Aggregating results for %d document(s).", len(documents))

    total_words = 0
    total_lines = 0
    total_chars = 0
    merged_counter = Counter()
    files_processed: list[str] = []
    full_text_parts: list[str] = []

    for document in documents:
        metrics = parse_text_metrics(document["content"])
        total_words += metrics["total_words"]
        total_lines += metrics["total_lines"]
        total_chars += metrics["total_chars"]
        merged_counter.update(metrics["word_counter"])
        files_processed.append(document["name"])
        full_text_parts.append(document["content"])
        logger.debug("Parsed '%s': %d words.", document["name"], metrics["total_words"])

    most_frequent_words = [word for word, _ in merged_counter.most_common(top_n)]
    summary = generate_summary(" ".join(full_text_parts))

    logger.debug(
        "Aggregation complete. Total words: %d, files: %d.",
        total_words,
        len(files_processed),
    )

    return {
        "total_words": total_words,
        "total_lines": total_lines,
        "total_chars": total_chars,
        "most_frequent_words": most_frequent_words,
        "files_processed": files_processed,
        "summary": summary,
    }
