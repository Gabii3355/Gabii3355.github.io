import os

from dotenv import load_dotenv

load_dotenv()

print("Checking Python packages...")

packages = [
    ("streamlit", "Streamlit"),
    ("pymupdf", "PyMuPDF"),
    ("chromadb", "ChromaDB"),
    ("sentence_transformers", "SentenceTransformers"),
    ("torch", "PyTorch"),
    ("groq", "Groq SDK"),
]

failed = False

for module_name, display_name in packages:
    try:
        __import__(module_name)
        print(f"OK: {display_name}")
    except Exception as exc:
        failed = True
        print(f"ERROR: {display_name}: {exc}")

if os.getenv("GROQ_API_KEY"):
    print("OK: GROQ_API_KEY found")
else:
    failed = True
    print("ERROR: GROQ_API_KEY is missing")

if failed:
    raise SystemExit("\nSetup check failed.")

print("\nEverything looks ready.")
