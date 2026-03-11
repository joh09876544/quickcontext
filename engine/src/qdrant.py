from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse, ResponseHandlingException
from engine.src.config import QdrantConfig


class QdrantConnection:
    """
    Manages a single QdrantClient lifecycle: connect, health check, close.

    _config: QdrantConfig — Connection parameters.
    _client: QdrantClient | None — Active client instance.
    """

    def __init__(self, config: QdrantConfig):
        """
        config: QdrantConfig — Qdrant connection configuration.
        """
        self._config = config
        self._client: QdrantClient | None = None

    def connect(self) -> QdrantClient:
        """
        Create and return a QdrantClient. Reuses existing connection if alive.

        Returns: QdrantClient — Connected client instance.
        Raises: ConnectionError — If Qdrant is unreachable.
        """
        if self._client is not None:
            return self._client

        try:
            self._client = QdrantClient(
                host=self._config.host,
                port=self._config.port,
                grpc_port=self._config.grpc_port,
                prefer_grpc=self._config.prefer_grpc,
                api_key=self._config.api_key,
                timeout=self._config.timeout,
            )
            self._client.get_collections()
        except (UnexpectedResponse, ResponseHandlingException, Exception) as exc:
            self._client = None
            raise ConnectionError(
                f"Failed to connect to Qdrant at {self._config.url}: {exc}"
            ) from exc

        return self._client

    @property
    def client(self) -> QdrantClient:
        """
        Returns: QdrantClient — Active client, connecting if needed.
        Raises: ConnectionError — If not connected and connection fails.
        """
        if self._client is None:
            return self.connect()
        return self._client

    def is_alive(self) -> bool:
        """
        Check if the Qdrant server is reachable.

        Returns: bool — True if server responds to health check.
        """
        if self._client is None:
            return False
        try:
            self._client.get_collections()
            return True
        except Exception:
            return False

    def close(self) -> None:
        """
        Close the client connection and release resources.
        """
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "QdrantConnection":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __repr__(self) -> str:
        alive = self.is_alive() if self._client else False
        return f"QdrantConnection(url={self._config.url!r}, alive={alive})"
