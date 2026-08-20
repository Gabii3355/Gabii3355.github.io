import os

from groq import Groq


MAX_CONTEXT_CHARS = 16000


def _format_context(
    retrieved_chunks: list[dict],
) -> str:
    sections = []
    used_chars = 0

    for item in retrieved_chunks:
        source = item["metadata"]["source"]
        page = item["metadata"]["page"]
        text = item["text"]

        section = (
            f"[SOURCE: {source}, PAGE: {page}]\n"
            f"{text}\n"
        )

        if (
            used_chars + len(section)
            > MAX_CONTEXT_CHARS
        ):
            break

        sections.append(section)
        used_chars += len(section)

    return "\n---\n".join(sections)


def answer_question(
    question: str,
    retrieved_chunks: list[dict],
    model: str | None = None,
) -> str:
    if not retrieved_chunks:
        return (
            "I could not retrieve any relevant passages "
            "from the indexed papers."
        )

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY was not found. "
            "Add it to the .env file."
        )

    model = (
        model
        or os.getenv(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile",
        )
    )

    client = Groq(api_key=api_key)

    context = _format_context(
        retrieved_chunks
    )

    system_prompt = """
You are a scientific literature assistant.

Answer ONLY from the supplied context.
Do not use outside knowledge to fill gaps.

If the supplied context does not support an answer,
say that the indexed papers do not contain enough
information.

Every factual claim should be accompanied by a citation
in this exact format:

[filename.pdf, p. X]

Keep the answer concise but scientifically precise.

If multiple papers disagree, describe the disagreement
and cite the relevant sources.
""".strip()

    user_prompt = f"""
QUESTION:
{question}

CONTEXT:
{context}
""".strip()

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.1,
    )

    content = completion.choices[0].message.content

    if not content:
        return "Groq returned an empty response."

    return content
