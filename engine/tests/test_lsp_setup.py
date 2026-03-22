import tempfile
import unittest
from pathlib import Path
from unittest import mock

from engine.sdk import QuickContext
from engine.src.config import EngineConfig
from engine.src.lsp_setup import build_lsp_setup_plan
from engine.src.pipe import PipeClient


class LspSetupTests(unittest.TestCase):
    def test_typescript_project_setup_plan_includes_typescript_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text("{}", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "main.ts").write_text("export const x = 1;\n", encoding="utf-8")

            plan = build_lsp_setup_plan(root)

        by_name = {server.name: server for server in plan.servers}
        self.assertIn("typescript-language-server", by_name)
        self.assertTrue(by_name["typescript-language-server"].auto_install_supported)
        self.assertTrue(any("npm install -g typescript-language-server typescript" in step.command for step in by_name["typescript-language-server"].install_steps))

    def test_java_project_setup_plan_marks_manual_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pom.xml").write_text("<project />", encoding="utf-8")
            (root / "Main.java").write_text("class Main {}", encoding="utf-8")

            plan = build_lsp_setup_plan(root)

        by_name = {server.name: server for server in plan.servers}
        self.assertIn("jdtls", by_name)
        self.assertFalse(by_name["jdtls"].auto_install_supported)
        self.assertTrue(by_name["jdtls"].notes)

    def test_quickcontext_exposes_lsp_setup_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements.txt").write_text("requests\n", encoding="utf-8")
            (root / "app.py").write_text("print('hello')\n", encoding="utf-8")
            with QuickContext(EngineConfig()) as qc:
                plan = qc.lsp_setup_plan(root)

        self.assertEqual(plan.target_path, str(root.resolve()))
        self.assertTrue(any(server.language_id == "python" for server in plan.servers))

    def test_lsp_setup_ignores__ignore_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements.txt").write_text("requests\n", encoding="utf-8")
            (root / "app.py").write_text("print('hello')\n", encoding="utf-8")
            ignored = root / "_ignore"
            ignored.mkdir()
            (ignored / "package.json").write_text("{}", encoding="utf-8")
            (ignored / "main.ts").write_text("export const x = 1;\n", encoding="utf-8")

            plan = build_lsp_setup_plan(root)

        languages = {server.language_id for server in plan.servers}
        self.assertIn("python", languages)
        self.assertNotIn("typescript", languages)

    def test_pipe_client_has_lsp_definition_method(self) -> None:
        client = PipeClient()
        with mock.patch.object(client, "request", return_value={"status": "ok", "data": {"items": []}}) as request:
            result = client.lsp_definition("C:/repo/main.py", 1, 2)

        request.assert_called_once_with({
            "method": "lsp_definition",
            "file": "C:/repo/main.py",
            "line": 1,
            "character": 2,
        })
        self.assertEqual(result, {"items": []})
