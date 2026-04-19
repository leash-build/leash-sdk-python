"""Tests for framework isolation.

Verifies the Leash SDK has zero web-framework dependencies at three levels:
1. Static: no .py file in leash/ imports a web framework
2. Runtime: importing leash does not pull any framework into sys.modules
3. Dependency: pyproject.toml declares no framework in dependencies
"""

import ast
import os
import subprocess
import sys
import textwrap

import pytest

# Frameworks that must never appear as SDK dependencies
FORBIDDEN_FRAMEWORKS = [
    "flask",
    "django",
    "fastapi",
    "starlette",
    "tornado",
    "bottle",
    "pyramid",
    "sanic",
    "aiohttp",
]

LEASH_PKG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "leash",
)

PYPROJECT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "pyproject.toml",
)


# ── helpers ──────────────────────────────────────────────────────────


def _collect_py_files(directory: str):
    """Yield all .py file paths under *directory*."""
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            if fname.endswith(".py"):
                yield os.path.join(root, fname)


def _imported_modules(filepath: str):
    """Return a set of top-level module names imported in *filepath*."""
    with open(filepath) as fh:
        try:
            tree = ast.parse(fh.read(), filename=filepath)
        except SyntaxError:
            return set()

    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module.split(".")[0])
    return modules


# ── static checks ────────────────────────────────────────────────────


class TestStaticImports:
    """Scan every .py file inside leash/ and reject framework imports."""

    def test_no_framework_imports_in_any_source_file(self):
        violations = []
        for pyfile in _collect_py_files(LEASH_PKG_DIR):
            imported = _imported_modules(pyfile)
            for fw in FORBIDDEN_FRAMEWORKS:
                if fw in imported:
                    rel = os.path.relpath(pyfile, LEASH_PKG_DIR)
                    violations.append(f"{rel} imports {fw}")

        assert violations == [], (
            "Framework imports found in SDK source files:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_only_requests_and_stdlib(self):
        """Every import should be either stdlib, 'requests', or intra-package."""
        # Build a rough stdlib list from the running interpreter
        if sys.version_info >= (3, 10):
            stdlib_names = sys.stdlib_module_names
        else:
            import pkgutil
            stdlib_names = {m.name for m in pkgutil.iter_modules()}
            # Add common built-ins that iter_modules may skip
            stdlib_names |= {
                "os", "sys", "json", "typing", "abc", "re",
                "collections", "functools", "urllib", "pathlib",
                "dataclasses", "enum", "io", "copy", "importlib",
                "unittest", "builtins", "__future__",
            }

        allowed_third_party = {"requests", "jwt"}
        for pyfile in _collect_py_files(LEASH_PKG_DIR):
            imported = _imported_modules(pyfile)
            for mod in imported:
                if mod == "leash":
                    continue  # intra-package
                if mod in stdlib_names:
                    continue
                if mod in allowed_third_party:
                    continue
                rel = os.path.relpath(pyfile, LEASH_PKG_DIR)
                pytest.fail(
                    f"{rel} imports unexpected third-party module '{mod}'"
                )


# ── runtime isolation ────────────────────────────────────────────────


class TestRuntimeIsolation:
    """Import leash in a fresh subprocess and inspect sys.modules."""

    def test_import_succeeds_in_subprocess(self):
        result = subprocess.run(
            [sys.executable, "-c", "import leash; print('ok')"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(LEASH_PKG_DIR),
        )
        assert result.returncode == 0, (
            f"import leash failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "ok" in result.stdout

    def test_no_framework_in_sys_modules_after_import(self):
        frameworks_csv = ",".join(f'"{fw}"' for fw in FORBIDDEN_FRAMEWORKS)
        script = textwrap.dedent(f"""\
            import leash
            import sys
            frameworks = [{frameworks_csv}]
            leaked = [fw for fw in frameworks if fw in sys.modules]
            if leaked:
                print("LEAKED:" + ",".join(leaked))
            else:
                print("CLEAN")
        """)

        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(LEASH_PKG_DIR),
        )
        assert result.returncode == 0, (
            f"subprocess failed:\nstderr: {result.stderr}"
        )
        assert "CLEAN" in result.stdout, (
            f"Framework modules leaked into sys.modules: {result.stdout.strip()}"
        )


# ── dependency isolation ─────────────────────────────────────────────


class TestDependencyIsolation:
    """Parse pyproject.toml and reject any framework in [project.dependencies]."""

    def test_no_framework_in_pyproject_dependencies(self):
        with open(PYPROJECT_PATH) as fh:
            content = fh.read()

        # Lightweight TOML parsing: grab the dependencies list
        # Works for the simple array format used by this project
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib  # backport
            except ImportError:
                tomllib = None

        if tomllib:
            deps = tomllib.loads(content).get("project", {}).get("dependencies", [])
        else:
            # Fallback: simple regex extraction
            import re
            match = re.search(
                r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL
            )
            assert match, "Could not locate dependencies in pyproject.toml"
            deps = re.findall(r'"([^"]+)"', match.group(1))

        dep_names = [d.split(">")[0].split("<")[0].split("=")[0].split("[")[0].strip().lower() for d in deps]

        for fw in FORBIDDEN_FRAMEWORKS:
            assert fw not in dep_names, (
                f"Web framework '{fw}' found in pyproject.toml dependencies"
            )

    def test_only_expected_dependencies(self):
        """Dependencies should only contain 'requests' and 'PyJWT'."""
        with open(PYPROJECT_PATH) as fh:
            content = fh.read()

        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                tomllib = None

        if tomllib:
            deps = tomllib.loads(content).get("project", {}).get("dependencies", [])
        else:
            import re
            match = re.search(
                r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL
            )
            assert match, "Could not locate dependencies in pyproject.toml"
            deps = re.findall(r'"([^"]+)"', match.group(1))

        dep_names = [d.split(">")[0].split("<")[0].split("=")[0].split("[")[0].strip().lower() for d in deps]
        allowed = {"requests", "pyjwt"}
        unexpected = set(dep_names) - allowed
        assert not unexpected, (
            f"Unexpected dependencies in pyproject.toml: {unexpected}"
        )
