# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Pytest fixtures and the --report plugin for x16-emulator-MCP.

The emulatorBinary and romPath fixtures locate the external runtime inputs
via x16dbg's discovery helpers, skipping tests cleanly when they are absent
so the suite runs on a bare checkout.

The --report flag generates tests/TEST_REPORT.md after a run: a structured
listing of every test grouped by module and class, pass/fail/skip status,
duration, and (when pytest-cov is active) a per-file code coverage summary.

    pytest tests/ --report

It is enabled by default through addopts in pyproject.toml.
"""

from __future__ import annotations

import ast
import datetime
import inspect
import os
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from x16dbg.config import discoverEmulator, discoverRom

# -----------------------------------------------------------------------
# Runtime-input discovery fixtures
# -----------------------------------------------------------------------


@pytest.fixture
def emulatorBinary() -> Path:
    """Locate the x16emu binary for a test, skipping cleanly when absent.

    Returns:
        Path: the resolved emulator binary path.
    """

    found = discoverEmulator()

    if found is None:
        pytest.skip("x16emu binary not found; set $X16EMU_PATH or drop it in resources/")

    return found


@pytest.fixture
def romPath() -> Path:
    """Locate rom.bin for a test, skipping cleanly when absent.

    Returns:
        Path: the resolved ROM path.
    """

    found = discoverRom()

    if found is None:
        pytest.skip("rom.bin not found; set $X16ROM_PATH or drop it in resources/")

    return found


# -----------------------------------------------------------------------
# --report plugin registration
# -----------------------------------------------------------------------


def pytest_addoption(parser: Any) -> None:
    """Register the --report flag. The hook name is fixed by pytest.

    Args:
        parser: the pytest command-line parser.
    """

    parser.addoption(
        "--report",
        action="store_true",
        default=False,
        help="Generate tests/TEST_REPORT.md after the test run.",
    )


def pytest_configure(config: Any) -> None:
    """Attach the report collector when --report is set. Hook name fixed by pytest.

    Args:
        config: the pytest config for this session.
    """

    if config.getoption("--report", default=False):
        plugin = ReportCollector(config)
        config._report_collector = plugin
        config.pluginmanager.register(plugin, "report_collector")


# -----------------------------------------------------------------------
# Report collector
# -----------------------------------------------------------------------


class ReportCollector:
    """Collects test results and writes the markdown report."""

    def __init__(self, config: Any) -> None:
        """Hold the pytest config and the accumulators the hooks fill in.

        Args:
            config: the pytest config for this session.
        """

        self._config = config
        self._results: List[Dict[str, Any]] = []
        self._descriptions: Dict[str, str] = {}

    def pytest_collection_modifyitems(
        self,
        session: Any,
        config: Any,
        items: List[Any],
    ) -> None:
        """Capture per-test descriptions from docstrings during collection.

        Args:
            session: the pytest session (unused).
            config: the pytest config (unused).
            items: the collected test items.
        """

        del session
        del config

        # Record a human-readable description for each collected test.
        for item in items:
            self._descriptions[item.nodeid] = _describeTestItem(item)

    def pytest_runtest_logreport(self, report: Any) -> None:
        """Capture the final outcome of each test.

        Args:
            report: a pytest test report for one phase of one test.
        """

        # Record only the final outcome: "call" for pass/fail, "setup" for
        # setup-time skips, anything failing in setup/teardown as an error.
        if report.when == "call":
            outcome = report.outcome
        elif report.when == "setup" and report.outcome == "skipped":
            outcome = "skipped"
        elif report.failed:
            outcome = "error"
        else:
            return

        self._results.append(
            {
                "nodeid": report.nodeid,
                "outcome": outcome,
                "duration": report.duration,
                "longrepr": str(report.longrepr) if report.failed else "",
                "description": self._descriptions.get(report.nodeid, ""),
            }
        )

    def pytest_sessionfinish(self, session: Any, exitstatus: int) -> None:
        """Write the report after all tests complete.

        Args:
            session: the pytest session (unused).
            exitstatus: the session exit status (unused).
        """

        del session
        del exitstatus

        # Build the markdown from the collected results plus any coverage data.
        root = str(self._config.rootpath)
        report_path = os.path.join(root, "tests", "TEST_REPORT.md")
        coverage = _extractCoverage(self._config)
        content = _buildReport(self._results, coverage)

        with open(report_path, "w") as f:
            f.write(content)

        # Mirror the report into the Actions job summary when present.
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")

        if summary_path:
            with open(summary_path, "a") as f:
                f.write(content)


# -----------------------------------------------------------------------
# Coverage extraction
# -----------------------------------------------------------------------


def _extractCoverage(config: Any) -> Optional[List[Tuple[str, int, int, int]]]:
    """Pull per-file coverage data from pytest-cov.

    Args:
        config: the pytest config, which may hold the active cov plugin.

    Returns:
        Optional[List[Tuple[str, int, int, int]]]: one (filename, stmts, miss,
        cover_pct) tuple per measured file, or None when coverage is inactive.
    """

    # Walk down the pytest-cov plugin to the underlying coverage object,
    # bailing out cleanly at each step if cov is not active.
    cov_plugin = config.pluginmanager.getplugin("_cov")

    if cov_plugin is None:
        return None

    cov = getattr(cov_plugin, "cov_controller", None)

    if cov is None:
        return None

    cov_obj = getattr(cov, "cov", None)

    if cov_obj is None:
        return None

    # Analyse each measured file and shorten its path to the package-relative
    # form (everything after the src/ segment).
    results = []
    marker = os.sep + "src" + os.sep

    try:
        data = cov_obj.get_data()

        for filename in sorted(data.measured_files()):
            analysis = cov_obj._analyze(filename)
            stmts = len(analysis.statements)
            miss = len(analysis.missing)
            cover = int(analysis.numbers.pc_covered) if stmts > 0 else 100

            short = filename
            idx = filename.rfind(marker)

            if idx >= 0:
                short = filename[idx + len(marker) :]

            results.append((short, stmts, miss, cover))

    except Exception:
        return None

    coverage = results if results else None
    return coverage


# -----------------------------------------------------------------------
# Rendering helpers
# -----------------------------------------------------------------------


def _statusBadge(outcome: str) -> str:
    """Return a shields.io image badge for the test outcome.

    Args:
        outcome: the test outcome, such as "passed" or "skipped".

    Returns:
        str: a markdown image badge for the outcome.
    """

    labels = {
        "passed": ("PASS", "2ea043"),
        "failed": ("FAIL", "cf222e"),
        "skipped": ("SKIP", "9a6700"),
        "error": ("ERROR", "a40e26"),
        "xfailed": ("XFAIL", "8250df"),
        "xpassed": ("XPASS", "0a7ea4"),
    }

    label, color = labels.get(outcome, (outcome.upper(), "57606a"))
    badge = f"![{label}](https://img.shields.io/badge/{label}-{color})"
    return badge


def _coverageBar(pct: int) -> str:
    """Build an HTML progress bar for code coverage, color-coded by threshold.

    Args:
        pct: the coverage percentage to render.

    Returns:
        str: an inline HTML bar followed by the clamped percentage.
    """

    clamped = max(0, min(100, pct))

    # Green at or above 80%, amber from 60%, red below.
    if clamped >= 80:
        color = "#2ea043"
    elif clamped >= 60:
        color = "#d29922"
    else:
        color = "#cf222e"

    # Always show at least 4% width so the bar is visible at very low coverage.
    visible_pct = max(4, clamped) if clamped > 0 else 0

    bar = (
        '<span style="display:inline-block;width:98px;background:#30363d;'
        'border-radius:4px;overflow:hidden;vertical-align:middle;">'
        f'<span style="display:inline-block;width:{visible_pct}%;'
        f'background:{color};">&nbsp;</span></span> {clamped}%'
    )
    return bar


def _coverageFileLink(filename: str) -> str:
    """Link a coverage row filename to the source file under src/.

    Args:
        filename: the package-relative filename from the coverage data.

    Returns:
        str: a markdown link when the file is one of ours, else the name.
    """

    if filename.startswith("x16dbg/") or filename.startswith("x16mcp/"):
        link = f"[{filename}](../src/{filename})"
        return link

    return filename


def _moduleDocstring(module: str) -> str:
    """Return the module-level docstring from a test file.

    Args:
        module: the test module path relative to the repo root.

    Returns:
        str: the module docstring, or an empty string when there is none.
    """

    tests_dir = os.path.dirname(__file__)
    repo_root = os.path.dirname(tests_dir)
    filepath = os.path.join(repo_root, module)

    if not os.path.isfile(filepath):
        return ""

    # Parse the file and read its module docstring, tolerating read errors.
    try:
        with open(filepath, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())

        doc = ast.get_docstring(tree)
        result = doc or ""
        return result

    except (OSError, SyntaxError):
        return ""


def _moduleLink(module: str) -> str:
    """Link a test module heading to its source file.

    Args:
        module: the test module path relative to the repo root.

    Returns:
        str: a markdown link when under tests/, else the module path.
    """

    if module.startswith("tests/"):
        relative = module[len("tests/") :]
        link = f"[{module}](./{relative})"
        return link

    return module


def _normalizeWhitespace(text: str) -> str:
    """Collapse whitespace and trim to a single readable line.

    Args:
        text: the text to normalise.

    Returns:
        str: the text with runs of whitespace collapsed to single spaces.
    """

    collapsed = re.sub(r"\s+", " ", text).strip()
    return collapsed


def _humanizeTestName(test_name: str) -> str:
    """Convert internal test names to readable sentence case.

    Args:
        test_name: the test function or method name, with any parametrisation.

    Returns:
        str: a sentence-cased description derived from the name.
    """

    # Split a parametrised suffix (the [...] part) off the base name.
    if "[" in test_name and test_name.endswith("]"):
        base, param = test_name.split("[", 1)
        suffix = f" [{param[:-1]}]"
    else:
        base = test_name
        suffix = ""

    # Break camelCase and snake_case into words and drop a leading "test".
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", base)
    spaced = spaced.replace("_", " ")
    spaced = re.sub(r"(?i)^test\s+", "", spaced)
    pretty = _normalizeWhitespace(spaced)

    if not pretty:
        return test_name

    humanized = pretty[0].upper() + pretty[1:] + suffix
    return humanized


def _describeTestItem(item: Any) -> str:
    """Build a test description using docstring first, then name fallback.

    Args:
        item: the collected pytest item.

    Returns:
        str: the best available description for the test.
    """

    parts: List[str] = []

    # Prefer the class docstring's first sentence, when the test is a method.
    cls = getattr(item, "cls", None)

    if cls is not None:
        class_doc = inspect.getdoc(cls)

        if class_doc:
            first = _normalizeWhitespace(class_doc).split(". ")[0]
            parts.append(first.rstrip("."))

    # Then the test's own docstring.
    obj = getattr(item, "obj", None)

    if obj is not None:
        doc = inspect.getdoc(obj)

        if doc:
            parts.append(_normalizeWhitespace(doc))

    # Fall back to the module docstring when nothing more specific exists.
    module_obj = getattr(item, "module", None)

    if module_obj is not None and not parts:
        module_doc = inspect.getdoc(module_obj)

        if module_doc:
            first = _normalizeWhitespace(module_doc).split(". ")[0]
            parts.append(first.rstrip("."))

    if parts:
        description = " - ".join(parts)
        return description

    fallback = _humanizeTestName(item.name)
    return fallback


def _escapeTableCell(text: str) -> str:
    """Escape markdown table delimiters in user-controlled strings.

    Args:
        text: the cell text to escape.

    Returns:
        str: the text with pipe characters escaped.
    """

    escaped = text.replace("|", "\\|")
    return escaped


def _badgeUrl(label: str, message: str, color: str) -> str:
    """Build a shields.io badge URL for summary counters.

    Args:
        label: the badge label.
        message: the badge message.
        color: the badge color, as a hex string.

    Returns:
        str: the assembled shields.io URL.
    """

    safe_label = label.replace(" ", "%20")
    safe_message = message.replace(" ", "%20")
    url = f"https://img.shields.io/badge/{safe_label}-{safe_message}-{color}"
    return url


# -----------------------------------------------------------------------
# Markdown report builder
# -----------------------------------------------------------------------


def _buildReport(
    results: List[Dict[str, Any]],
    coverage: Optional[List[Tuple[str, int, int, int]]],
) -> str:
    """Build the full TEST_REPORT.md content.

    Args:
        results: the collected per-test outcome records.
        coverage: per-file coverage tuples, or None when coverage is inactive.

    Returns:
        str: the complete markdown document.
    """

    lines: List[str] = []
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append("# Test Report")
    lines.append("")
    lines.append(f"Generated: {timestamp}")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append("This report summarizes the latest pytest run for this repository.")
    lines.append("It includes pass and fail outcomes, code coverage highlights, and")
    lines.append("per-test descriptions sourced from test docstrings when available.")
    lines.append("")

    # -- Summary -------------------------------------------------------

    total = len(results)
    passed = sum(1 for r in results if r["outcome"] == "passed")
    failed = sum(1 for r in results if r["outcome"] == "failed")
    skipped = sum(1 for r in results if r["outcome"] == "skipped")
    errors = sum(1 for r in results if r["outcome"] == "error")
    duration = sum(r["duration"] for r in results)
    pass_rate = int((passed / total) * 100) if total else 100

    lines.append(
        " ".join(
            [
                f"![Total tests]({_badgeUrl('tests', str(total), '0366d6')})",
                f"![Passed]({_badgeUrl('passed', str(passed), '2ea043')})",
                f"![Failed]({_badgeUrl('failed', str(failed), 'cf222e')})",
                f"![Skipped]({_badgeUrl('skipped', str(skipped), '9a6700')})",
                f"![Pass rate]({_badgeUrl('pass%20rate', f'{pass_rate}%25', '2ea043')})",
            ]
        )
    )
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("| --- | ---: |")
    lines.append(f"| Total tests | {total} |")
    lines.append(f"| Passed | {passed} |")
    lines.append(f"| Failed | {failed} |")
    lines.append(f"| Skipped | {skipped} |")

    if errors:
        lines.append(f"| Errors | {errors} |")

    lines.append(f"| Pass rate | {pass_rate}% |")
    lines.append(f"| Duration | {duration:.2f}s |")
    lines.append("")

    lines.append("```mermaid")
    lines.append("pie title Test outcomes")
    lines.append(f'    "Passed" : {passed}')
    lines.append(f'    "Failed" : {failed}')
    lines.append(f'    "Skipped" : {skipped}')

    if errors:
        lines.append(f'    "Errors" : {errors}')

    lines.append("```")
    lines.append("")

    # -- Coverage summary (if available) -------------------------------

    if coverage:
        total_stmts = sum(s for _, s, _, _ in coverage)
        total_miss = sum(m for _, _, m, _ in coverage)
        overall = int(((total_stmts - total_miss) / total_stmts * 100) if total_stmts else 100)
        covered = total_stmts - total_miss

        lines.append("## Code Coverage")
        lines.append("")
        lines.append(f"**Overall: {overall}%**")
        lines.append("")
        lines.append(_coverageBar(overall))
        lines.append("")
        lines.append("```mermaid")
        lines.append("pie title Covered vs missed statements")
        lines.append(f'    "Covered" : {covered}')
        lines.append(f'    "Missed" : {total_miss}')
        lines.append("```")
        lines.append("")

        lines.append("### Per-file Coverage")
        lines.append("")
        lines.append("| File | Stmts | Miss | Coverage |")
        lines.append("| --- | ---: | ---: | --- |")

        for filename, stmts, miss, cover in coverage:
            link = _coverageFileLink(filename)
            lines.append(f"| {link} | {stmts} | {miss} | {_coverageBar(cover)} |")

        lines.append("")

        # Surface the files with the most missing lines first.
        worst = sorted(coverage, key=lambda row: (-row[2], row[3], row[0]))[:8]

        lines.append("### Coverage Priorities")
        lines.append("")
        lines.append("| File | Missing lines | Cover |")
        lines.append("| --- | ---: | ---: |")

        for filename, _stmts, miss, cover in worst:
            lines.append(f"| {_coverageFileLink(filename)} | {miss} | {cover}% |")

        lines.append("")

    # -- Detailed results grouped by module/class ----------------------

    lines.append("## Test Results")
    lines.append("")

    grouped = _groupResults(results)

    for module, classes in grouped.items():
        lines.append(f"### {_moduleLink(module)}")
        lines.append("")

        # Quote the module docstring under the heading, when there is one.
        doc = _moduleDocstring(module)

        if doc:
            for paragraph in doc.split("\n\n"):
                line = paragraph.replace("\n", " ").strip()

                if line:
                    lines.append(f"> {line}")
                    lines.append(">")

            if lines[-1] == ">":
                lines[-1] = ""
            else:
                lines.append("")

        # One result table per class (the empty class groups bare functions).
        for classname, tests in classes.items():
            if classname:
                lines.append(f"**{classname}**")
                lines.append("")

            lines.append("| Status | Test | Description | Time |")
            lines.append("| --- | --- | --- | ---: |")

            for test in tests:
                icon = _statusBadge(test["outcome"])
                desc = _escapeTableCell(test["description"])
                lines.append(f"| {icon} | {test['name']} | {desc} | {test['duration']:.3f}s |")

            lines.append("")

    # -- Failures (if any) ---------------------------------------------

    failures = [r for r in results if r["outcome"] in ("failed", "error")]

    if failures:
        lines.append("## Failures")
        lines.append("")

        for f in failures:
            lines.append(f"### {f['nodeid']}")
            lines.append("")
            lines.append("```")
            lines.append(f["longrepr"])
            lines.append("```")
            lines.append("")

    content = "\n".join(lines) + "\n"
    return content


def _groupResults(
    results: List[Dict[str, Any]],
) -> "OrderedDict[str, OrderedDict[str, List[Dict[str, Any]]]]":
    """Group results by module and class, preserving insertion order.

    Args:
        results: the collected per-test outcome records.

    Returns:
        OrderedDict[str, OrderedDict[str, List[Dict[str, Any]]]]: results keyed
        by module then class name (the empty class holds bare functions).
    """

    grouped: OrderedDict[str, OrderedDict[str, List[Dict[str, Any]]]] = OrderedDict()

    for r in results:
        nodeid = r["nodeid"]

        # nodeid looks like "tests/test_foo.py::TestClass::testMethod"
        # or "tests/test_foo.py::test_function".
        parts = nodeid.split("::")
        module = parts[0]

        if len(parts) == 3:
            classname = parts[1]
            testname = parts[2]
        elif len(parts) == 2:
            classname = ""
            testname = parts[1]
        else:
            classname = ""
            testname = nodeid

        # Create the module and class buckets on first sighting.
        if module not in grouped:
            grouped[module] = OrderedDict()

        if classname not in grouped[module]:
            grouped[module][classname] = []

        grouped[module][classname].append(
            {
                "name": testname,
                "outcome": r["outcome"],
                "duration": r["duration"],
                "description": r.get("description", ""),
            }
        )

    return grouped
