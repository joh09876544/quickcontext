from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ProjectFolderInfo:
    relative_path: str
    absolute_path: str


@dataclass(frozen=True, slots=True)
class ProjectCollectionInfo:
    project_name: str
    indexed: bool
    real_collection: str | None = None
    points_count: int | None = None
    indexed_vectors_count: int | None = None
    segments_count: int | None = None
    status: str | None = None
    vectors: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProjectInfo:
    path: str
    project_name: str
    indexed: bool
    qdrant_enabled: bool
    qdrant_available: bool
    parser_connected: bool
    cache_entries: int
    cache_disk_bytes: int
    cache_path: str
    collection: ProjectCollectionInfo
    folders: list[ProjectFolderInfo] = field(default_factory=list)
