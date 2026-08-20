import os
import re
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader
from rank_bm25 import BM25Okapi


load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError("No GROQ_API_KEY in .env file")


PAPERS_DIR = Path("data/papers")


def read_pdfs():
    documents = []

    pdf_files = list(PAPERS_DIR.glob("*.pdf"))

    if not pdf_files:
        raise FileNotFoundError(
            "No pdf file found in data/papers/"
        )

    for pdf_path in pdf_files:
        print(f"Loading: {pdf_path.name}")

        reader = PdfReader(pdf_path)

        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text()

            if text:
                documents.append(
                    {
                        "text": text,
                        "source": pdf_path.name,
                        "page": page_number,
                    }
                )

    return documents


def split_into_chunks(documents, chunk_size=1200):
    chunks = []

    for document in documents:
        text = document["text"]

        for start in range(0, len(text), chunk_size):
            chunk = text[start:start + chunk_size].strip()

            if chunk:
                chunks.append(
                    {
                        "text": chunk,
                        "source": document["source"],
                        "page": document["page"],
                    }
                )

    return chunks


def tokenize(text):
    return re.findall(r"\w+", text.lower())


def create_bm25(chunks):
    tokenized_chunks = [
        tokenize(chunk["text"])
        for chunk in chunks
    ]

    return BM25Okapi(tokenized_chunks)


def retrieve(question, bm25, chunks, top_k=4):
    tokenized_question = tokenize(question)

    scores = bm25.get_scores(tokenized_question)

    best_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )[:top_k]

    return [chunks[i] for i in best_indices]


def ask_groq(question, retrieved_chunks):
    client = Groq(api_key=API_KEY)

    context_parts = []

    for chunk in retrieved_chunks:
        context_parts.append(
            f"""
SOURCE: {chunk['source']}
PAGE: {chunk['page']}

{chunk['text']}
"""
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
You are a scientific literature assistant.

Answer the question only using the context provided below.

If the answer cannot be found in the context, say:
"I could not find this information in the provided documents."

When possible, mention the source file and page number.

CONTEXT:

{context}

QUESTION:

{question}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content


def main():

    print()
    print("Scientific Literature Assistant")
    print("=" * 40)

    documents = read_pdfs()

    chunks = split_into_chunks(documents)

    print(f"Number of fragments: {len(chunks)}")

    bm25 = create_bm25(chunks)

    print()
    print("RAG is ready.")
    print("Write 'exit' to finish.")

    while True:

        print()

        question = input("Write question: ")

        if question.lower() == "exit":
            break

        retrieved_chunks = retrieve(
            question,
            bm25,
            chunks,
        )

        answer = ask_groq(
            question,
            retrieved_chunks,
        )

        print()
        print("ANSWER:")
        print(answer)

        print()
        print("FOUND FRAGMENTS:")

        for i, chunk in enumerate(
            retrieved_chunks,
            start=1,
        ):

            print()
            print(
                f"{i}. {chunk['source']} "
                f"| page {chunk['page']}"
            )

            print(chunk["text"])
            print("...")


if __name__ == "__main__":
    main()
