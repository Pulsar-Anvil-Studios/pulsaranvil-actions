from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ACTION = REPO / ".github/actions/rust-mutants/action.yml"


def require(pattern: str, text: str, message: str) -> None:
    if not re.search(pattern, text, re.MULTILINE | re.DOTALL):
        raise AssertionError(message)


def test_mutation_command_keeps_timeout_multiplier_without_in_place() -> None:
    text = ACTION.read_text()
    require(
        r"- name: Run mutation testing.*?cargo mutants \\\s+--in-diff /tmp/pr\.diff \\\s+(?:(?!--in-place).)*--test-tool \$\{\{ inputs\.test-tool \}\} \\\s+--timeout-multiplier \$\{\{ inputs\.timeout-multiplier \}\}",
        text,
        "mutation command must keep timeout-multiplier wiring without using --in-place",
    )
    if "--in-place" in text:
        raise AssertionError("rust-mutants action must not use --in-place")


def test_unexpected_exit_codes_fail_the_job() -> None:
    text = ACTION.read_text()
    require(r"- name: Fail on missed mutants.*?case", text, "final gate must use a case statement")
    for expected in (
        'case "${{ steps.mutants.outputs.exit-code }}" in',
        "0|3)",
        "2|4)",
        'echo "::error::Unexpected cargo-mutants exit code: ${{ steps.mutants.outputs.exit-code }}"',
    ):
        if expected not in text:
            raise AssertionError(f"missing expected final-gate snippet: {expected}")
    if text.count("exit 1") < 2:
        raise AssertionError("final gate must fail both known-failing and unexpected exit codes")


if __name__ == "__main__":
    test_mutation_command_keeps_timeout_multiplier_without_in_place()
    test_unexpected_exit_codes_fail_the_job()
    print("ok")
