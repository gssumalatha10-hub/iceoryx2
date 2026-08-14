# Eclipse iceoryx Code Review Agent

A comprehensive C++ code review bot for Eclipse iceoryx that automates static analysis and standards compliance checking based on MISRA, AUTOSAR, and project-specific policies.

## Features

- ✅ **Automated Analysis**: Runs clang-tidy, Clang Static Analyzer, and compiler diagnostics
- ✅ **Standards Mapping**: Maps findings to MISRA C++ and AUTOSAR C++14 guidelines
- ✅ **Project Policy Enforcement**: Enforces Eclipse iceoryx-specific coding standards
- ✅ **PR Integration**: Posts inline comments and check runs on GitHub pull requests
- ✅ **SARIF Export**: Generates SARIF reports for Code Scanning integration
- ✅ **Deduplication**: Removes duplicate findings from multiple tools
- ✅ **Baseline Filtering**: Reports only new findings, not pre-existing issues

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           GitHub Pull Request (iceoryx)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│         code-review-bot/.github/workflows/code-review.yml   │
│  (GitHub Actions: Setup environment, run analysis)          │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
    ┌────────┐   ┌──────────┐   ┌─────────┐
    │ Clang  │   │clang-tidy│   │  Clang  │
    │Compiler│   │          │   │Analyzer │
    └───┬────┘   └────┬─────┘   └────┬────┘
        │             │              │
        └─────────────┼──────────────┘
                      │
                      ▼
      ┌──────────────────────────────┐
      │ review_orchestrator.py       │
      │ - Normalize findings         │
      │ - Filter duplicates          │
      │ - Map to standards           │
      │ - Generate SARIF             │
      └──────────┬───────────────────┘
                 │
        ┌────────┴───────────┐
        ▼                    ▼
  ┌─────────────┐     ┌──────────────┐
  │SARIF Report │     │JSON Summary  │
  └─────────────┘     └──────┬───────┘
                             │
                             ▼
                   ┌──────────────────────┐
                   │ github_reporter.py   │
                   │ - Post check run     │
                   │ - Post PR comments   │
                   │ - Upload SARIF       │
                   └──────────────────────┘
                             │
                             ▼
                   ┌──────────────────────┐
                   │  GitHub PR Timeline  │
                   │  - Check results     │
                   │  - Inline comments   │
                   │  - Code Scanning     │
                   └──────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8+
- CMake 3.16+
- Clang/LLVM 18+
- Git
- GitHub token (for PR posting)

### Installation

1. **Clone the review agent:**
   ```bash
   cd /path/to/your/workspace
   git clone <this-repo> code-review-agent
   cd code-review-agent
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup in your fork of iceoryx:**
   ```bash
   # Copy .github/workflows to your iceoryx fork
   cp -r code-review-bot/.github/workflows <your-iceoryx-fork>/
   
   # Copy review bot source and config to .github/
   cp -r code-review-bot/src <your-iceoryx-fork>/.github/review-bot/
   cp code-review-bot/review-config.yaml <your-iceoryx-fork>/.github/review-bot/
   ```

## Usage

### Local Testing

Run the review analysis on a local checkout:

```bash
python3 src/review_orchestrator.py \
  --repo /path/to/iceoryx \
  --config review-config.yaml \
  --pr-base main \
  --pr-head your-branch \
  --output review-results.json
```

### GitHub Actions

The bot automatically runs on every PR when the workflow is installed. It will:

1. Checkout iceoryx
2. Set up build environment (clang-18, cmake, etc.)
3. Build with compile_commands.json
4. Run all configured analyzers
5. Post check run with results
6. Add inline comments for high-severity findings
7. Upload SARIF to Code Scanning

### View Results

- **Check Run**: See summary on PR checks tab
- **Inline Comments**: Review each finding on the "Files changed" tab
- **Detailed Report**: Download from run artifacts
- **SARIF**: Integrated with GitHub Code Scanning

## Configuration

Edit `review-config.yaml` to customize:

- **Enabled analyzers**: Enable/disable clang-tidy, clang-analyzer, compiler warnings
- **Rule mappings**: Map tool checks to MISRA/AUTOSAR/project rules
- **Severity levels**: Define criticality and merge-gate behavior
- **Exclusions**: Skip analysis of certain files or check types

### Example: Enforce critical findings only

```yaml
review_policy:
  merge_gate_threshold: "critical"  # Fail on new critical findings
  only_new_findings: true           # Report only new issues
```

### Example: Add custom project rule

```yaml
rule_mappings:
  - id: "PROJECT-API-001"
    tool: "clang-tidy"
    check: "cppcoreguidelines-avoid-* "
    severity: "major"
    standards: ["project-policy"]
    description: "Unsafe API usage"
    remediation: "Use approved wrapper"
```

## Components

### `src/review_orchestrator.py`

**Main orchestrator:** Manages the analysis pipeline.

- **Input**: Git repository, config file, PR base/head branches
- **Process**:
  1. Identify changed files in PR
  2. Build project with compile_commands.json
  3. Run configured analyzers
  4. Normalize findings to SARIF
  5. Filter new findings only
  6. Deduplicate across tools
  7. Map to standards
- **Output**: JSON results, SARIF report, summary statistics

### `src/github_reporter.py`

**GitHub integration:** Posts findings as PR comments and checks.

- **Input**: Review results JSON file
- **Operations**:
  - Post check run with summary
  - Add inline comments on changed lines
  - Generate markdown report
  - Upload SARIF to Code Scanning
- **Output**: GitHub PR comments, checks, and artifacts

### `review-config.yaml`

**Configuration file:** Defines policies, rule mappings, and severity handling.

- Specifies enabled analyzers and versions
- Maps tool checks to standards (MISRA/AUTOSAR/project)
- Controls merge-gate behavior
- Defines suppressions and deviations

### `.github/workflows/code-review.yml`

**GitHub Actions workflow:** Orchestrates bot execution on every PR.

- Sets up build environment
- Clones iceoryx and review-bot
- Runs analysis orchestrator
- Posts results to GitHub
- Uploads SARIF

## Severity Levels

| Level | Priority | Merge Gate | Inline Comments |
|-------|----------|-----------|-----------------|
| **Critical** | 1 | ❌ Fail | ✅ Yes |
| **Major** | 2 | ⚠️ Warn | ✅ Yes |
| **Minor** | 3 | ℹ️ Info | ❌ Summary only |
| **Info** | 4 | ℹ️ Info | ❌ Summary only |

## Standards Support

### MISRA C++ (via internal approved mapping)

- No approved rule text stored (proprietary)
- Uses Eclipse iceoryx-approved rule ID mappings
- Organizations can customize mappings in `review-config.yaml`

### AUTOSAR C++14

- Mapped from clang-tidy checks and static analyzer findings
- Example: AUTOSAR-CXX14-CAST-001 → bugprone-narrowing-conversions

### Project-Specific Policies

- No heap allocation after initialization
- No exceptions
- No raw `new`/`delete`; use approved containers
- Compile with C++17 and strict warnings
- All return values must be checked

## Customization Guide

### Add a New Rule

1. Edit `review-config.yaml` and add to `rule_mappings`:

```yaml
- id: "CUSTOM-RULE-001"
  tool: "clang-tidy"
  check: "custom-check-name"
  severity: "major"
  standards: ["project-policy"]
  description: "Find problematic pattern X"
  remediation: "Replace with approach Y"
```

2. The bot will automatically detect and report violations.

### Add a New Analyzer

1. Extend `review_orchestrator.py`:

```python
def _run_my_analyzer(self):
    # Run analyzer
    # Parse results
    # Convert to Finding objects
    self.findings.extend(...)
```

2. Enable in `review-config.yaml`:

```yaml
analyzers:
  my_analyzer:
    enabled: true
```

### Suppress False Positives

Add to `review-config.yaml`:

```yaml
suppressions:
  - pattern: "*.proto.h"  # Auto-generated files
  - rule_id: "SOME-CHECK"
    file: "iceoryx_examples/**"
```

## Development

### Running Tests Locally

```bash
# Test the orchestrator on a local checkout
python3 src/review_orchestrator.py \
  --repo ~/iceoryx \
  --config review-config.yaml \
  --output my-results.json

# Generate report
python3 src/github_reporter.py \
  --results my-results.json \
  --generate-report \
  --output my-report.md
```

### Debugging

Set verbose logging in Python:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check GitHub Actions logs in your fork's Actions tab.

## Known Limitations

1. **Compile commands**: Requires project to support CMake with `CMAKE_EXPORT_COMPILE_COMMANDS`
2. **Clang version**: Analysis quality depends on clang-18+
3. **C++ standard**: Best results with C++17 or later
4. **Platform**: Currently optimized for Linux; macOS/Windows may need adjustments
5. **Large PRs**: May timeout on PRs touching 100+ files (can be tuned via config)

## Future Enhancements

- [ ] AI-powered explanation and fix suggestions (LLM integration)
- [ ] Coverity integration for deeper analysis
- [ ] Axivion Suite import of findings
- [ ] Custom AST-based checks for project-specific rules
- [ ] Machine learning for false-positive filtering
- [ ] Metrics dashboard and trend analysis
- [ ] Suppression management UI in GitHub
- [ ] Multi-branch analysis (base, head, trunk)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Test locally
5. Submit a PR

## License

This code review agent is released under the Apache License 2.0, matching Eclipse iceoryx.

## Support

- **Issues**: Open issues in this repository
- **Discussions**: Check existing issues for FAQ
- **Eclipse iceoryx**: https://github.com/eclipse-iceoryx/iceoryx

## References

- [Eclipse iceoryx](https://github.com/eclipse-iceoryx/iceoryx)
- [AUTOSAR C++14 Guidelines](https://www.autosar.org/)
- [clang-tidy checks](https://clang.llvm.org/extra/clang-tidy/checks/)
- [SARIF Specification](https://sarifweb.azurewebsites.net/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
