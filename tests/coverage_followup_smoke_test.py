from __future__ import annotations

import os
import re
import subprocess
import tempfile
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ACTION = REPO / '.github/actions/rust-coverage/action.yml'
SCRIPT = REPO / '.github/actions/rust-check/diff-coverage.sh'


def require(pattern: str, text: str, message: str) -> None:
    if not re.search(pattern, text, re.MULTILINE | re.DOTALL):
        raise AssertionError(message)


def test_action_uses_env_for_regex_plumbing() -> None:
    text = ACTION.read_text()
    require(
        r"- name: Build combined ignore regex.*?env:\s*\n\s*EXTRA_IGNORE_REGEX: \$\{\{ inputs\.extra-ignore-regex \}\}.*?if \[\[ -n \"\$EXTRA_IGNORE_REGEX\" \]\]; then.*?COMBINED=\"\$\{COMBINED\}\|\$EXTRA_IGNORE_REGEX\".*?printf 'pattern=%s\\n' \"\$COMBINED\" >> \"\$GITHUB_OUTPUT\"",
        text,
        'build step must use env-backed EXTRA_IGNORE_REGEX and printf to GITHUB_OUTPUT',
    )
    require(
        r"- name: Test with coverage.*?env:.*?IGNORE_REGEX: \$\{\{ steps\.ignore-regex\.outputs\.pattern \}\}.*?--ignore-filename-regex \"\$IGNORE_REGEX\"",
        text,
        'test step must pass ignore regex via env and shell variable',
    )
    require(
        r"- name: Enforce global coverage.*?env:.*?IGNORE_REGEX: \$\{\{ steps\.ignore-regex\.outputs\.pattern \}\}.*?--ignore-filename-regex \"\$IGNORE_REGEX\".*?--ignore-filename-regex \"\$IGNORE_REGEX\"",
        text,
        'enforce step must pass ignore regex via env and shell variable for both reports',
    )
    require(
        r"- name: Coverage summary.*?env:.*?IGNORE_REGEX: \$\{\{ steps\.ignore-regex\.outputs\.pattern \}\}.*?--ignore-filename-regex \"\$IGNORE_REGEX\" 2>&1",
        text,
        'summary step must pass ignore regex via env and shell variable',
    )


def test_diff_coverage_usage_mentions_both_thresholds() -> None:
    text = SCRIPT.read_text()
    expected = '<lcov-file> <base-sha> <pr-number> [diff-threshold] [global-threshold]'
    if expected not in text:
        raise AssertionError('usage text must document diff and global thresholds')


def test_diff_coverage_global_threshold_contract() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        repo = tmp_path / 'repo'
        repo.mkdir()
        subprocess.run(['git', 'init', '-b', 'main'], cwd=repo, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo, check=True)

        src = repo / 'src'
        src.mkdir()
        target = src / 'lib.rs'
        target.write_text('fn before() {}\n')
        subprocess.run(['git', 'add', 'src/lib.rs'], cwd=repo, check=True)
        subprocess.run(['git', 'commit', '-m', 'base'], cwd=repo, check=True, stdout=subprocess.DEVNULL)
        base_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
        target.write_text('fn after() {}\n')
        subprocess.run(['git', 'add', 'src/lib.rs'], cwd=repo, check=True)
        subprocess.run(['git', 'commit', '-m', 'head'], cwd=repo, check=True, stdout=subprocess.DEVNULL)

        lcov = repo / 'lcov.info'
        lcov.write_text(textwrap.dedent('''\
            TN:
            SF:src/lib.rs
            DA:1,1
            LF:2
            LH:1
            end_of_record
        '''))

        gh = tmp_path / 'gh'
        gh.write_text(textwrap.dedent('''\
            #!/usr/bin/env bash
            set -euo pipefail
            if [[ "$1" == "api" ]]; then
              exit 0
            fi
            if [[ "$1" == "pr" && "$2" == "comment" ]]; then
              printf '%s' "$5" > "$GH_CAPTURE"
              exit 0
            fi
            exit 1
        '''))
        gh.chmod(0o755)

        env = os.environ.copy()
        env['PATH'] = f"{tmp_path}:{env['PATH']}"
        env['GITHUB_REPOSITORY'] = 'owner/repo'

        capture_5 = tmp_path / 'comment-5.txt'
        env['GH_CAPTURE'] = str(capture_5)
        result = subprocess.run(
            ['bash', str(SCRIPT), str(lcov), base_sha, '123', '95', '60'],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(f'5-arg invocation should pass diff threshold check: {result.stderr}\n{result.stdout}')
        body_5 = capture_5.read_text()
        if '| Global | 50.0% | 60% | Fail |' not in body_5:
            raise AssertionError('global row must use arg 5 threshold')
        if '| Diff | 100.0% | 95% | Pass |' not in body_5:
            raise AssertionError('diff row must use arg 4 threshold')

        capture_4 = tmp_path / 'comment-4.txt'
        env['GH_CAPTURE'] = str(capture_4)
        result = subprocess.run(
            ['bash', str(SCRIPT), str(lcov), base_sha, '123', '95'],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(f'4-arg invocation should still pass diff threshold check: {result.stderr}\n{result.stdout}')
        body_4 = capture_4.read_text()
        if '| Global | 50.0% | 95% | Fail |' not in body_4:
            raise AssertionError('global threshold must fall back to diff threshold when arg 5 is omitted')


if __name__ == '__main__':
    test_action_uses_env_for_regex_plumbing()
    test_diff_coverage_usage_mentions_both_thresholds()
    test_diff_coverage_global_threshold_contract()
    print('ok')
