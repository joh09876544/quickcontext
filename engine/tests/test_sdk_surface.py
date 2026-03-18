import tempfile
import unittest
from pathlib import Path
from unittest import mock

from engine.sdk import QuickContext
from engine.src.config import EngineConfig, QdrantConfig
from engine.src.parsing import TextSearchMatch
from engine.src.sdk_models import ProjectCollectionInfo


class SDKSurfaceTests(unittest.TestCase):
    def test_qdrant_available_probes_connection_when_requested(self) -> None:
        qc = QuickContext(EngineConfig(qdrant=QdrantConfig()))

        with mock.patch.object(qc, "connect", return_value=qc) as connect:
            self.assertTrue(qc.qdrant_available(verify=True))

        connect.assert_called_once_with(verify=True)

    def test_status_reports_qdrant_health_without_prior_cached_client(self) -> None:
        qc = QuickContext(EngineConfig(qdrant=QdrantConfig()))
        fake_pipe = mock.Mock(_pipe_name="test-pipe")
        qc._parser_service = mock.Mock(connected=True, _client=fake_pipe)

        with mock.patch.object(qc, "connect", return_value=qc) as connect:
            status = qc.status()

        self.assertTrue(status["qdrant"]["configured"])
        self.assertTrue(status["qdrant"]["alive"])
        self.assertEqual(status["parser"]["pipe_name"], "test-pipe")
        connect.assert_called_once_with(verify=True)

    def test_project_info_returns_stable_discovery_payload(self) -> None:
        qc = QuickContext(EngineConfig(qdrant=QdrantConfig()))
        qc._parser_service = mock.Mock(connected=False)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text("{}", encoding="utf-8")
            (root / "src").mkdir()

            with mock.patch.object(qc, "qdrant_available", return_value=False):
                info = qc.project_info(root, include_folders=True)

        self.assertEqual(info.project_name, root.name)
        self.assertFalse(info.qdrant_available)
        self.assertFalse(info.collection.indexed)
        self.assertEqual(info.folders[0].relative_path, ".")
        self.assertIn("src", {item.relative_path for item in info.folders})

    def test_list_projects_returns_typed_collection_info(self) -> None:
        qc = QuickContext(EngineConfig(qdrant=QdrantConfig()))
        qc._conn = mock.Mock()
        qc._conn.client = object()

        fake_projects = [
            {
                "name": "demo",
                "real_collection": "demo_v2",
                "points_count": 42,
                "indexed_vectors_count": 84,
                "segments_count": 3,
                "status": "green",
                "vectors": {"code": {"size": 768, "distance": "cosine"}},
            }
        ]

        with mock.patch.object(qc, "qdrant_available", return_value=True):
            with mock.patch("engine.src.collection.CollectionManager.list_all_projects", return_value=fake_projects):
                projects = qc.list_projects()

        self.assertEqual(len(projects), 1)
        self.assertIsInstance(projects[0], ProjectCollectionInfo)
        self.assertEqual(projects[0].project_name, "demo")
        self.assertTrue(projects[0].indexed)
        self.assertEqual(projects[0].vectors["code"]["size"], 768)

    def test_text_search_match_normalizes_windows_verbatim_prefix(self) -> None:
        match = TextSearchMatch.from_dict(
            {
                "file_path": "\\\\?\\C:\\repo\\src\\main.py",
                "score": 1.0,
                "matched_terms": ["main"],
                "snippet": "def main(): pass",
                "snippet_line_start": 1,
                "snippet_line_end": 1,
                "language": "python",
            }
        )
        self.assertEqual(match.file_path, "C:\\repo\\src\\main.py")
