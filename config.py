import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

NLI_THRESHOLD = 0.7
SMALL_SAMPLE_N = 30
NLI_MODEL = "MoritzLaurer/deberta-v3-base-zeroshot-v2"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CONTRIEVER_MODEL = "facebook/contriever"

OLLAMA_BASE_URL = os.environ.get(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-5-haiku-latest")

DATA_IN = BASE_DIR / "data" / "in"
DATA_OUT = BASE_DIR / "data" / "out"

DATA_DIRS = [DATA_IN, DATA_OUT]

HOST = "127.0.0.1"
PORT = 8000
