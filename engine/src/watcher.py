from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({
    ".py", ".pyi",
    ".js", ".mjs", ".cjs", ".jsx",
    ".ts", ".mts", ".tsx",
    ".rs",
    ".go",
    ".java",
    ".c", ".h",
    ".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".hh",
    ".cs",
    ".rb", ".rake", ".gemspec",
    ".php",
    ".sh", ".bash", ".zsh",
    ".html", ".htm",
    ".css", ".scss", ".less", ".sass",
    ".json",
    ".yaml", ".yml",
    ".toml",
    ".md", ".markdown",
})


class _DebouncedHandler(FileSystemEventHandler):
    """
    Collects file change events and fires a batched callback after a debounce window.

    _pending: set[str] — Accumulated file paths waiting to be flushed.
    _lock: threading.Lock — Guards _pending and _timer.
    _timer: threading.Timer | None — Active debounce timer.
    _debounce_seconds: float — Quiet period before flush.
    _callback: Callable[[list[str]], None] — Called with batch of changed paths.
    """

    def __init__(self, debounce_seconds: float, callback: Callable[[list[str]], None]):
        """
        debounce_seconds: float — Seconds to wait after last event before flushing.
        callback: Callable[[list[str]], None] — Receives deduplicated list of changed file paths.
        """
        super().__init__()
        self._pending: set[str] = set()
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._debounce_seconds = debounce_seconds
        self._callback = callback

    def on_any_event(self, event: FileSystemEvent) -> None:
        """
        event: FileSystemEvent — Watchdog filesystem event.
        """
        if event.is_directory:
            return

        src = event.src_path
        if not self._is_supported(src):
            return

        with self._lock:
            self._pending.add(str(Path(src).resolve()))

            if self._timer is not None:
                self._timer.cancel()

            self._timer = threading.Timer(self._debounce_seconds, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self) -> None:
        with self._lock:
            if not self._pending:
                return
            batch = sorted(self._pending)
            self._pending.clear()
            self._timer = None

        self._callback(batch)

    def _is_supported(self, path: str) -> bool:
        """
        path: str — File path to check.
        Returns: bool — True if file extension is in SUPPORTED_EXTENSIONS.
        """
        ext = Path(path).suffix.lower()
        return ext in SUPPORTED_EXTENSIONS

    def cancel(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._pending.clear()


class FileWatcher:
    """
    Watches a directory for file changes and triggers incremental re-indexing.

    _directory: Path — Watched directory (resolved absolute).
    _project_name: str | None — Manual project name override.
    _debounce_seconds: float — Debounce window for batching events.
    _observer: Observer | None — Watchdog observer instance.
    _handler: _DebouncedHandler | None — Event handler with debounce logic.
    _on_refresh: Callable[[list[str]], None] | None — Callback for refresh batches.
    _on_error: Callable[[Exception], None] | None — Callback for errors during refresh.
    _running: bool — True while watcher is active.
    """

    def __init__(
        self,
        directory: str | Path,
        project_name: Optional[str] = None,
        debounce_seconds: float = 2.0,
        on_refresh: Optional[Callable[[list[str]], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        """
        directory: str | Path — Directory to watch.
        project_name: str | None — Manual project name override for indexing.
        debounce_seconds: float — Seconds to wait after last change before triggering refresh.
        on_refresh: Callable[[list[str]], None] | None — Called with batch of refreshed file paths.
        on_error: Callable[[Exception], None] | None — Called when refresh raises an exception.
        """
        self._directory = Path(directory).resolve()
        self._project_name = project_name
        self._debounce_seconds = debounce_seconds
        self._observer: Optional[Observer] = None
        self._handler: Optional[_DebouncedHandler] = None
        self._on_refresh = on_refresh
        self._on_error = on_error
        self._running = False

    @property
    def directory(self) -> Path:
        return self._directory

    @property
    def running(self) -> bool:
        return self._running

    def start(self, refresh_fn: Callable[[list[str], Optional[str]], None]) -> None:
        """
        Start watching. Calls refresh_fn(file_paths, project_name) on each debounced batch.

        refresh_fn: Callable[[list[str], str | None], None] — Function to call with changed paths.
        """
        if self._running:
            return

        def _on_batch(paths: list[str]) -> None:
            existing = [p for p in paths if Path(p).is_file()]
            if not existing:
                return
            try:
                refresh_fn(existing, self._project_name)
                if self._on_refresh:
                    self._on_refresh(existing)
            except Exception as exc:
                if self._on_error:
                    self._on_error(exc)
                else:
                    print(f"[watcher] refresh failed: {exc}")

        self._handler = _DebouncedHandler(self._debounce_seconds, _on_batch)
        self._observer = Observer()
        self._observer.schedule(self._handler, str(self._directory), recursive=True)
        self._observer.daemon = True
        self._observer.start()
        self._running = True

    def stop(self) -> None:
        """
        Stop watching and clean up resources.
        """
        if not self._running:
            return

        if self._handler:
            self._handler.cancel()

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5.0)

        self._observer = None
        self._handler = None
        self._running = False

    def run_forever(self, refresh_fn: Callable[[list[str], Optional[str]], None]) -> None:
        """
        Start watching and block until KeyboardInterrupt.

        refresh_fn: Callable[[list[str], str | None], None] — Function to call with changed paths.
        """
        self.start(refresh_fn)
        try:
            while self._running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
