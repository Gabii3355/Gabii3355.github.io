import re


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = 1400,
    overlap: int = 250,
) -> list[str]:
    """
    Character-based chunking that tries to split on paragraph
    or sentence boundaries while keeping a small overlap.
    """
    text = clean_text(text)

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        max_end = min(start + chunk_size, len(text))
        end = max_end

        if max_end < len(text):
            search_start = start + int(chunk_size * 0.6)

            candidates = [
                text.rfind("\n\n", search_start, max_end),
                text.rfind(". ", search_start, max_end),
                text.rfind("; ", search_start, max_end),
            ]

            best_break = max(candidates)

            if best_break > start:
                end = best_break + 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - overlap, start + 1)

    return chunks


def chunk_pages(pages: list[dict]) -> list[dict]:
    output = []

    for page in pages:
        for chunk_index, text_chunk in enumerate(
            chunk_text(page["text"])
        ):
            output.append(
                {
                    "text": text_chunk,
                    "metadata": {
                        "source": page["source"],
                        "page": int(page["page"]),
                        "chunk": int(chunk_index),
                    },
                }
            )

    return output
