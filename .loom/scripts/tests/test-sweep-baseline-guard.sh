#!/bin/bash
# test-sweep-baseline-guard.sh - main-clean baseline creation under worktree
# isolation (sky130-opamp#188).
#
# The sweep coordinator used to build its baseline with ad-hoc Bash in the main
# checkout (`mkdir -p .loom/sweep-checkpoint`, `--snapshot <relative path>`),
# which the Bash-tool worktree-write-confinement guard correctly DENIES while a
# Loom-managed worktree exists. The fix routes creation through the bounded
# `sweep-run-registry.sh snapshot-baseline <RUN_ID>` helper instead of relaxing
# the guard. This suite proves, in a disposable repository with a managed
# worktree and the INSTALLED guard dispatcher + vendored guard + config copied
# in verbatim:
#   - the helper invocation (and the documented capture recipe and the
#     baseline consumer) is allowed;
#   - direct main-checkout mkdir, an unresolved-variable write, and arbitrary
#     main source writes are still denied — guard controls are unchanged;
#   - the allowed helper call, actually executed, writes only its contained
#     baseline and leaves main's tracked source untouched.
#
# Hermetic: no forge, network, or daemon. The guard runs under `env -i` with a
# throwaway HOME so no user-level Loom config or session env can leak in. The
# only variables passed are the decision-TELEMETRY toggle and its file path (so
# the stable deny pattern tag can be asserted); no guard control is touched.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOOM_DIR="$(cd "$SCRIPTS_DIR/.." && pwd)"
HOOKS_SRC="$LOOM_DIR/hooks"

for f in "$HOOKS_SRC/guard-destructive.sh" "$HOOKS_SRC/guard-destructive-generic.sh" \
    "$SCRIPTS_DIR/sweep-run-registry.sh" "$SCRIPTS_DIR/check-main-clean.sh"; do
    if [[ ! -f "$f" ]]; then
        echo "FAIL: required installed file missing: $f" >&2
        exit 1
    fi
done
if ! command -v jq >/dev/null 2>&1; then
    echo "FAIL: jq is required (the guard itself needs it)" >&2
    exit 1
fi

FIX_RAW="$(mktemp -d)"
FIX="$(cd -P "$FIX_RAW" && pwd -P)/repo"
FIX_HOME="$(cd -P "$FIX_RAW" && pwd -P)/home"
DECISION_LOG="$(cd -P "$FIX_RAW" && pwd -P)/guard-decisions.log"
LIVE_PID=""
cleanup() {
    [[ -n "$LIVE_PID" ]] && kill "$LIVE_PID" 2>/dev/null
    rm -rf "$FIX_RAW"
}
trap cleanup EXIT

mkdir -p "$FIX" "$FIX_HOME"
cd "$FIX" || exit 1
git init -q -b main . 2>/dev/null || git init -q .
git config user.email t@example.invalid
git config user.name t
mkdir -p .loom/hooks .loom/scripts
cp "$HOOKS_SRC/guard-destructive.sh" "$HOOKS_SRC/guard-destructive-generic.sh" .loom/hooks/
cp -R "$SCRIPTS_DIR/lib" .loom/scripts/lib
cp "$SCRIPTS_DIR/sweep-run-registry.sh" "$SCRIPTS_DIR/check-main-clean.sh" .loom/scripts/
[[ -f "$LOOM_DIR/config.json" ]] && cp "$LOOM_DIR/config.json" .loom/config.json
chmod +x .loom/hooks/*.sh .loom/scripts/*.sh
printf '.loom/worktrees/\n.loom/sweep-checkpoint/\n.loom/sweep-run/\n.loom/logs/\n' > .gitignore
echo 'int main(void) { return 0; }' > src.c
git add -A && git commit -q -m init

# A Loom-managed worktree: worktree isolation is now in play for this repo.
git worktree add -q .loom/worktrees/issue-1 -b feature/issue-1 2>/dev/null
printf '# Loom-managed worktree\n# Branch: feature/issue-1\n' > .loom/worktrees/issue-1/.loom-managed

PASS=0
FAIL=0

# guard <command> — run the fixture's installed dispatcher as a PreToolUse
# hook with cwd = the main checkout (where the sweep coordinator runs). Prints
# "deny:<pattern>", "ask", or "allow".
guard() {
    local cmd="$1" input out decision
    input=$(jq -n --arg c "$cmd" --arg cwd "$FIX" \
        '{hook_event_name:"PreToolUse", tool_name:"Bash", tool_input:{command:$c}, cwd:$cwd}')
    : > "$DECISION_LOG"
    out=$(printf '%s' "$input" | env -i PATH="$PATH" HOME="$FIX_HOME" \
        LOOM_GUARD_DECISION_LOG=1 LOOM_GUARD_DECISION_LOG_FILE="$DECISION_LOG" \
        bash "$FIX/.loom/hooks/guard-destructive.sh" 2>/dev/null)
    decision=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecision // empty' 2>/dev/null)
    case "$decision" in
        deny)
            # The JSONL decision log carries the stable pattern tag.
            local pat
            pat=$(jq -r '.pattern // empty' "$DECISION_LOG" 2>/dev/null | tail -n1)
            if [[ -z "$pat" ]]; then
                pat=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecisionReason' |
                    grep -o 'worktree-write-confinement[a-z-]*' | head -n1)
            fi
            echo "deny:${pat:-unknown}"
            ;;
        ask) echo "ask" ;;
        *) echo "allow" ;;
    esac
}

expect() {
    local desc="$1" want="$2" cmd="$3" got
    got=$(guard "$cmd")
    if [[ "$got" == "$want" ]]; then
        echo "PASS: $desc ($got)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $desc (expected $want, got $got) :: $cmd" >&2
        FAIL=$((FAIL + 1))
    fi
}

HOOK_ERRORS="$FIX/.loom/logs/hook-errors.log"

# A durable liveness PID for the registered run (reaped by the EXIT trap).
sleep 300 >/dev/null 2>&1 &
LIVE_PID=$!
RUN_ID=$(./.loom/scripts/sweep-run-registry.sh new --pid "$LIVE_PID")
BASELINE="$FIX/.loom/sweep-checkpoint/main-clean-baseline-${RUN_ID}.txt"

# --- Controls: guard confinement is armed and unchanged ---------------------
expect "direct main-checkout mkdir is denied" "deny:worktree-write-confinement" \
    "mkdir -p .loom/sweep-checkpoint"
expect "legacy direct baseline redirection into main is denied" "deny:worktree-write-confinement" \
    "git status --porcelain > .loom/sweep-checkpoint/main-clean-baseline-${RUN_ID}.txt"
# shellcheck disable=SC2016 # the literal, unexpanded variable IS the input
expect "unresolved-variable write is denied" "deny:worktree-write-confinement-unresolved-var" \
    'printf "%s\n" x > "$SWEEP_STATE_DIR/main-clean-baseline.txt"'
expect "arbitrary main source write (redirect) is denied" "deny:worktree-write-confinement" \
    "echo 'int x;' > src.c"
expect "arbitrary main source write (sed -i) is denied" "deny:worktree-write-confinement" \
    "sed -i 's/0/1/' src.c"

# --- The helper path is allowed --------------------------------------------
rm -f "$HOOK_ERRORS"
expect "snapshot-baseline helper invocation is allowed" "allow" \
    "./.loom/scripts/sweep-run-registry.sh snapshot-baseline ${RUN_ID}"
expect "documented capture recipe is allowed" "allow" \
    "MAIN_CLEAN_BASELINE=\"\$(./.loom/scripts/sweep-run-registry.sh snapshot-baseline ${RUN_ID})\" || MAIN_CLEAN_BASELINE=\"\"; echo \"MAIN_CLEAN_BASELINE=\${MAIN_CLEAN_BASELINE}\""
expect "baseline consumer (check-main-clean --baseline) is allowed" "allow" \
    "./.loom/scripts/check-main-clean.sh --baseline ${BASELINE} --quarantine --label \"run=${RUN_ID} issue=1\""
if [[ ! -s "$HOOK_ERRORS" ]]; then
    echo "PASS: allows were real decisions, not an ERR-trap fail-open"
    PASS=$((PASS + 1))
else
    echo "FAIL: guard logged hook errors during allowed cases:" >&2
    cat "$HOOK_ERRORS" >&2
    FAIL=$((FAIL + 1))
fi

# --- Execute the allowed call: contained write only --------------------------
src_before=$(git hash-object src.c)
out=$(./.loom/scripts/sweep-run-registry.sh snapshot-baseline "$RUN_ID" 2>/dev/null)
rc=$?
if [[ $rc -eq 0 && "$out" == "$BASELINE" && -f "$BASELINE" && ! -L "$BASELINE" ]]; then
    echo "PASS: executed helper wrote the contained baseline and printed its path"
    PASS=$((PASS + 1))
else
    echo "FAIL: helper rc=$rc out='$out' (expected $BASELINE)" >&2
    FAIL=$((FAIL + 1))
fi
if [[ "$(git hash-object src.c)" == "$src_before" && -z "$(git status --porcelain)" ]]; then
    echo "PASS: main checkout source and status untouched by the helper"
    PASS=$((PASS + 1))
else
    echo "FAIL: helper changed main's tracked state: $(git status --porcelain)" >&2
    FAIL=$((FAIL + 1))
fi

echo
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] || exit 1
