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


def test_timeout_exit_only_passes_when_no_mutants_are_missed() -> None:
    text = ACTION.read_text()
    require(
        r'- name: Mutation testing summary.*?echo "missed-count=\$MISSED" >> "\$GITHUB_OUTPUT".*?echo "timeout-count=\$TIMEOUT" >> "\$GITHUB_OUTPUT"',
        text,
        "summary step must export missed and timeout counts for the final gate",
    )
    require(
        r'- name: Fail on missed mutants.*?3\).*?if \[ "\$\{\{ steps\.summary\.outputs\.missed-count \}\}" -gt 0 \]; then.*?exit 1.*?fi.*?exit 0',
        text,
        "exit code 3 must fail when missed mutants are present and pass otherwise",
    )


def test_unexpected_exit_codes_fail_the_job() -> None:
    text = ACTION.read_text()
    require(r"- name: Fail on missed mutants.*?case", text, "final gate must use a case statement")
    for expected in (
        'case "${{ steps.mutants.outputs.exit-code }}" in',
        '0)',
        '2|4)',
        '3)',
        'if [ "${{ steps.summary.outputs.missed-count }}" -gt 0 ]; then',
        'echo "::error::Mutation testing timed out and also left surviving mutants."',
        'echo "::warning::Some mutants timed out, but none survived."',
        'echo "::error::Unexpected cargo-mutants exit code: ${{ steps.mutants.outputs.exit-code }}"',
    ):
        if expected not in text:
            raise AssertionError(f"missing expected final-gate snippet: {expected}")
    if text.count("exit 1") < 3:
        raise AssertionError("final gate must fail known failures, timeout+missed runs, and unexpected exit codes")


if __name__ == "__main__":
    test_mutation_command_keeps_timeout_multiplier_without_in_place()
    test_timeout_exit_only_passes_when_no_mutants_are_missed()
    test_unexpected_exit_codes_fail_the_job()
    print("ok")
