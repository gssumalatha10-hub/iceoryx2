# Implementation Guide: Eclipse iceoryx Code Review Bot MVP

This guide describes the complete implementation and deployment steps for the code review bot.

## Project Structure

```
code-review-bot/
├── src/
│   ├── review_orchestrator.py      # Main analysis pipeline
│   ├── github_reporter.py         # GitHub PR integration
│   └── baseline_manager.py        # Baseline tracking & deduplication
├── .github/workflows/
│   └── code-review.yml            # GitHub Actions workflow
├── review-config.yaml             # Configuration & rule mappings
├── requirements.txt               # Python dependencies
├── setup.sh                       # Installation script
└── README.md                      # User documentation
```

## Components

### 1. Review Orchestrator (`src/review_orchestrator.py`)

**Responsibilities:**
- Clone and build Eclipse iceoryx with compile_commands.json
- Run static analyzers (clang-tidy, clang-analyzer, compiler)
- Normalize findings to SARIF format
- Filter for new findings only
- Generate summary statistics

**Key Classes:**
- `Finding`: Dataclass representing a code issue
- `CodeReviewOrchestrator`: Main pipeline orchestration

**Input:**
```bash
python3 src/review_orchestrator.py \
  --repo /path/to/iceoryx \
  --config review-config.yaml \
  --pr-base main \
  --pr-head feature-branch \
  --output review-results.json
```

**Output:**
- `review-results.json`: Results with findings, summary, and status
- `.review-results/review-results.sarif`: SARIF report for Code Scanning
- Build logs and analyzer outputs

### 2. GitHub Reporter (`src/github_reporter.py`)

**Responsibilities:**
- Read review results from JSON
- Post check runs to PR
- Add inline comments on changed files
- Upload SARIF to Code Scanning
- Generate markdown reports
- Handle GitHub API errors gracefully

**Key Classes:**
- `ReviewComment`: Individual PR comment
- `GitHubReportGenerator`: GitHub integration

**Environment Variables:**
```bash
GITHUB_TOKEN          # GitHub API token
GITHUB_REPOSITORY     # "owner/repo"
GITHUB_PR_NUMBER      # PR number
GITHUB_RUN_ID         # Workflow run ID
GITHUB_ACTIONS        # "true" when in Actions
```

**Usage:**
```bash
python3 src/github_reporter.py \
  --results review-results.json \
  --post-check \
  --post-comments \
  --generate-report \
  --output review-report.md
```

### 3. Baseline Manager (`src/baseline_manager.py`)

**Responsibilities:**
- Track historical findings in `.review-baseline.json`
- Mark issues as fixed, suppressed, or false-positive
- Filter only new findings for PR reporting
- Deduplicate findings from multiple tools
- Compute stable fingerprints

**Key Classes:**
- `BaselineManager`: Tracks and manages findings
- `DeduplicationManager`: Removes duplicates

**Usage:**
```bash
python3 src/baseline_manager.py \
  --results review-results.json \
  --baseline .review-baseline.json \
  --output filtered-results.json
```

### 4. Configuration (`review-config.yaml`)

**Sections:**

| Section | Purpose |
|---------|---------|
| `review_policy` | Merge gate, reporting behavior, exclusions |
| `analyzers` | Enable/disable tools, set versions, flags |
| `rule_mappings` | Map tool checks to MISRA/AUTOSAR/project rules |
| `suppressions` | Patterns to ignore (test files, etc.) |
| `severity_levels` | Define priority and actions |
| `quality_targets` | Optional metrics |

**Example Custom Rule:**

```yaml
rule_mappings:
  - id: "PROJECT-NAMING-001"
    tool: "clang-tidy"
    check: "readability-identifier-naming"
    severity: "minor"
    standards: ["project-policy"]
    description: "Variable naming must follow snake_case"
    remediation: "Rename to lowercase_with_underscores"
```

### 5. GitHub Actions Workflow (`.github/workflows/code-review.yml`)

**Triggers:** Pull request (opened, synchronize, reopened) or manual

**Steps:**
1. Checkout iceoryx and review-bot
2. Setup build environment (Ubuntu 22.04, clang-18, CMake)
3. Run review orchestrator
4. Post check run and comments to PR
5. Upload artifacts and SARIF

**Environment:**
- Container: `ubuntu:22.04`
- Clang: v18
- Python: 3.x
- Memory: Sufficient for iceoryx build
- Timeout: ~30 minutes per PR

## Installation Steps

### For Repository Maintainers

#### Step 1: Create a fork of iceoryx (if you haven't already)

```bash
# At GitHub: Fork https://github.com/eclipse-iceoryx/iceoryx
# Clone your fork
git clone https://github.com/<your-username>/iceoryx.git
cd iceoryx
```

#### Step 2: Clone the review bot

```bash
cd /path/to/your/workspace
git clone <THIS-REPO> code-review-agent
```

#### Step 3: Run setup script

```bash
cd code-review-agent
./setup.sh . /path/to/your/iceoryx/fork
```

This will:
- Copy `.github/workflows/code-review.yml` to your fork
- Copy bot source, config, and dependencies to `.github/review-bot/`
- Create setup documentation

#### Step 4: Create GitHub token

1. Go to GitHub Settings → Personal Access Tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select scopes:
   - `repo` (full control)
   - `pull-requests` (PR access)
   - `checks` (check runs)
4. Copy the token

#### Step 5: Add repository secret

In your forked iceoryx repository:

1. Settings → Secrets and variables → Actions
2. "New repository secret"
3. Name: `GITHUB_TOKEN`
4. Value: Paste the token from Step 4

#### Step 6: Enable Actions (if needed)

1. Go to Actions tab
2. "I understand my workflows, go ahead and enable them"

#### Step 7: Open a test PR

1. Create a minimal test branch with a C++ change
2. Open a PR
3. The bot should comment within 5-10 minutes

### For Local Testing

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run analysis locally
cd /path/to/iceoryx
python3 /path/to/code-review-bot/src/review_orchestrator.py \
  --repo . \
  --config /path/to/code-review-bot/review-config.yaml \
  --pr-base main \
  --pr-head your-branch \
  --output results.json

# View results
cat results.json | jq '.summary'

# Generate markdown report
python3 /path/to/code-review-bot/src/github_reporter.py \
  --results results.json \
  --generate-report \
  --output report.md
```

## Workflow Execution Flow

```
┌────────────────────────────────────────────┐
│ Developer opens PR on forked iceoryx       │
└─────────────────┬──────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────────┐
│ GitHub Actions workflow triggered          │
│ (code-review.yml)                          │
└─────────────────┬──────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
    Checkout            Setup
    iceoryx             environment
    + review-bot        (clang-18,
                        CMake, Python)
        │                   │
        └─────────┬─────────┘
                  │
                  ▼
        ┌──────────────────────┐
        │  Build iceoryx       │
        │  Generate compile_   │
        │  commands.json       │
        └─────────┬────────────┘
                  │
        ┌─────────┴─────────────────────┐
        │                               │
        ▼                               ▼
   Run clang-tidy              Run compiler +
   + clang-analyzer            clang-analyzer
        │                               │
        └─────────┬─────────────────────┘
                  │
                  ▼
        ┌──────────────────────┐
        │ Normalize &          │
        │ Deduplicate          │
        │ findings             │
        └─────────┬────────────┘
                  │
                  ▼
        ┌──────────────────────┐
        │ Filter new findings  │
        │ (vs baseline)        │
        └─────────┬────────────┘
                  │
        ┌─────────┴──────────────────────┐
        │                                │
        ▼                                ▼
   Post check run            Upload SARIF
   + PR summary              to Code
        │                    Scanning
        │                        │
        ▼                        ▼
   Post inline           Generate
   comments              markdown
   (high-severity)       report
        │                        │
        └─────────┬──────────────┘
                  │
                  ▼
     ┌────────────────────────────────┐
     │ Results visible on PR:         │
     │ - Check summary               │
     │ - Inline comments             │
     │ - Code Scanning alerts        │
     │ - Artifacts for download      │
     └────────────────────────────────┘
```

## Customization Examples

### Example 1: Enforce only critical findings

**Edit `review-config.yaml`:**

```yaml
review_policy:
  merge_gate_threshold: "critical"
  only_new_findings: true
```

**Effect:** Bot will fail the check only if new critical findings are introduced.

### Example 2: Add custom project rule

**Edit `review-config.yaml`:**

```yaml
rule_mappings:
  - id: "PROJECT-NO-STATIC-GLOBAL"
    tool: "clang-tidy"
    check: "cppcoreguidelines-avoid-non-const-global-variables"
    severity: "major"
    standards: ["project-policy"]
    description: "Static global variables violate project architecture"
    remediation: "Use function-static or class-static instead"
```

**Effect:** Bot will flag static global variables as major issues.

### Example 3: Exclude test files

**Edit `review-config.yaml`:**

```yaml
review_policy:
  exclude_paths:
    - "**/*_test.cpp"
    - "test/**"
    - "examples/**"
```

**Effect:** Bot skips analysis of files matching these patterns.

### Example 4: Disable a checker

**Edit `review-config.yaml`:**

```yaml
rule_mappings:
  # Remove this entry to disable the check:
  # - id: "UNWANTED-CHECK"
```

Or use suppressions:

```yaml
suppressions:
  - rule_id: "AUTOSAR-CXX14-CAST-001"
    file: "iceoryx_examples/**"
```

## Troubleshooting

### Issue: Bot doesn't run on PR

**Cause:** Actions not enabled or workflow file missing

**Solution:**
```bash
# Verify workflow exists
ls -la .github/workflows/code-review.yml

# Enable Actions in GitHub settings
# Settings → Actions → General → Allow all actions
```

### Issue: Build fails with "CMake not found"

**Cause:** Project build environment incomplete

**Solution:** The workflow installs CMake. Check logs for specific errors.

```
Setup build environment >
  apt-get install cmake
```

### Issue: No comments on PR

**Cause:** GitHub token permissions insufficient

**Solution:**
1. Regenerate token with full `repo` scope
2. Update repository secret
3. Retry workflow

### Issue: "clang-tidy: command not found"

**Cause:** Version mismatch or installation issue

**Solution:**
```bash
# In the workflow, clang-18 is installed and linked:
ln -sf /usr/bin/clang-tidy-18 /usr/bin/clang-tidy
```

### Issue: Timeout on large PRs

**Cause:** Too many files to analyze

**Solution:** Limit changed files in config or split PR into smaller changes.

## Monitoring & Metrics

### Check Results on GitHub

1. **PR Checks Tab:** Summarizes findings by severity
2. **Inline Comments:** Click to see individual findings
3. **Code Scanning:** Security/quality tab shows SARIF results
4. **Artifacts:** Download reports and detailed JSON

### Local Metrics

```bash
# Count findings by severity
cat results.json | jq '.findings | group_by(.severity) | map({(.[0].severity): length})'

# See which files have most issues
cat results.json | jq '.findings | group_by(.file) | map({file: .[0].file, count: length})'

# List all rules
cat results.json | jq '.findings | map(.rule_id) | unique'
```

## Next Steps for Production

1. **Test on more PRs:** Verify bot behavior across different change types
2. **Collect feedback:** Adjust rules based on developer experience
3. **Add AI enrichment:** Integrate LLM for fix suggestions
4. **Coverity/Axivion:** Import external analysis results
5. **Dashboard:** Track metrics and trends over time
6. **Custom checks:** Add project-specific AST-based rules

## Support & References

- **Issues:** Open an issue in this repository
- **iceoryx docs:** https://github.com/eclipse-iceoryx/iceoryx
- **clang-tidy:** https://clang.llvm.org/extra/clang-tidy/
- **SARIF spec:** https://sarifweb.azurewebsites.net/
- **GitHub Actions:** https://docs.github.com/en/actions
