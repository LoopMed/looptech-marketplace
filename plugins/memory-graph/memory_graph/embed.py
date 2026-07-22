"""Local embedding backend (fastembed / ONNX). No network calls at query time.

The model weights (ONNX) are downloaded once by fastembed on first use and
cached on disk. After that first download, embedding is 100% local — no data
ever leaves the machine.
"""

from __future__ import annotations

import os

import numpy as np

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384


class Embedder:
    """Wraps fastembed's TextEmbedding with a stable, simple interface."""

    def __init__(self, model_name: str = MODEL_NAME, cache_dir: str | None = None):
        from fastembed import TextEmbedding

        cache_dir = cache_dir or os.environ.get("MEMORY_GRAPH_CACHE_DIR")
        kwargs = {}
        if cache_dir:
            kwargs["cache_dir"] = cache_dir
        self._model = TextEmbedding(model_name=model_name, **kwargs)
        self.dim = EMBED_DIM

    def embed(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts. Returns an (N, dim) float32 array."""
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vectors = list(self._model.embed(texts))
        return np.asarray(vectors, dtype=np.float32)

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]
