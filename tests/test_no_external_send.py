"""
Structural verification of the Hard Rule "Publisher may not submit externally."

Rather than trusting that no one *ever* adds a send call, this test scans every source file in
src/dispatch_publisher for tokens that indicate outbound network/email capability. If this test
starts failing, someone added a code path that can leave this repo's boundary — that requires a
Conflict Notice and Mike's decision, not a quiet fix.
"""
import ast
import pathlib

FORBIDDEN_IMPORT_MODULES = {
    "smtplib", "requests", "urllib.request", "urllib3", "http.client", "httpx",
    "socket", "ftplib", "telnetlib", "aiohttp", "boto3",
}

SRC_ROOT = pathlib.Path(__file__).resolve().parent.parent / "src" / "dispatch_publisher"


def _all_source_files():
    return sorted(SRC_ROOT.rglob("*.py"))


def test_source_files_exist_to_scan():
    files = _all_source_files()
    assert len(files) >= 5, "expected the dispatch_publisher package to contain multiple modules"


def test_no_forbidden_network_imports_anywhere_in_publisher():
    violations = []
    for path in _all_source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_IMPORT_MODULES or alias.name.split(".")[0] in FORBIDDEN_IMPORT_MODULES:
                        violations.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module in FORBIDDEN_IMPORT_MODULES or module.split(".")[0] in FORBIDDEN_IMPORT_MODULES:
                    violations.append(f"{path.name}: from {module} import ...")

    assert violations == [], f"forbidden network-capable imports found: {violations}"


def test_no_send_or_submit_named_functions_exist():
    """No function in this repo may be named to suggest external transmission."""
    forbidden_name_fragments = ("send_email", "send_to_customer", "send_to_broker", "submit_to_government", "smtp")
    violations = []
    for path in _all_source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lowered = node.name.lower()
                if any(fragment in lowered for fragment in forbidden_name_fragments):
                    violations.append(f"{path.name}: def {node.name}")

    assert violations == [], f"forbidden send/submit-named functions found: {violations}"
