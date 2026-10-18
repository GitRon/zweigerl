#!/usr/bin/env bash
# Runs the gates from .github/workflows/tests.yml locally - the lock file, the hooks, the suite, the import
# contracts and the stylesheet build - plus the one gate no CI run can have, and records the outcome.
#
# Usage: bash .claude/skills/implement-story/scripts/ci.sh .claude/runs/<slug>
# Exit code: 0 when every gate passes, 1 otherwise.

set -uo pipefail

RUN_DIR="${1:?usage: ci.sh <run-dir>}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1

# A drive letter is an absolute path too. Without that arm "C:/workspace/..." falls through as relative
# and gets the repo root prefixed onto it, so ci.md and the logs land in a directory nobody reads.
case "$RUN_DIR" in
  /*) ;;
  ?:/*) ;;
  *) RUN_DIR="$REPO_ROOT/$RUN_DIR" ;;
esac

LOG_DIR="$RUN_DIR/ci-logs"
mkdir -p "$LOG_DIR"
OUT="$RUN_DIR/ci.md"

# "--all-files" means every file git tracks, so a file the story created and has not staged yet is never
# linted - and the commit hook is the first thing to see it. Marking those files intent-to-add puts them
# in the list pre-commit reads without staging their content, and the trap takes the marks off again on
# any exit, so the index is left exactly as it was found. Naming them with "--files" instead would not
# scale: the whole tree's paths overrun the Windows command line.
UNTRACKED_LIST="$(mktemp)"
git ls-files --others --exclude-standard -z > "$UNTRACKED_LIST"
restore_index() {
  if [ -s "$UNTRACKED_LIST" ]; then
    xargs -0 git reset --quiet -- < "$UNTRACKED_LIST"
  fi
  rm -f "$UNTRACKED_LIST"
}
trap restore_index EXIT
if [ -s "$UNTRACKED_LIST" ]; then
  xargs -0 git add --intent-to-add -- < "$UNTRACKED_LIST"
fi

# pre-commit itself is not a project dependency: a machine-wide install is used when there is one, uvx
# otherwise, which is what docs/contributing/linting.md tells a contributor to run.
if command -v pre-commit > /dev/null 2>&1; then
  PRE_COMMIT=(pre-commit)
else
  PRE_COMMIT=(uvx pre-commit)
fi

# The formatting hooks rewrite files and then fail the very run that rewrote them, so a single red pass
# proves nothing. The second pass on the rewritten tree is the honest signal - hence a retry, not a loop.
"${PRE_COMMIT[@]}" run --all-files > "$LOG_DIR/pre-commit.log" 2>&1
lint_status=$?
lint_passes=1
if [ $lint_status -ne 0 ]; then
  "${PRE_COMMIT[@]}" run --all-files > "$LOG_DIR/pre-commit.log" 2>&1
  lint_status=$?
  lint_passes=2
fi
# Only the lint gate needs the marks. Taken off now rather than at exit, so a run killed during the suite
# does not leave them behind for "git status" to report
restore_index
trap - EXIT

# CI installs with "uv sync --locked", which refuses a uv.lock that no longer matches pyproject.toml. The
# "uv run" calls below would quietly re-lock instead, so the check is its own gate.
uv lock --check > "$LOG_DIR/uv-lock.log" 2>&1
lock_status=$?

# Coverage config lives in pyproject.toml and fails below 100% branch coverage, so this one command is
# both the test gate and the coverage gate.
uv run pytest --cov > "$LOG_DIR/pytest.log" 2>&1
test_status=$?

# The import contracts live in pyproject.toml and are a step of their own in CI, outside pre-commit
# and the suite - so neither gate above sees a module importing across a boundary it may not cross.
uv run lint-imports > "$LOG_DIR/lint-imports.log" 2>&1
imports_status=$?

# CI's "assets" job: the stylesheet is compiled, not committed, so this is the only thing that notices a
# build that has stopped working. It writes to static/dist/, which is gitignored.
yarn build:css > "$LOG_DIR/build-css.log" 2>&1
assets_status=$?

# The suite above already refuses a migration graph with two leaves - "migrate" raises before a single
# database test runs. What it cannot see is the neighbouring worktree holding the other 0009, because
# that number only becomes a conflict once both branches are in the same tree. By then the run that
# would have caught it is a green tick on a merged pull request.
BASE_REF="$(sed -n 's/.*"base"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$RUN_DIR/state.json" 2>/dev/null | head -n 1)"
bash "$REPO_ROOT/.claude/skills/implement-story/scripts/migration-numbers.sh" "${BASE_REF:-github/main}" \
  > "$LOG_DIR/migration-numbers.log" 2>&1
migration_status=$?

verdict() { [ "$1" -eq 0 ] && echo "PASS" || echo "FAIL"; }

# A number shared with a neighbour exits 0 and still has something to say: that branch may never land,
# so it is worth a line in the report and not worth blocking on.
migration_verdict="PASS"
if [ $migration_status -ne 0 ]; then
  migration_verdict="FAIL"
elif [ -s "$LOG_DIR/migration-numbers.log" ]; then
  migration_verdict="WARN"
fi

{
  echo "# CI gates"
  echo
  echo "Commit: \`$(git rev-parse --short HEAD 2>/dev/null || echo unknown)\` on branch \`$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\`"
  echo
  echo "| Gate | Command | Result |"
  echo "|---|---|---|"
  echo "| Lock file | \`uv lock --check\` | $(verdict $lock_status) |"
  echo "| Lint | \`pre-commit run --all-files\` ($lint_passes pass(es)) | $(verdict $lint_status) |"
  echo "| Tests + coverage | \`uv run pytest --cov\` | $(verdict $test_status) |"
  echo "| Import boundaries | \`uv run lint-imports\` | $(verdict $imports_status) |"
  echo "| Stylesheet | \`yarn build:css\` | $(verdict $assets_status) |"
  echo "| Migration numbers | \`migration-numbers.sh ${BASE_REF:-github/main}\` | $migration_verdict |"
  echo
  if [ $lint_status -ne 0 ]; then
    echo "## pre-commit (last 60 lines)"
    echo
    echo '```'
    tail -n 60 "$LOG_DIR/pre-commit.log"
    echo '```'
    echo
  fi
  if [ $test_status -ne 0 ]; then
    echo "## pytest (last 80 lines)"
    echo
    echo '```'
    tail -n 80 "$LOG_DIR/pytest.log"
    echo '```'
    echo
  fi
  if [ $lock_status -ne 0 ]; then
    echo "## uv lock --check"
    echo
    echo '```'
    tail -n 20 "$LOG_DIR/uv-lock.log"
    echo '```'
    echo
  fi
  if [ $assets_status -ne 0 ]; then
    echo "## yarn build:css (last 40 lines)"
    echo
    echo '```'
    tail -n 40 "$LOG_DIR/build-css.log"
    echo '```'
    echo
  fi
  if [ $imports_status -ne 0 ]; then
    echo "## lint-imports (last 40 lines)"
    echo
    echo '```'
    tail -n 40 "$LOG_DIR/lint-imports.log"
    echo '```'
    echo
  fi
  if [ "$migration_verdict" != "PASS" ]; then
    echo "## Migration numbers"
    echo
    echo '```'
    cat "$LOG_DIR/migration-numbers.log"
    echo '```'
    echo
  fi
  echo "Full output: \`${LOG_DIR#"$REPO_ROOT/"}/\`"
} > "$OUT"

cat "$OUT"

if [ $lock_status -eq 0 ] && [ $lint_status -eq 0 ] && [ $test_status -eq 0 ] && [ $imports_status -eq 0 ] \
  && [ $assets_status -eq 0 ] && [ $migration_status -eq 0 ]; then
  exit 0
fi
exit 1
