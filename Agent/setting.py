"""Optional embedding utilities; not imported by the web app.

Historical indexes have no build metadata. Use the same embedding model and
dimension used to build an index; do not mix OpenAI and E5 embeddings.
"""

import json
from functools import lru_cache

import config


def get_openai_embedding(text):
    import openai
    openai.api_key = config.api_key
    response = openai.Embedding.create(input=text, model="text-embedding-ada-002")
    return response["data"][0]["embedding"]


@lru_cache(maxsize=1)
def get_siamese_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("intfloat/multilingual-e5-large-instruct")


def get_siamese_embedding(text):
    return get_siamese_model().encode([text])[0]


def load_departments_from_json(file_path):
    import chardet
    raw = file_path.read_bytes()
    encoding = chardet.detect(raw)["encoding"] or "utf-8"
    data = json.loads(raw.decode(encoding))
    return [item.get("학과명") or item.get("학과") for item in data if item.get("학과명") or item.get("학과")]


def load_department_index():
    import faiss
    return faiss.read_index(str(config.DATA_DIR / "index_file_for_department.index"))
