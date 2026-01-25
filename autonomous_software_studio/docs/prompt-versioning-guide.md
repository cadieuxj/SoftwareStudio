# Prompt Versioning Guide

This guide covers version control, A/B testing, and changelog management for persona prompt templates.

## Overview

The Autonomous Software Studio uses versioned prompt templates for each agent persona:
- **PM (Product Manager)** - `pm_prompt.md`
- **Architect** - `architect_prompt.md`
- **Engineer** - `engineer_prompt.md`
- **QA** - `qa_prompt.md`

Each template uses `{variable}` placeholders for dynamic content injection.

## Version Control

### Git-Based Versioning

Templates are version-controlled through Git. The `PromptTemplateManager` provides utilities to track versions:

```python
from src.personas import PromptTemplateManager

manager = PromptTemplateManager()

# Get template metadata including version
metadata = manager.get_template_metadata("pm")
print(f"Version: {metadata.version}")
print(f"Content hash: {metadata.content_hash}")

# Get git history
history = manager.get_template_history("pm", limit=10)
for commit in history:
    print(f"{commit['short_hash']} - {commit['message']}")
```

### Version Identifiers

Versions are identified by:
1. **Git commit hash** (preferred) - Short hash of the last commit that modified the template
2. **Content hash** (fallback) - SHA256 hash of template content when not in a git repository

## Making Changes to Templates

### 1. Pre-Change Validation

Before modifying a template, validate its current state:

```bash
# CLI validation
python -m src.personas.template_manager --validate pm

# Or validate all templates
python -m src.personas.template_manager --validate-all
```

### 2. Edit the Template

Make your changes to the `.md` file. Ensure you:
- Keep all required variables (see Variable Documentation below)
- Maintain proper Markdown formatting
- Close all code blocks properly

### 3. Post-Change Validation

```python
from src.personas import validate_all_templates

results = validate_all_templates()
for persona, result in results.items():
    print(f"{persona}: {'PASS' if result.is_valid else 'FAIL'}")
    if result.errors:
        print(f"  Errors: {result.errors}")
    if result.warnings:
        print(f"  Warnings: {result.warnings}")
```

### 4. Commit with Meaningful Message

```bash
git add src/personas/pm_prompt.md
git commit -m "prompt(pm): Improve clarity of user story guidance

- Added examples of good user stories
- Clarified acceptance criteria format
- Added edge case handling instructions"
```

### Commit Message Convention

Use the prefix `prompt(persona):` for prompt changes:
- `prompt(pm): Update mission analysis instructions`
- `prompt(arch): Add security considerations section`
- `prompt(eng): Clarify batch scope handling`
- `prompt(qa): Add test coverage requirements`

## Variable Documentation

### Required Variables by Persona

| Persona | Variable | Description |
|---------|----------|-------------|
| PM | `{user_mission}` | The user's project request |
| Architect | `{prd_content}` | Product Requirements Document |
| Engineer | `{tech_spec_content}` | Technical Specification |
| Engineer | `{rules_of_engagement}` | Coding standards from tech spec |
| Engineer | `{batch_name}` | Current implementation batch name |
| Engineer | `{batch_scope}` | Files/features in the batch |
| QA | `{acceptance_criteria}` | Acceptance criteria from PRD |

### Viewing Variable Documentation

```bash
python -m src.personas.template_manager --vars pm
```

Or programmatically:

```python
manager = PromptTemplateManager()
doc = manager.get_variable_documentation("pm")
print(doc)
```

## A/B Testing Prompts

### Setting Up A/B Tests

1. **Create variant templates**:
   ```
   src/personas/
   ├── pm_prompt.md           # Control (A)
   ├── pm_prompt_v2.md        # Variant (B)
   └── pm_prompt_v3.md        # Variant (C)
   ```

2. **Load variants programmatically**:
   ```python
   import random
   from pathlib import Path

   # Select variant
   variants = ["pm_prompt.md", "pm_prompt_v2.md", "pm_prompt_v3.md"]
   selected = random.choice(variants)

   # Load the variant
   from src.personas import PERSONAS_DIR
   content = (PERSONAS_DIR / selected).read_text()
   ```

3. **Track which variant was used** in session logs:
   ```python
   session_data = {
       "prompt_variant": selected,
       "prompt_hash": hashlib.sha256(content.encode()).hexdigest()[:12],
       # ... other session data
   }
   ```

### Measuring Results

Track metrics like:
- Task completion rate
- Output quality scores
- Number of iterations needed
- Token usage efficiency

## Changelog Management

### Maintaining a Changelog

Create `docs/PROMPT_CHANGELOG.md`:

```markdown
# Prompt Changelog

## [2024-01-15] - PM Prompt v2.3

### Changed
- Improved user story format guidance
- Added more examples of acceptance criteria

### Fixed
- Clarified ambiguous instructions in section 3

## [2024-01-10] - Architect Prompt v1.5

### Added
- New section on security architecture
- Performance requirements checklist

### Removed
- Deprecated technology references
```

### Automated Change Detection

```python
from src.personas import PromptTemplateManager

manager = PromptTemplateManager()

# Check if template has changed since a known version
current = manager.get_template_metadata("pm")
if current.content_hash != "expected_hash":
    print("Template has been modified!")
```

## Best Practices

1. **Test before commit**: Always validate templates before committing
2. **Document changes**: Update changelog for significant modifications
3. **Review in PRs**: Prompt changes should go through code review
4. **Gradual rollout**: Use A/B testing for major changes
5. **Monitor impact**: Track metrics after deploying prompt changes
6. **Keep history**: Don't delete old variants until confident in new ones

## CLI Reference

```bash
# Validate single template
python -m src.personas.template_manager --validate pm

# Validate all templates
python -m src.personas.template_manager --validate-all

# List all templates with metadata
python -m src.personas.template_manager --list

# Show git history for a template
python -m src.personas.template_manager --history pm

# Show variable documentation
python -m src.personas.template_manager --vars pm
```

## Programmatic API

```python
from src.personas import (
    PromptTemplateManager,
    validate_all_templates,
    PERSONA_VARIABLES,
)

# Create manager
manager = PromptTemplateManager(strict_mode=True)

# Load raw template
content = manager.load_template("pm")

# Render with variables
rendered = manager.render_template("pm", {"user_mission": "Build an app"})

# Validate template
result = manager.validate_template("pm", {"user_mission": "Build an app"})
print(f"Valid: {result.is_valid}")

# Get metadata
metadata = manager.get_template_metadata("pm")
print(f"Version: {metadata.version}")
print(f"Variables: {[v.name for v in metadata.variables]}")

# Get git history
history = manager.get_template_history("pm")

# Get required variables
required = manager.get_required_variables("pm")
print(f"Required: {required}")
```
