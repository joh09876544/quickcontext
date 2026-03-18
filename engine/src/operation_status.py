from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from threading import Lock
from typing import Any
import uuid

from engine.src.sdk_models import IndexOperationSnapshot


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_operation_path(path: str) -> str:
    return str(path or "").replace("\\\\?\\", "")


@dataclass(slots=True)
class _OperationRecord:
    snapshot: IndexOperationSnapshot
    key: str


class OperationRegistry:
    def __init__(self, max_entries: int = 128) -> None:
        self._lock = Lock()
        self._records: dict[str, _OperationRecord] = {}
        self._active_by_key: dict[str, str] = {}
        self._order: list[str] = []
        self._max_entries = max_entries

    def start_or_attach(
        self,
        *,
        kind: str,
        path: str,
        project_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[IndexOperationSnapshot, bool]:
        normalized_path = _normalize_operation_path(path)
        key = self._make_key(kind=kind, path=normalized_path, project_name=project_name)
        with self._lock:
            active_id = self._active_by_key.get(key)
            if active_id and active_id in self._records:
                return self._records[active_id].snapshot, True

            snapshot = IndexOperationSnapshot(
                operation_id=uuid.uuid4().hex[:12],
                kind=kind,
                path=normalized_path,
                project_name=project_name,
                status="queued",
                current_stage="queued",
                message="Queued",
                created_at=_now_iso(),
                updated_at=_now_iso(),
            )
            if metadata:
                snapshot = replace(snapshot, **metadata)
            self._records[snapshot.operation_id] = _OperationRecord(snapshot=snapshot, key=key)
            self._active_by_key[key] = snapshot.operation_id
            self._order.append(snapshot.operation_id)
            self._prune_locked()
            return snapshot, False

    def mark_running(self, operation_id: str, *, stage: str, message: str) -> IndexOperationSnapshot:
        snapshot = self.get(operation_id)
        started_at = snapshot.started_at if snapshot is not None and snapshot.started_at else _now_iso()
        return self.update(
            operation_id,
            status="running",
            current_stage=stage,
            message=message,
            started_at=started_at,
        )

    def update(self, operation_id: str, **changes: Any) -> IndexOperationSnapshot:
        with self._lock:
            record = self._records[operation_id]
            snapshot = record.snapshot
            changes["updated_at"] = _now_iso()
            record.snapshot = replace(snapshot, **changes)
            return record.snapshot

    def complete(self, operation_id: str, *, final_stats: dict[str, Any], message: str = "Completed") -> IndexOperationSnapshot:
        with self._lock:
            record = self._records[operation_id]
            snapshot = replace(
                record.snapshot,
                status="completed",
                current_stage="completed",
                message=message,
                final_stats=final_stats,
                finished_at=_now_iso(),
                updated_at=_now_iso(),
            )
            record.snapshot = snapshot
            self._active_by_key.pop(record.key, None)
            return snapshot

    def fail(self, operation_id: str, *, error: str, stage: str = "failed", message: str = "Failed") -> IndexOperationSnapshot:
        with self._lock:
            record = self._records[operation_id]
            snapshot = replace(
                record.snapshot,
                status="failed",
                current_stage=stage,
                message=message,
                error=error,
                finished_at=_now_iso(),
                updated_at=_now_iso(),
            )
            record.snapshot = snapshot
            self._active_by_key.pop(record.key, None)
            return snapshot

    def get(self, operation_id: str) -> IndexOperationSnapshot | None:
        with self._lock:
            record = self._records.get(operation_id)
            return record.snapshot if record is not None else None

    def list(self, active_only: bool = False, limit: int = 20) -> list[IndexOperationSnapshot]:
        with self._lock:
            ordered = list(reversed(self._order[-limit:]))
            snapshots = [self._records[item].snapshot for item in ordered if item in self._records]
            if active_only:
                return [item for item in snapshots if item.status in {"queued", "running"}]
            return snapshots

    def get_for_target(self, *, kind: str, path: str, project_name: str) -> list[IndexOperationSnapshot]:
        normalized_path = _normalize_operation_path(path)
        key = self._make_key(kind=kind, path=normalized_path, project_name=project_name)
        with self._lock:
            operation_id = self._active_by_key.get(key)
            if operation_id and operation_id in self._records:
                return [self._records[operation_id].snapshot]
            for item in reversed(self._order):
                record = self._records.get(item)
                if record and record.key == key:
                    return [record.snapshot]
            return []

    def _prune_locked(self) -> None:
        while len(self._order) > self._max_entries:
            oldest = self._order.pop(0)
            record = self._records.get(oldest)
            if record and record.snapshot.status in {"queued", "running"}:
                self._order.append(oldest)
                break
            self._records.pop(oldest, None)

    @staticmethod
    def _make_key(*, kind: str, path: str, project_name: str) -> str:
        return f"{kind}|{project_name}|{path.lower()}"


class OperationProgressReporter:
    def __init__(self, registry: OperationRegistry, operation_id: str):
        self._registry = registry
        self._operation_id = operation_id
        self._lock = Lock()

    @property
    def operation_id(self) -> str:
        return self._operation_id

    def start(self, stage: str, message: str) -> IndexOperationSnapshot:
        return self._registry.mark_running(self._operation_id, stage=stage, message=message)

    def set_stage(self, stage: str, message: str) -> IndexOperationSnapshot:
        return self._registry.update(self._operation_id, current_stage=stage, message=message)

    def update(self, **changes: Any) -> IndexOperationSnapshot:
        with self._lock:
            current = self._registry.get(self._operation_id)
            if current is None:
                raise KeyError(self._operation_id)
            merged = {}
            for key, value in changes.items():
                if value is None:
                    continue
                current_value = getattr(current, key)
                if isinstance(current_value, int) and isinstance(value, int) and key.endswith(("_completed", "_failed")):
                    merged[key] = max(current_value, value)
                else:
                    merged[key] = value
            return self._registry.update(self._operation_id, **merged)

    def increment(self, **deltas: int) -> IndexOperationSnapshot:
        with self._lock:
            current = self._registry.get(self._operation_id)
            if current is None:
                raise KeyError(self._operation_id)
            changes = {}
            for key, value in deltas.items():
                changes[key] = max(0, int(getattr(current, key)) + int(value))
            return self._registry.update(self._operation_id, **changes)

    def complete(self, final_stats: dict[str, Any], message: str = "Completed") -> IndexOperationSnapshot:
        return self._registry.complete(self._operation_id, final_stats=final_stats, message=message)

    def fail(self, error: str, stage: str = "failed", message: str = "Failed") -> IndexOperationSnapshot:
        return self._registry.fail(self._operation_id, error=error, stage=stage, message=message)


GLOBAL_OPERATION_REGISTRY = OperationRegistry()


def snapshot_to_dict(snapshot: IndexOperationSnapshot) -> dict[str, Any]:
    return asdict(snapshot)
