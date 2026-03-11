from typing import Sequence
import numpy as np

from engine.src.config import EmbeddingConfig
from engine.src.providers.base import EmbeddingProvider


def _get_fastembed_class():
    """
    Lazy-import fastembed TextEmbedding.

    Returns: type — The TextEmbedding class.
    """
    from fastembed import TextEmbedding
    return TextEmbedding


class FastEmbedProvider(EmbeddingProvider):
    """
    Local ONNX-based embedding provider via fastembed.
    No API keys required — fully offline.

    _model: TextEmbedding — Loaded fastembed model instance.
    """

    def __init__(self, config: EmbeddingConfig):
        """
        config: EmbeddingConfig — Must have provider="fastembed".
        """
        super().__init__(config)
        self._model = None

    def _ensure_model(self):
        """
        Lazy-load the fastembed model on first use.

        Returns: TextEmbedding — Loaded model instance.
        """
        if self._model is None:
            cls = _get_fastembed_class()
            self._model = cls(model_name=self._config.model)
        return self._model

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]:
        """
        Generate embeddings for a batch of texts using fastembed.

        texts: Sequence[str] — Input text strings.
        Returns: list[np.ndarray] — One embedding vector per input text.
        """
        model = self._ensure_model()
        return list(model.embed(
            documents=list(texts),
            batch_size=self._config.batch_size,
        ))

    def embed_single(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text using fastembed.

        text: str — Input text string.
        Returns: np.ndarray — Embedding vector.
        """
        model = self._ensure_model()
        results = list(model.embed(documents=[text], batch_size=1))
        return results[0]
