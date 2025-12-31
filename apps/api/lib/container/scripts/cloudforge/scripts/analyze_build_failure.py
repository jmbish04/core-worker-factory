# apps/api/sandbox-modules/scripts/analyze_build_failure.py
#!/usr/bin/env python3
"""
Script to analyze a build failure and suggest fixes.

Usage:
    python analyze_build_failure.py --logs build.log --output analysis.json
"""

import click
import json
import re
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class BuildError:
    """Represents a build error."""
    type: str
    message: str
    file: str = ""
    line: int = 0
    suggestion: str = ""


def analyze_typescript_errors(logs: str) -> List[BuildError]:
    """Analyze TypeScript compilation errors."""
    errors = []
    
    # Pattern: src/file.ts(10,5): error TS2304: Cannot find name 'x'.
    pattern = r"([^\s]+\.tsx?)\((\d+),(\d+)\):\s+error\s+(TS\d+):\s+(.+)"
    
    for match in re.finditer(pattern, logs):
        file, line, col, code, message = match.groups()
        errors.append(BuildError(
            type=f"typescript:{code}",
            message=message,
            file=file,
            line=int(line),
            suggestion=get_typescript_suggestion(code, message),
        ))
    
    return errors


def analyze_npm_errors(logs: str) -> List[BuildError]:
    """Analyze npm/pnpm errors."""
    errors = []
    
    # Module not found
    pattern = r"Cannot find module ['\"]([^'\"]+)['\"]"
    for match in re.finditer(pattern, logs):
        module = match.group(1)
        errors.append(BuildError(
            type="npm:module_not_found",
            message=f"Cannot find module '{module}'",
            suggestion=f"Run: pnpm add {module}",
        ))
    
    return errors


def get_typescript_suggestion(code: str, message: str) -> str:
    """Get a suggestion for a TypeScript error."""
    suggestions = {
        "TS2304": "Import the missing type/value or declare it",
        "TS2307": "Check the import path or install the missing package",
        "TS2322": "Fix the type mismatch or add a type assertion",
        "TS2345": "Ensure argument types match parameter types",
        "TS7006": "Add explicit type annotation to the parameter",
    }
    return suggestions.get(code, "Check the TypeScript documentation for this error")


@click.command()
@click.option("--logs", required=True, type=click.Path(exists=True), help="Build log file")
@click.option("--output", default="analysis.json", help="Output file")
def main(logs: str, output: str):
    """Analyze build failure logs and suggest fixes."""
    with open(logs) as f:
        log_content = f.read()
    
    errors = []
    errors.extend(analyze_typescript_errors(log_content))
    errors.extend(analyze_npm_errors(log_content))
    
    analysis = {
        "total_errors": len(errors),
        "errors": [
            {
                "type": e.type,
                "message": e.message,
                "file": e.file,
                "line": e.line,
                "suggestion": e.suggestion,
            }
            for e in errors
        ],
    }
    
    with open(output, "w") as f:
        json.dump(analysis, f, indent=2)
    
    click.echo(f"Found {len(errors)} errors")
    click.echo(f"Analysis written to: {output}")
    
    for error in errors[:5]:  # Show first 5
        click.echo(f"  - [{error.type}] {error.message}")
        if error.suggestion:
            click.echo(f"    Suggestion: {error.suggestion}")


if __name__ == "__main__":
    main()
