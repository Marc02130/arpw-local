from __future__ import annotations

from app.config import settings

_model = None
EMBED_BATCH = 32


def uses_stub_embeddings() -> bool:
    return settings.EMBEDDING_PROVIDER == "stub"


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding(model_name=settings.EMBEDDING_MODEL)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if uses_stub_embeddings():
        return [[0.01] * settings.EMBEDDING_DIM for _ in texts]
    model = _get_model()
    out: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH):
        batch = texts[start : start + EMBED_BATCH]
        out.extend(list(map(float, vec)) for vec in model.embed(batch))
    return out
