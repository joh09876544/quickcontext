from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import numpy as np


DEFAULT_MODEL_REPO = "lightonai/answerai-colbert-small-v1-onnx"
DEFAULT_EMBEDDING_DIM = 96
DEFAULT_MAX_LENGTH = 512
QUERY_PREFIX = "[Q] "
DOC_PREFIX = "[D] "


@dataclass(frozen=True, slots=True)
class RerankResult:
    """
    Single reranked result.

    index: int — Original index in the input list.
    score: float — MaxSim score from ColBERT reranking.
    """

    index: int
    score: float


class ColBERTReranker:
    """
    ColBERT reranker using ONNX Runtime for fast CPU inference.

    Uses answerai-colbert-small-v1 (96-dim, 33M params) with INT8 quantization.
    Computes MaxSim scoring: for each query token, find max cosine similarity
    across all document tokens, then sum.

    _session: onnxruntime.InferenceSession — ONNX model session.
    _tokenizer: tokenizers.Tokenizer — HuggingFace fast tokenizer.
    _max_length: int — Maximum token sequence length.
    _embedding_dim: int — Token embedding dimensionality.
    """

    def __init__(
        self,
        model_dir: Optional[str] = None,
        model_repo: str = DEFAULT_MODEL_REPO,
        use_int8: bool = True,
        max_length: int = DEFAULT_MAX_LENGTH,
    ):
        """
        model_dir: Optional[str] — Local directory with ONNX model files. Auto-downloads if None.
        model_repo: str — HuggingFace repo ID for auto-download.
        use_int8: bool — Use INT8 quantized model (faster, slightly less accurate).
        max_length: int — Maximum token sequence length.
        """
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self._max_length = max_length
        self._embedding_dim = DEFAULT_EMBEDDING_DIM

        model_path = self._resolve_model_path(model_dir, model_repo, use_int8)
        tokenizer_path = self._resolve_tokenizer_path(model_dir, model_repo)

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.intra_op_num_threads = 4
        sess_options.inter_op_num_threads = 1

        self._session = ort.InferenceSession(
            str(model_path),
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )

        self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self._tokenizer.enable_truncation(max_length=max_length)
        self._tokenizer.enable_padding(length=max_length)

    @staticmethod
    def _resolve_model_path(
        model_dir: Optional[str],
        model_repo: str,
        use_int8: bool,
    ) -> Path:
        """
        model_dir: Optional[str] — Local model directory.
        model_repo: str — HuggingFace repo for download.
        use_int8: bool — Whether to use INT8 quantized model.
        Returns: Path — Resolved path to ONNX model file.
        """
        filename = "model_int8.onnx" if use_int8 else "model.onnx"

        if model_dir:
            path = Path(model_dir) / filename
            if path.exists():
                return path

        from huggingface_hub import hf_hub_download
        return Path(hf_hub_download(repo_id=model_repo, filename=filename))

    @staticmethod
    def _resolve_tokenizer_path(
        model_dir: Optional[str],
        model_repo: str,
    ) -> Path:
        """
        model_dir: Optional[str] — Local model directory.
        model_repo: str — HuggingFace repo for download.
        Returns: Path — Resolved path to tokenizer.json.
        """
        if model_dir:
            path = Path(model_dir) / "tokenizer.json"
            if path.exists():
                return path

        from huggingface_hub import hf_hub_download
        return Path(hf_hub_download(repo_id=model_repo, filename="tokenizer.json"))

    def _encode_batch(self, texts: list[str]) -> np.ndarray:
        """
        Encode a batch of texts into token-level embeddings.

        texts: list[str] — Input texts to encode.
        Returns: np.ndarray — Shape (batch, seq_len, embedding_dim).
        """
        encodings = self._tokenizer.encode_batch(texts)

        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        token_type_ids = np.zeros_like(input_ids, dtype=np.int64)

        outputs = self._session.run(
            None,
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            },
        )

        embeddings = outputs[0]
        mask_3d = attention_mask[:, :, np.newaxis].astype(np.float32)
        embeddings = embeddings * mask_3d

        norms = np.linalg.norm(embeddings, axis=-1, keepdims=True)
        norms = np.where(norms < 1e-12, 1.0, norms)
        embeddings = embeddings / norms

        return embeddings

    def _maxsim(self, query_emb: np.ndarray, doc_emb: np.ndarray) -> float:
        """
        Compute MaxSim score between query and document embeddings.

        For each query token, find the maximum cosine similarity across all
        document tokens, then sum those maximums.

        query_emb: np.ndarray — Shape (query_tokens, dim), L2-normalized.
        doc_emb: np.ndarray — Shape (doc_tokens, dim), L2-normalized.
        Returns: float — MaxSim score.
        """
        sim_matrix = query_emb @ doc_emb.T
        max_sims = sim_matrix.max(axis=1)
        return float(max_sims.sum())

    def rerank(
        self,
        query: str,
        documents: Sequence[str],
        top_k: Optional[int] = None,
        batch_size: int = 16,
    ) -> list[RerankResult]:
        """
        Rerank documents by ColBERT MaxSim relevance to query.

        query: str — Search query.
        documents: Sequence[str] — Documents to rerank.
        top_k: Optional[int] — Return only top K results. None = return all.
        batch_size: int — Batch size for document encoding.
        Returns: list[RerankResult] — Reranked results sorted by score descending.
        """
        if not documents:
            return []

        query_text = QUERY_PREFIX + query
        query_emb = self._encode_batch([query_text])[0]

        query_mask = np.any(query_emb != 0, axis=-1)
        query_emb = query_emb[query_mask]

        scores: list[tuple[int, float]] = []

        for batch_start in range(0, len(documents), batch_size):
            batch_end = min(batch_start + batch_size, len(documents))
            batch_texts = [DOC_PREFIX + d for d in documents[batch_start:batch_end]]
            batch_embs = self._encode_batch(batch_texts)

            for i, doc_emb in enumerate(batch_embs):
                doc_mask = np.any(doc_emb != 0, axis=-1)
                doc_emb_masked = doc_emb[doc_mask]

                if doc_emb_masked.shape[0] == 0:
                    scores.append((batch_start + i, 0.0))
                    continue

                score = self._maxsim(query_emb, doc_emb_masked)
                scores.append((batch_start + i, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        if top_k is not None:
            scores = scores[:top_k]

        return [RerankResult(index=idx, score=sc) for idx, sc in scores]
