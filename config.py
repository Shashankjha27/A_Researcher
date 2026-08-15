from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

NLI_THRESHOLD = 0.7
SMALL_SAMPLE_N = 30
NLI_MODEL = "MoritzLaurer/deberta-v3-base-zeroshot-v2"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_PROVIDER = "ollama"
OLLAMA_BASE_URL = "http://localhost:11434"
LLM_MODEL = "hf.co/unsloth/Qwen2.5-Coder-3B-Instruct-GGUF:Q4_K_M"
CONTRIEVER_MODEL = "facebook/contriever"


DATA_IN = BASE_DIR / "data" / "in"
DATA_OUT = BASE_DIR / "data" / "out"

DATA_DIRS = [DATA_IN, DATA_OUT]

HOST = "127.0.0.1"
PORT = 8000
