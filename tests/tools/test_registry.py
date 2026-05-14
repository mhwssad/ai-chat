import sys
import unittest
import json
from pathlib import Path

from langchain_core.tools import tool

from src.ai_chat.tools import ToolType, tool_registry


def _reset_tool_registry() -> None:
    tool_registry._tools.clear()
    tool_registry._searched_modules.clear()
    tool_registry._module_candidates = None
    tool_registry._current_loading_module = None
    tool_registry._module_tool_names.clear()

    for module_name in [
        "src.ai_chat.tools.common",
        "src.ai_chat.tools.paths",
        "src.ai_chat.tools.search",
        "src.ai_chat.tools.command",
    ]:
        sys.modules.pop(module_name, None)

    tool_registry.load_system_tools()


class ToolRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_tool_registry()

    def test_only_system_tools_are_loaded_by_default(self) -> None:
        loaded = {tool_obj.name for tool_obj in tool_registry.get_all()}

        self.assertIn("read_file", loaded)
        self.assertIn("write_file", loaded)
        self.assertIn("search_text", loaded)
        self.assertIn("list_dir", loaded)
        self.assertIn("path_info", loaded)
        self.assertIn("glob_files", loaded)
        self.assertIn("run_command", loaded)
        self.assertEqual(tool_registry.get_record("read_file").tool_type, ToolType.SYSTEM)

    def test_get_all_does_not_trigger_lazy_loading(self) -> None:
        before = {tool_obj.name for tool_obj in tool_registry.get_all()}

        after = {tool_obj.name for tool_obj in tool_registry.get_all()}

        self.assertEqual(before, after)
        self.assertIn("search_text", after)

    def test_missing_tool_search_does_not_pollute_loaded_set(self) -> None:
        before = set(tool_registry._tools)

        with self.assertRaises(KeyError):
            tool_registry.get("tool_that_does_not_exist")

        self.assertEqual(before, set(tool_registry._tools))

    def test_make_dir_creates_directory_inside_project(self) -> None:
        created_dir = Path("tests/.tmp_tool_dir")
        if created_dir.exists():
            for child in created_dir.iterdir():
                if child.is_file():
                    child.unlink()
            created_dir.rmdir()

        result = tool_registry.get("make_dir").invoke({"path": str(created_dir)})
        payload = json.loads(result)

        self.assertTrue(payload["ok"])
        self.assertTrue(created_dir.exists())
        created_dir.rmdir()

    def test_make_dir_rejects_path_outside_project(self) -> None:
        result = tool_registry.get("make_dir").invoke({"path": "../outside_dir"})

        self.assertIn("[ERROR]", result)

    def test_path_info_returns_json_for_existing_path(self) -> None:
        result = tool_registry.get("path_info").invoke({"path": "README.md"})
        payload = json.loads(result)

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["exists"])
        self.assertEqual(payload["type"], "file")

    def test_glob_files_and_search_text_respect_project_scope(self) -> None:
        glob_result = tool_registry.get("glob_files").invoke({
            "pattern": "*.md",
            "root_dir": "docs",
        })
        glob_payload = json.loads(glob_result)

        self.assertTrue(glob_payload["ok"])
        self.assertTrue(any(path.endswith("README.md") for path in glob_payload["matches"]))

        denied = tool_registry.get("search_text").invoke({
            "pattern": "README",
            "root_dir": "..",
        })
        self.assertIn("[ERROR]", denied)

    def test_run_command_executes_whitelisted_command(self) -> None:
        result = tool_registry.get("run_command").invoke({
            "command": "Get-Location",
            "cwd": ".",
            "timeout": 5,
        })
        payload = json.loads(result)

        self.assertIn("ok", payload)
        self.assertIn("stdout", payload)
        self.assertIn("stderr", payload)
        self.assertIn("exit_code", payload)
        self.assertEqual(payload["command"], "Get-Location")

    def test_run_command_rejects_dangerous_syntax(self) -> None:
        result = tool_registry.get("run_command").invoke({
            "command": "Get-Location | Select-Object -First 1",
        })
        payload = json.loads(result)

        self.assertFalse(payload["ok"])
        self.assertIn("危险语法", payload["stderr"])

    def test_run_command_rejects_outside_cwd(self) -> None:
        result = tool_registry.get("run_command").invoke({
            "command": "Get-Location",
            "cwd": "..",
        })
        payload = json.loads(result)

        self.assertFalse(payload["ok"])
        self.assertIn("cwd 超出项目根目录", payload["stderr"])

    def test_mcp_tools_are_marked_with_mcp_type(self) -> None:
        @tool
        def fake_remote_tool() -> str:
            """fake mcp tool"""
            return "ok"

        tool_registry.register(
            fake_remote_tool,
            tool_type=ToolType.MCP,
            source_module="mcp",
        )

        mcp_tools = {tool_obj.name for tool_obj in tool_registry.get_all(ToolType.MCP)}

        self.assertIn("fake_remote_tool", mcp_tools)
        self.assertEqual(tool_registry.get_record("fake_remote_tool").tool_type, ToolType.MCP)


if __name__ == "__main__":
    unittest.main()
