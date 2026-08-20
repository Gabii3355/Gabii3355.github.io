import os
import re
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader
from rank_bm25 import BM25Plus


# ==================================================
# CONFIG
# ==================================================

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
PAPERS_DIR = Path("data/papers")
MODEL_NAME = "openai/gpt-oss-20b"


st.set_page_config(
    page_title="Scientific Literature Assistant",
    page_icon="📚",
    layout="centered",
)


# ==================================================
# QUERY EXPANSION
# ==================================================

QUERY_EXPANSIONS = {
    "objective": [
        "aim",
        "aimed",
        "goal",
        "purpose",
        "sought",
    ],

    "aim": [
        "objective",
        "goal",
        "purpose",
        "sought",
    ],

    "method": [
        "methods",
        "methodology",
        "analysis",
        "workflow",
        "approach",
    ],

    "methods": [
        "method",
        "methodology",
        "analysis",
        "workflow",
        "approach",
    ],

    "result": [
        "results",
        "finding",
        "findings",
        "observed",
    ],

    "results": [
        "result",
        "finding",
        "findings",
        "observed",
    ],

    "conclusion": [
        "conclusions",
        "finding",
        "findings",
        "suggest",
        "demonstrate",
    ],

    "conclusions": [
        "conclusion",
        "finding",
        "findings",
        "suggest",
        "demonstrate",
    ],
}


def expand_query(tokens):

    expanded = list(tokens)

    for token in tokens:

        if token in QUERY_EXPANSIONS:

            expanded.extend(
                QUERY_EXPANSIONS[token]
            )

    # Remove duplicates while preserving order
    return list(
        dict.fromkeys(expanded)
    )


# ==================================================
# TEXT CLEANING
# ==================================================

def normalize_text(text):
    """
    Clean text extracted from PDF.
    """

    # Example:
    # "signa-\ntures" -> "signatures"
    text = re.sub(
        r"-\s*\n\s*",
        "",
        text,
    )

    # Remaining line breaks -> spaces
    text = text.replace(
        "\n",
        " ",
    )

    # Repeated whitespace -> one space
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# ==================================================
# PDF READING
# ==================================================

def read_pdfs():

    documents = []

    pdf_files = sorted(
        PAPERS_DIR.glob("*.pdf")
    )

    if not pdf_files:

        raise FileNotFoundError(
            "No PDF files found in data/papers/"
        )

    for pdf_path in pdf_files:

        reader = PdfReader(
            pdf_path
        )

        for page_number, page in enumerate(
            reader.pages,
            start=1,
        ):

            text = (
                page.extract_text()
                or ""
            )

            text = normalize_text(
                text
            )

            if text:

                documents.append(
                    {
                        "text": text,
                        "source": pdf_path.name,
                        "page": page_number,
                    }
                )

    return documents


# ==================================================
# CHUNKING
# ==================================================

def split_into_chunks(
    documents,
    chunk_size=220,
    overlap=60,
):
    """
    Split documents into overlapping,
    word-based chunks.
    """

    if overlap >= chunk_size:

        raise ValueError(
            "overlap must be smaller than chunk_size"
        )

    chunks = []

    step = (
        chunk_size
        - overlap
    )

    for document in documents:

        words = (
            document["text"]
            .split()
        )

        for start in range(
            0,
            len(words),
            step,
        ):

            chunk_words = words[
                start:
                start + chunk_size
            ]

            # Ignore very short fragments
            if len(chunk_words) < 30:
                continue

            chunk_text = " ".join(
                chunk_words
            )

            chunks.append(
                {
                    "text": chunk_text,
                    "source": document["source"],
                    "page": document["page"],
                }
            )

            if (
                start + chunk_size
                >= len(words)
            ):
                break

    return chunks


# ==================================================
# TOKENIZATION
# ==================================================

STOPWORDS = {
    "the", "a", "an", "and", "or",
    "of", "to", "in", "on", "for",
    "with", "was", "were", "is", "are",
    "be", "been", "this", "that", "these",
    "those", "by", "from", "as", "at",
    "it", "its", "we", "our", "they",
    "their", "what", "which", "who",
    "how", "when", "where",
}


def tokenize(text):

    tokens = re.findall(
        r"[a-zA-Z0-9]+",
        text.lower(),
    )

    return [
        token
        for token in tokens
        if (
            token not in STOPWORDS
            and len(token) > 2
        )
    ]


# ==================================================
# BM25 INDEX
# ==================================================

def create_bm25(chunks):

    tokenized_chunks = [
        tokenize(
            chunk["text"]
        )
        for chunk in chunks
    ]

    return BM25Plus(
        tokenized_chunks
    )


# ==================================================
# LOW VALUE CHUNK FILTER
# ==================================================

def is_low_value_chunk(text):
    """
    Detect bibliography, acknowledgements,
    and other low-value fragments.
    """

    text_lower = (
        text.lower()
    )

    low_value_patterns = [
        "references",
        "bibliography",
        "acknowledgments",
        "acknowledgements",
        "funded by",
        "doi:",
        "pmid:",
    ]

    matches = sum(
        pattern in text_lower
        for pattern in low_value_patterns
    )

    doi_count = (
        text_lower.count(
            "doi:"
        )
    )

    pmid_count = (
        text_lower.count(
            "pmid:"
        )
    )

    if matches >= 2:
        return True

    if (
        doi_count >= 3
        or pmid_count >= 3
    ):
        return True

    return False


# ==================================================
# DUPLICATE DETECTION
# ==================================================

def chunk_similarity(
    text1,
    text2,
):
    """
    Calculate Jaccard similarity between
    two chunks.
    """

    words1 = set(
        tokenize(text1)
    )

    words2 = set(
        tokenize(text2)
    )

    if (
        not words1
        or not words2
    ):
        return 0.0

    intersection = len(
        words1 & words2
    )

    union = len(
        words1 | words2
    )

    return (
        intersection
        / union
    )


# ==================================================
# LOCAL RETRIEVAL
# BM25PLUS + HEURISTIC RERANKING
# ==================================================

def retrieve(
    question,
    bm25,
    chunks,
    top_k=10,
    candidate_k=30,
):

    original_question_tokens = tokenize(
        question
    )

    if not original_question_tokens:
        return []

    question_tokens = expand_query(
        original_question_tokens
    )

    scores = bm25.get_scores(
        question_tokens
    )

    candidate_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )[:candidate_k]

    query_terms = set(
        question_tokens
    )

    query_bigrams = set(
        zip(
            original_question_tokens,
            original_question_tokens[1:],
        )
    )

    objective_terms = {
        "objective",
        "aim",
        "aimed",
        "goal",
        "purpose",
    }

    objective_question = bool(
        objective_terms
        & set(
            original_question_tokens
        )
    )

    locally_reranked = []

    for index in candidate_indices:

        chunk = chunks[index]

        # Remove bibliography etc.
        if is_low_value_chunk(
            chunk["text"]
        ):
            continue

        chunk_tokens = tokenize(
            chunk["text"]
        )

        chunk_terms = set(
            chunk_tokens
        )

        common_terms = (
            query_terms
            & chunk_terms
        )

        coverage = (
            len(common_terms)
            / max(
                len(query_terms),
                1,
            )
        )

        chunk_bigrams = set(
            zip(
                chunk_tokens,
                chunk_tokens[1:],
            )
        )

        bigram_overlap = len(
            query_bigrams
            & chunk_bigrams
        )

        # Small bonus for early pages
        # when asking about study objective
        early_page_bonus = 0.0

        if objective_question:

            if chunk["page"] == 1:

                early_page_bonus = 2.0

            elif chunk["page"] == 2:

                early_page_bonus = 1.0

        bm25_score = float(
            scores[index]
        )

        retrieval_score = (
            bm25_score
            + (2.0 * coverage)
            + (0.5 * bigram_overlap)
            + early_page_bonus
        )

        locally_reranked.append(
            (
                retrieval_score,
                bm25_score,
                index,
            )
        )

    locally_reranked.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    selected = []

    pages_used = {}

    for (
        retrieval_score,
        bm25_score,
        index,
    ) in locally_reranked:

        chunk = chunks[index]

        page_key = (
            chunk["source"],
            chunk["page"],
        )

        # Maximum 2 chunks per page
        if pages_used.get(
            page_key,
            0,
        ) >= 2:
            continue

        # Remove near-duplicate chunks
        too_similar = False

        for existing_chunk in selected:

            similarity = chunk_similarity(
                chunk["text"],
                existing_chunk["text"],
            )

            if similarity > 0.60:

                too_similar = True
                break

        if too_similar:
            continue

        selected.append(
            {
                **chunk,
                "bm25_score": bm25_score,
                "retrieval_score": retrieval_score,
            }
        )

        pages_used[page_key] = (
            pages_used.get(
                page_key,
                0,
            )
            + 1
        )

        if len(selected) == top_k:
            break

    return selected


# ==================================================
# GROQ RERANKER
# ==================================================

def rerank_with_groq(
    question,
    candidate_chunks,
    top_k=4,
):
    """
    Ask Groq to select the passages
    that best answer the question.
    """

    if not candidate_chunks:
        return []

    if len(candidate_chunks) <= top_k:

        return [
            {
                **chunk,
                "llm_rank": rank,
            }

            for rank, chunk in enumerate(
                candidate_chunks,
                start=1,
            )
        ]

    if not API_KEY:

        raise ValueError(
            "GROQ_API_KEY is missing in .env"
        )

    client = Groq(
        api_key=API_KEY
    )

    candidate_blocks = []

    for number, chunk in enumerate(
        candidate_chunks,
        start=1,
    ):

        candidate_blocks.append(
            f"""
C{number}

SOURCE: {chunk['source']}
PAGE: {chunk['page']}

TEXT:
{chunk['text']}
"""
        )

    candidates_text = "\n\n".join(
        candidate_blocks
    )

    prompt = f"""
You are the reranking stage of a scientific
Retrieval-Augmented Generation system.

Do NOT answer the question.

Select the {top_k} candidate passages that provide
the strongest and most direct evidence for answering
the user's question.

Prioritize passages that:

1. directly address the question,

2. contain explicit factual evidence,

3. describe the study itself when the question is
   about its objective, methods, results or conclusions,

4. are sufficient to support an accurate answer.

Penalize passages that:

1. only share keywords with the question,

2. contain unrelated background,

3. are mainly references or acknowledgements,

4. are figure captions that do not directly help
   answer the question.

QUESTION:

{question}

CANDIDATE PASSAGES:

{candidates_text}

Return ONLY the candidate labels in ranked order,
separated by commas.

Example:

C3,C1,C7,C2

Do not add explanations.
"""

    response = (
        client
        .chat
        .completions
        .create(
            model=MODEL_NAME,

            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],

            temperature=0.0,
        )
    )

    raw_result = (
        response
        .choices[0]
        .message
        .content
        or ""
    )

    # Extract:
    # C3,C1,C7,C2
    selected_numbers = re.findall(
        r"C\s*(\d+)",
        raw_result.upper(),
    )

    selected_indices = []

    for number in selected_numbers:

        index = (
            int(number)
            - 1
        )

        if (
            0 <= index < len(candidate_chunks)
            and index not in selected_indices
        ):

            selected_indices.append(
                index
            )

        if len(selected_indices) == top_k:
            break

    # Fallback if Groq returns fewer
    # than top_k valid labels
    if len(selected_indices) < top_k:

        for index in range(
            len(candidate_chunks)
        ):

            if index not in selected_indices:

                selected_indices.append(
                    index
                )

            if len(selected_indices) == top_k:
                break

    return [
        {
            **candidate_chunks[index],
            "llm_rank": rank,
        }

        for rank, index in enumerate(
            selected_indices,
            start=1,
        )
    ]


# ==================================================
# GROQ ANSWER GENERATION
# WITH PRECISE SOURCE CITATIONS
# ==================================================

def ask_groq(
    question,
    retrieved_chunks,
):

    if not API_KEY:

        raise ValueError(
            "GROQ_API_KEY is missing in .env"
        )

    client = Groq(
        api_key=API_KEY
    )

    context_parts = []

    for number, chunk in enumerate(
        retrieved_chunks,
        start=1,
    ):

        citation = (
            f"[{chunk['source']}, "
            f"p. {chunk['page']}]"
        )

        context_parts.append(
            f"""
PASSAGE {number}

SOURCE: {chunk['source']}
PAGE: {chunk['page']}
ALLOWED CITATION: {citation}

TEXT:
{chunk['text']}
"""
        )

    context = "\n\n".join(
        context_parts
    )

    prompt = f"""
You are a scientific literature assistant.

Answer the user's question using ONLY the evidence
contained in the CONTEXT below.

STRICT EVIDENCE AND CITATION RULES:

1. Every factual claim in your answer must be supported
   by at least one retrieved passage.

2. Place the citation immediately after the sentence
   or paragraph that it supports.

3. Use ONLY the exact citations provided in the
   "ALLOWED CITATION" fields.

4. Never invent a filename, page number, citation,
   result, method, number or conclusion.

5. ONE SOURCE CLAIM PER SENTENCE:
   If different parts of an answer are supported by
   different pages, they MUST be written as separate
   sentences or separate paragraphs.

Example:

The study catalogued known and previously unreported
mutational signatures across large cancer WGS cohorts
[2022_Science.pdf, p. 5].

It also developed a practical approach for fitting
common and rare signatures in new samples
[2022_Science.pdf, p. 11].

6. Never combine two claims supported by different
   pages into one sentence followed by multiple citations.

   BAD:
   The study catalogued mutational signatures and
   developed FitMS
   [paper.pdf, p. 5] [paper.pdf, p. 11].

   GOOD:
   The study catalogued known and previously unreported
   mutational signatures
   [paper.pdf, p. 5].

   The authors also developed FitMS for identifying
   common and rare signatures
   [paper.pdf, p. 11].

7. Prefer direct evidence over interpretation.

8. Do not generalize a result from one specific analysis
   into a broader conclusion unless the retrieved passage
   explicitly supports that conclusion.

9. Do NOT use outside knowledge.

10. If the retrieved context does not contain enough
    evidence to answer the question, respond exactly:

"I could not find this information in the provided documents."

11. Keep the answer concise but complete.

12. Do NOT create a separate bibliography or Sources
    section in the answer. The application displays
    retrieved source passages below the answer.

13. Use one citation immediately after the claim it
   supports. Use multiple citations after one sentence
   ONLY when the exact same factual claim is independently
   supported by multiple passages.
   
FORMAT REQUIREMENT:

Write the answer as short evidence-based paragraphs.

Each paragraph should preferably contain one main factual
claim followed immediately by its citation.

When information comes from different pages, create
separate paragraphs for those pieces of information.
CONTEXT:

{context}

QUESTION:

{question}

Before returning your answer, verify that every factual
claim is supported by the passage identified in the
citation immediately following that claim.
"""

    response = (
        client
        .chat
        .completions
        .create(
            model=MODEL_NAME,

            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],

            temperature=0.0,
        )
    )

    return (
        response
        .choices[0]
        .message
        .content
    )


# ==================================================
# LOAD RAG
# ==================================================

@st.cache_resource
def load_rag():

    documents = read_pdfs()

    chunks = split_into_chunks(
        documents
    )

    bm25 = create_bm25(
        chunks
    )

    return (
        documents,
        chunks,
        bm25,
    )


# ==================================================
# STREAMLIT INTERFACE
# ==================================================

st.title(
    "📚 Scientific Literature Assistant"
)

st.write(
    "Ask questions about scientific papers stored "
    "in the `data/papers` folder."
)


try:

    documents, chunks, bm25 = (
        load_rag()
    )

    pdf_count = len(
        {
            document["source"]
            for document in documents
        }
    )

    st.success(
        f"RAG ready. "
        f"Loaded {pdf_count} PDF(s) "
        f"and {len(chunks)} text chunks."
    )

except Exception as error:

    st.error(
        "Could not load the documents."
    )

    st.exception(
        error
    )

    st.stop()


question = st.text_input(
    "Ask a question about the papers:"
)


if st.button("Ask"):

    if not question.strip():

        st.warning(
            "Enter a question first."
        )

    else:

        # ==================================================
        # STEP 1
        # BM25Plus local retrieval
        # ==================================================

        candidate_chunks = retrieve(
            question,
            bm25,
            chunks,
            top_k=10,
            candidate_k=30,
        )

        if not candidate_chunks:

            st.warning(
                "No relevant text fragments were found."
            )

        else:

            try:

                with st.spinner(
                    "Retrieving and reranking scientific evidence..."
                ):

                    # ==================================================
                    # STEP 2
                    # Groq semantic reranking
                    # ==================================================

                    try:

                        retrieved_chunks = rerank_with_groq(
                            question,
                            candidate_chunks,
                            top_k=4,
                        )

                        reranker_used = True

                    except Exception:

                        reranker_used = False

                        st.warning(
                            "Groq reranking failed, so the app "
                            "is using the local retrieval ranking."
                        )

                        retrieved_chunks = [
                            {
                                **chunk,
                                "llm_rank": rank,
                            }

                            for rank, chunk in enumerate(
                                candidate_chunks[:4],
                                start=1,
                            )
                        ]

                    # ==================================================
                    # STEP 3
                    # Final answer generation
                    # ==================================================

                    answer = ask_groq(
                        question,
                        retrieved_chunks,
                    )


                # ==================================================
                # ANSWER
                # ==================================================

                st.subheader(
                    "Answer"
                )

                # Markdown allows citations and
                # paragraphs to render cleanly.
                st.markdown(
                    answer
                )


                # ==================================================
                # FINAL SOURCES
                # ==================================================

                st.subheader(
                    "Sources"
                )

                if reranker_used:

                    st.caption(
                        "These passages were first retrieved "
                        "with BM25Plus and then reranked by Groq."
                    )

                else:

                    st.caption(
                        "These passages were selected using "
                        "the local BM25Plus retrieval ranking."
                    )


                for number, chunk in enumerate(
                    retrieved_chunks,
                    start=1,
                ):

                    with st.expander(
                        f"{number}. "
                        f"{chunk['source']} "
                        f"— page {chunk['page']}"
                    ):

                        st.caption(
                            f"Final rank: "
                            f"{chunk['llm_rank']} "
                            f"| Local retrieval score: "
                            f"{chunk['retrieval_score']:.2f} "
                            f"| BM25 raw score: "
                            f"{chunk['bm25_score']:.2f}"
                        )

                        st.write(
                            chunk["text"]
                        )


                # ==================================================
                # DEBUG VIEW
                # RESULTS BEFORE GROQ RERANKER
                # ==================================================

                with st.expander(
                    "Show candidates before Groq reranking"
                ):

                    for number, chunk in enumerate(
                        candidate_chunks,
                        start=1,
                    ):

                        st.markdown(
                            f"**Candidate {number}: "
                            f"{chunk['source']} "
                            f"— page {chunk['page']}**"
                        )

                        st.caption(
                            f"Local retrieval score: "
                            f"{chunk['retrieval_score']:.2f} "
                            f"| BM25 raw score: "
                            f"{chunk['bm25_score']:.2f}"
                        )

                        st.write(
                            chunk["text"]
                        )

                        st.divider()


            except Exception as error:

                st.error(
                    "An error occurred while processing the question."
                )

                st.exception(
                    error
                )
