from pathlib import Path

import pymupdf


def extract_pages_from_pdf(
    pdf_path: Path,
    source_name: str | None = None,
) -> list[dict]:
    """
    Extract text page by page so every later chunk keeps
    the source PDF filename and physical PDF page number.
    """
    source_name = source_name or pdf_path.name
    pages = []

    with pymupdf.open(pdf_path) as document:
        for page_index, page in enumerate(document):
            text = page.get_text("text", sort=True).strip()

            if text:
                pages.append(
                    {
                        "source": source_name,
                        "page": page_index + 1,
                        "text": text,
                    }
                )

    return pages
