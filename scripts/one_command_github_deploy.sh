#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# ONE-COMMAND FOOLPROOF GITHUB CLEAN DEPLOY & WORKFLOW RUNNER (V5.0)
# Usage: bash scripts/one_command_github_deploy.sh
# - Resets messy commit history into a single clean commit on `main`
#   (NEVER touches GitHub Repository Settings or Actions Secrets!)
# - Runs all 51 local verification checks before pushing
# - Triggers `.github/workflows/ai-game-studio.yml` and monitors until green
# ==============================================================================

python3 test/run_v2_verification_suite.py

if [ -d .git ]; then
  git checkout --orphan clean-studio-v5-main || true
  git add -A
  git commit -m "AI Game Studio V5.0 Final Master (Clean History + Positive/Negative Review Upgrades + Fast 3m QA)"
  git branch -M main
  git push -f origin main
fi

if command -v gh >/dev/null 2>&1; then
  gh workflow run ai-game-studio.yml --ref main
  sleep 5
  RUN_ID=$(gh run list --workflow=ai-game-studio.yml --limit 1 --json databaseId --jq '.[0].databaseId')
  echo "Triggered GitHub Actions Run ID: $RUN_ID"
  gh run watch "$RUN_ID" --exit-status
fi
