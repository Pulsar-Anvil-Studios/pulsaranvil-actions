from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ACTION = REPO / ".github/actions/rust-mutants-full/action.yml"


def require(pattern: str, text: str, message: str) -> None:
    if not re.search(pattern, text, re.MULTILINE | re.DOTALL):
        raise AssertionError(message)


def test_full_mutation_command_keeps_timeout_multiplier_without_in_place() -> None:
    text = ACTION.read_text()
    require(
        r"- name: Run full mutation testing .*?cargo mutants \\\s+--shard \$\{\{ inputs\.shard \}\}/\$\{\{ inputs\.total-shards \}\} \\\s+(?:(?!--in-place).)*--test-tool \$\{\{ inputs\.test-tool \}\} \\\s+--timeout-multiplier \$\{\{ inputs\.timeout-multiplier \}\}",
        text,
        "full mutation command must keep timeout-multiplier wiring without using --in-place",
    )
    if "--in-place" in text:
        raise AssertionError("rust-mutants-full action must not use --in-place")


def test_fail_on_survivors_only_controls_exit_code_2() -> None:
    text = ACTION.read_text()
    require(r"- name: Fail on missed mutants.*?case", text, "final gate must use a case statement")
    for expected in (
        'case "${{ steps.mutants.outputs.exit-code }}" in',
        "0|3)",
        "2)",
        'if [[ "${{ inputs.fail-on-survivors }}" == \'true\' ]]; then',
        "4)",
        "exit 1",
        'echo "::error::Unexpected cargo-mutants exit code: ${{ steps.mutants.outputs.exit-code }}"',
    ):
        if expected not in text:
            raise AssertionError(f"missing expected final-gate snippet: {expected}")
    if "2|4)" in text:
        raise AssertionError("exit code 4 must not be gated behind fail-on-survivors")
    require(r"4\)\s+exit 1", text, "exit code 4 must fail unconditionally")


def test_fail_on_survivors_description_matches_behavior() -> None:
    text = ACTION.read_text()
    expected = 'description: "When true, fail the action if mutants survive; baseline failures and unexpected errors still fail"'
    if expected not in text:
        raise AssertionError("fail-on-survivors description must match survivor-only semantics")


def test_upload_and_summary_behavior_remain_present() -> None:
    text = ACTION.read_text()
    require(
        r"- name: Upload mutation results.*?uses: actions/upload-artifact@v4.*?name: mutants-shard-\$\{\{ inputs\.shard \}\}.*?path: mutants\.out/",
        text,
        "full action must upload shard mutation results artifact",
    )
    require(
        r"- name: Shard summary.*?\| Metric \| Count \|.*?\| Caught \| \$CAUGHT \|.*?\| Missed \| \$MISSED \|.*?\| Timeout \| \$TIMEOUT \|",
        text,
        "full action must keep markdown shard summary counts",
    )
    require(
        r"- name: Shard summary.*?### Missed Mutants.*?cat mutants\.out/missed\.txt",
        text,
        "full action summary must include missed mutant details when present",
    )


if __name__ == "__main__":
    test_full_mutation_command_keeps_timeout_multiplier_without_in_place()
    test_fail_on_survivors_only_controls_exit_code_2()
    test_fail_on_survivors_description_matches_behavior()
    test_upload_and_summary_behavior_remain_present()
    print("ok")
