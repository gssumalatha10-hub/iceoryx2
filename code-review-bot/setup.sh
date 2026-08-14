#!/bin/bash
# Setup script for Eclipse iceoryx Code Review Bot
# Installs the bot in a forked iceoryx repository

set -e

REVIEW_BOT_REPO="${1:-.}"
TARGET_ICEORYX_PATH="${2:-.}"

echo "🚀 Setting up iceoryx Code Review Bot"
echo "  Review Bot: $REVIEW_BOT_REPO"
echo "  Target iceoryx: $TARGET_ICEORYX_PATH"

if [ ! -d "$REVIEW_BOT_REPO/src" ]; then
    echo "❌ Error: Invalid review bot path $REVIEW_BOT_REPO"
    exit 1
fi

if [ ! -d "$TARGET_ICEORYX_PATH/.git" ]; then
    echo "❌ Error: $TARGET_ICEORYX_PATH is not a git repository"
    exit 1
fi

if ! command -v git >/dev/null 2>&1; then
    echo "❌ Error: git is not installed or not available on PATH"
    exit 1
fi

if ! command -v cmake >/dev/null 2>&1; then
    echo "❌ Error: cmake is not installed or not available on PATH"
    exit 1
fi

if ! command -v clang >/dev/null 2>&1 || ! command -v clang-tidy >/dev/null 2>&1; then
    echo "❌ Error: clang/clang-tidy is not installed or not available on PATH"
    echo "   Install LLVM tools such as clang, clang-tidy, and scan-build for full analysis support."
    exit 1
fi

if ! command -v scan-build >/dev/null 2>&1; then
    echo "❌ Error: scan-build is not installed or not available on PATH"
    echo "   Install clang static analyzer tools to enable the Clang Static Analyzer step."
    exit 1
fi

# Copy workflow to target
echo "📋 Installing GitHub Actions workflow..."
mkdir -p "$TARGET_ICEORYX_PATH/.github/workflows"
cp "$REVIEW_BOT_REPO/.github/workflows/code-review.yml" \
   "$TARGET_ICEORYX_PATH/.github/workflows/"

# Copy bot source and config
echo "📦 Copying bot source and config..."
mkdir -p "$TARGET_ICEORYX_PATH/.github/review-bot"
cp "$REVIEW_BOT_REPO/src"/*.py "$TARGET_ICEORYX_PATH/.github/review-bot/"
cp "$REVIEW_BOT_REPO/review-config.yaml" "$TARGET_ICEORYX_PATH/.github/review-bot/"
cp "$REVIEW_BOT_REPO/requirements.txt" "$TARGET_ICEORYX_PATH/.github/review-bot/"

# Create a setup README
echo "📝 Creating setup documentation..."
cat > "$TARGET_ICEORYX_PATH/.github/review-bot/SETUP.md" << 'EOF'
# Code Review Bot Setup

The code review bot has been installed in your iceoryx fork. Here's what you need to do:

## 1. Configure GitHub Token

The bot needs a GitHub token to post comments on PRs. Create one:

1. Go to GitHub Settings → Personal Access Tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Grant these scopes:
   - `repo` (full control of private repositories)
   - `pull-requests` (read and write to PRs)
   - `checks` (read and write checks)
4. Copy the token

## 2. Add Secret to Repository

1. Go to your fork's Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `GITHUB_TOKEN`
4. Value: Paste your token

## 3. Enable GitHub Actions

1. Go to your fork's Actions tab
2. Click "I understand my workflows, go ahead and enable them"

## 4. Test on a Pull Request

1. Create a small test branch with a C++ code change
2. Open a PR
3. The bot should automatically run and post results

## 5. Customize Configuration

Edit `.github/review-bot/review-config.yaml` to:
- Enable/disable analyzers
- Adjust rule mappings
- Change severity levels
- Add project-specific rules

## Troubleshooting

### Bot doesn't run on PR
- Check that Actions are enabled
- Verify the workflow file is at `.github/workflows/code-review.yml`
- Check the Actions tab for error logs

### Bot runs but no comments appear
- Ensure GITHUB_TOKEN has correct permissions
- Check that the repository secret is set
- Look at the workflow logs for errors

### Build fails
- Check that iceoryx can be built with CMake
- Verify clang-18 is available (handled by workflow)
- Review the build log in the workflow output

### No findings reported
- This might be correct if the PR has no new issues
- Check `.review-results/review-results.json` artifact
- Review the inline check run summary

## Support

For issues with the bot, check:
1. Workflow logs: Actions tab → Latest run
2. Artifacts: `.review-results/` directory
3. This file and the main README.md
EOF

# Create a local test script
echo "🧪 Creating local test script..."
cat > "$TARGET_ICEORYX_PATH/.github/review-bot/test-local.sh" << 'EOF'
#!/bin/bash
# Local test script for code review bot

set -e

REPO_DIR="${1:-.}"
CONFIG_DIR="$(dirname "${BASH_SOURCE[0]}")"

echo "Testing code review bot locally..."
echo "  Repository: $REPO_DIR"
echo "  Config: $CONFIG_DIR"

# Ensure dependencies
echo "Installing dependencies..."
pip3 install -q pyyaml

# Run analysis
echo "Running analysis..."
python3 "$CONFIG_DIR/review_orchestrator.py" \
  --repo "$REPO_DIR" \
  --config "$CONFIG_DIR/review-config.yaml" \
  --pr-base main \
  --pr-head HEAD \
  --output "$REPO_DIR/.review-results-local.json"

echo "✓ Analysis complete!"
echo "  Results: $REPO_DIR/.review-results-local.json"

# Print summary
python3 - "$REPO_DIR/.review-results-local.json" << 'PYTHON'
import json, sys
with open(sys.argv[1]) as f:
    r = json.load(f)
    if r['status'] == 'success':
        s = r['summary']
        print(f"\nSummary:")
        print(f"  Total: {s['total_findings']}")
        print(f"  Critical: {s['by_severity'].get('critical', 0)}")
        print(f"  Major: {s['by_severity'].get('major', 0)}")
        print(f"  Minor: {s['by_severity'].get('minor', 0)}")
PYTHON
EOF

chmod +x "$TARGET_ICEORYX_PATH/.github/review-bot/test-local.sh"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📖 Next steps:"
echo "  1. Add GITHUB_TOKEN secret to your fork's repository settings"
echo "  2. Enable GitHub Actions if not already enabled"
echo "  3. Open a test PR to trigger the bot"
echo "  4. Check .github/review-bot/SETUP.md for detailed instructions"
echo ""
echo "🧪 To test locally:"
echo "  cd $TARGET_ICEORYX_PATH"
echo "  .github/review-bot/test-local.sh ."
echo ""
