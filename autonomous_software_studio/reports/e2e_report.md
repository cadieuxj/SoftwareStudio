# End-to-End Test Report

## Overview
This report captures end-to-end (E2E) pipeline test results for the multi-agent
orchestration workflow. It is intended to be updated by running the E2E suite.

## Latest Run
- Status: Not yet generated
- Command: `pytest tests/e2e/ -v -s --tb=short`

## Scenarios Covered
- Happy path (PM → Architect → Engineer → QA → Success)
- Human rejection at architect phase
- QA failure with repair loop
- Max iteration limit reached
- Checkpoint resume after interrupt

## Notes
Run the HTML report command to generate a rich report:

```bash
pytest tests/e2e/ --html=reports/e2e_report.html
```
