from __future__ import annotations

import ast
from pathlib import Path


PACKAGE = Path(__file__).parents[1] / "src" / "mmis_connector"
DEVELOPMENT_TOOLS = Path(__file__).parents[1] / "tools" / "mmis_development"
CORE_MODULE = "auto_link.orchestrator"


def _module_path(module_name: str) -> Path:
    return PACKAGE / (module_name.replace(".", "/") + ".py")


def _resolve_relative_import(module_name: str, node: ast.ImportFrom) -> str:
    package_parts = module_name.split(".")[:-1]
    parent_levels = node.level - 1
    if parent_levels > len(package_parts):
        return ""
    base_parts = package_parts[: len(package_parts) - parent_levels]
    if node.module:
        base_parts.extend(node.module.split("."))
    return ".".join(base_parts)


def _local_imports(module_name: str) -> set[str]:
    tree = ast.parse(_module_path(module_name).read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level == 0:
            continue
        dependency = _resolve_relative_import(module_name, node)
        if dependency and _module_path(dependency).is_file():
            imports.add(dependency)
    return imports


def _reachable_local_modules(root: str) -> set[str]:
    seen: set[str] = set()
    pending = [root]
    while pending:
        module_name = pending.pop()
        for dependency in _local_imports(module_name):
            if dependency not in seen:
                seen.add(dependency)
                pending.append(dependency)
    return seen


def test_auto_link_has_explicit_reusable_component_dependencies() -> None:
    assert _local_imports(CORE_MODULE) == {
        "auth",
        "auto_link.store",
        "daily_inspection.linker",
        "daily_inspection.query",
        "fault_notices.query",
    }


def test_auto_link_dependency_graph_does_not_reach_cli_or_subprocess() -> None:
    reachable = _reachable_local_modules(CORE_MODULE)

    assert reachable == {
        "auth",
        "auto_link.store",
        "daily_inspection.linker",
        "daily_inspection.query",
        "daily_inspection.reader",
        "events",
        "fault_notices.query",
        "parser",
    }
    assert "cli" not in reachable

    for module_name in {CORE_MODULE, *reachable}:
        tree = ast.parse(_module_path(module_name).read_text(encoding="utf-8"))
        imported_roots = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported_roots.update(
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.level == 0
            and node.module
        )
        assert "subprocess" not in imported_roots


def test_every_production_module_is_classified() -> None:
    expected_paths = {
        "__init__.py",
        "__main__.py",
        "auth.py",
        "auto_link/__init__.py",
        "auto_link/orchestrator.py",
        "auto_link/store.py",
        "cli.py",
        "daily_inspection/__init__.py",
        "daily_inspection/linker.py",
        "daily_inspection/query.py",
        "daily_inspection/reader.py",
        "events.py",
        "fault_notices/__init__.py",
        "fault_notices/atp_reader.py",
        "fault_notices/full_detail.py",
        "fault_notices/linked_work_orders.py",
        "fault_notices/repair_work_orders.py",
        "fault_notices/query.py",
        "fault_notices/reader.py",
        "parser.py",
        "temporary_repair/__init__.py",
        "temporary_repair/reader.py",
    }

    assert {
        path.relative_to(PACKAGE).as_posix()
        for path in PACKAGE.rglob("*.py")
    } == expected_paths


def _absolute_import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.level == 0
        and node.module
    )
    return roots


def test_production_modules_do_not_import_development_or_reference_code() -> None:
    forbidden_roots = {"tools", "development", "reference", "examples"}

    for module_path in PACKAGE.rglob("*.py"):
        assert _absolute_import_roots(module_path).isdisjoint(forbidden_roots), (
            f"production module imports non-production code: {module_path}"
        )


def test_development_tools_import_formal_components_not_production_cli() -> None:
    tool_paths = [
        path
        for path in DEVELOPMENT_TOOLS.glob("*.py")
        if path.name not in {"__init__.py", "_support.py"}
    ]

    assert len(tool_paths) == 11
    for tool_path in tool_paths:
        tree = ast.parse(tool_path.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert any(
            module.startswith("mmis_connector.")
            for module in imported_modules
        )
        assert "mmis_connector.cli" not in imported_modules
