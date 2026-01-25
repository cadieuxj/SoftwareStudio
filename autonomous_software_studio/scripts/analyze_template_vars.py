#!/usr/bin/env python3
"""Template Variable Analyzer Script.

Analyzes persona prompt templates to:
- Extract and document all variables
- Detect inconsistencies
- Generate variable documentation
- Compare template versions

Usage:
    python scripts/analyze_template_vars.py [--detailed] [--json] [--persona PERSONA]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.personas import (
    PERSONA_VARIABLES,
    PromptTemplateManager,
    validate_all_templates,
)


def analyze_template(
    manager: PromptTemplateManager,
    persona: str,
    detailed: bool = False,
) -> dict:
    """Analyze a single template.

    Args:
        manager: The template manager instance.
        persona: Persona name to analyze.
        detailed: Whether to include detailed info.

    Returns:
        Analysis results dictionary.
    """
    metadata = manager.get_template_metadata(persona)
    validation = manager.validate_template(persona)
    content = manager.load_template(persona)

    result = {
        "persona": persona,
        "file": str(metadata.file_path.name),
        "version": metadata.version,
        "content_hash": metadata.content_hash,
        "is_valid": validation.is_valid,
        "errors": validation.errors,
        "warnings": validation.warnings,
        "variables": {
            "expected": [v.name for v in metadata.variables],
            "found": list(manager._extract_placeholders(content)),
            "required": manager.get_required_variables(persona),
        },
        "stats": {
            "lines": len(content.splitlines()),
            "chars": len(content),
            "words": len(content.split()),
        },
    }

    if detailed:
        # Add variable definitions
        result["variable_definitions"] = [
            {
                "name": v.name,
                "description": v.description,
                "required": v.required,
                "default": v.default,
                "example": v.example,
            }
            for v in metadata.variables
        ]

        # Add git history
        history = manager.get_template_history(persona, limit=5)
        result["recent_commits"] = history

        # Add last modified
        if metadata.last_modified:
            result["last_modified"] = metadata.last_modified.isoformat()

    return result


def analyze_all_templates(
    manager: PromptTemplateManager,
    detailed: bool = False,
) -> dict:
    """Analyze all templates.

    Args:
        manager: The template manager instance.
        detailed: Whether to include detailed info.

    Returns:
        Analysis results for all templates.
    """
    results = {
        "summary": {
            "total_templates": len(manager.VALID_PERSONAS),
            "valid_count": 0,
            "invalid_count": 0,
            "total_variables": 0,
        },
        "templates": {},
    }

    for persona in manager.VALID_PERSONAS:
        analysis = analyze_template(manager, persona, detailed)
        results["templates"][persona] = analysis

        if analysis["is_valid"]:
            results["summary"]["valid_count"] += 1
        else:
            results["summary"]["invalid_count"] += 1

        results["summary"]["total_variables"] += len(
            analysis["variables"]["expected"]
        )

    return results


def print_analysis(results: dict, as_json: bool = False) -> None:
    """Print analysis results.

    Args:
        results: Analysis results dictionary.
        as_json: Whether to output as JSON.
    """
    if as_json:
        print(json.dumps(results, indent=2, default=str))
        return

    if "templates" in results:
        # Multiple templates
        print("=" * 60)
        print("TEMPLATE ANALYSIS SUMMARY")
        print("=" * 60)

        summary = results["summary"]
        print(f"\nTotal Templates: {summary['total_templates']}")
        print(f"Valid: {summary['valid_count']}")
        print(f"Invalid: {summary['invalid_count']}")
        print(f"Total Variables: {summary['total_variables']}")

        print("\n" + "-" * 60)

        for persona, analysis in results["templates"].items():
            print_single_analysis(analysis)
            print("-" * 60)
    else:
        # Single template
        print_single_analysis(results)


def print_single_analysis(analysis: dict) -> None:
    """Print analysis for a single template.

    Args:
        analysis: Analysis results for one template.
    """
    status = "VALID" if analysis["is_valid"] else "INVALID"
    status_color = "\033[92m" if analysis["is_valid"] else "\033[91m"
    reset = "\033[0m"

    print(f"\n{analysis['persona'].upper()} Template [{status_color}{status}{reset}]")
    print(f"  File: {analysis['file']}")
    print(f"  Version: {analysis['version']}")
    print(f"  Hash: {analysis['content_hash']}")

    # Stats
    stats = analysis["stats"]
    print(f"  Lines: {stats['lines']}, Words: {stats['words']}, Chars: {stats['chars']}")

    # Variables
    vars_info = analysis["variables"]
    print(f"\n  Expected Variables: {', '.join(vars_info['expected']) or 'None'}")
    print(f"  Found Variables: {', '.join(vars_info['found']) or 'None'}")
    print(f"  Required: {', '.join(vars_info['required']) or 'None'}")

    # Check for mismatches
    expected_set = set(vars_info["expected"])
    found_set = set(vars_info["found"])
    missing = expected_set - found_set
    unexpected = found_set - expected_set

    if missing:
        print(f"  Missing: {', '.join(missing)}")
    if unexpected:
        print(f"  Unexpected: {', '.join(unexpected)}")

    # Errors and warnings
    if analysis["errors"]:
        print(f"\n  Errors:")
        for error in analysis["errors"]:
            print(f"    - {error}")

    if analysis["warnings"]:
        print(f"\n  Warnings:")
        for warning in analysis["warnings"]:
            print(f"    - {warning}")

    # Detailed info
    if "variable_definitions" in analysis:
        print(f"\n  Variable Definitions:")
        for var in analysis["variable_definitions"]:
            req = "required" if var["required"] else "optional"
            print(f"    - {var['name']} ({req}): {var['description']}")
            if var["example"]:
                example = var["example"][:50] + "..." if len(var["example"]) > 50 else var["example"]
                print(f"      Example: {example}")

    if "recent_commits" in analysis and analysis["recent_commits"]:
        print(f"\n  Recent Commits:")
        for commit in analysis["recent_commits"]:
            print(f"    - {commit['short_hash']}: {commit['message'][:50]}")


def check_consistency(manager: PromptTemplateManager) -> list[str]:
    """Check for consistency issues across templates.

    Args:
        manager: The template manager instance.

    Returns:
        List of consistency issues found.
    """
    issues = []

    # Check that all expected variables are actually used
    for persona in manager.VALID_PERSONAS:
        expected = PERSONA_VARIABLES.get(persona, [])
        content = manager.load_template(persona)
        found = manager._extract_placeholders(content)

        for var in expected:
            if var.required and var.name not in found:
                issues.append(
                    f"{persona}: Required variable '{var.name}' not used in template"
                )

    return issues


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Analyze persona prompt templates"
    )
    parser.add_argument(
        "--persona",
        "-p",
        choices=["pm", "arch", "eng", "qa"],
        help="Analyze specific persona (default: all)",
    )
    parser.add_argument(
        "--detailed",
        "-d",
        action="store_true",
        help="Include detailed information",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--check",
        "-c",
        action="store_true",
        help="Check consistency and exit with error if issues found",
    )

    args = parser.parse_args()

    manager = PromptTemplateManager(strict_mode=False)

    if args.check:
        # Consistency check mode
        issues = check_consistency(manager)
        validation_results = validate_all_templates()

        all_valid = True
        for persona, result in validation_results.items():
            if not result.is_valid:
                all_valid = False
                for error in result.errors:
                    print(f"ERROR ({persona}): {error}")

        for issue in issues:
            print(f"ISSUE: {issue}")

        if not all_valid or issues:
            print(f"\nFound {len(issues)} consistency issues")
            return 1
        else:
            print("All templates valid and consistent")
            return 0

    if args.persona:
        results = analyze_template(manager, args.persona, args.detailed)
    else:
        results = analyze_all_templates(manager, args.detailed)

    print_analysis(results, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
