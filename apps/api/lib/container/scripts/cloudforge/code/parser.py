# apps/api/sandbox-modules/cloudforge/code/parser.py
"""
Code parsing utilities.
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ParsedFunction:
    """Represents a parsed function."""
    name: str
    params: str
    return_type: str
    body: str
    is_async: bool
    is_exported: bool
    start_line: int
    end_line: int


@dataclass
class ParsedImport:
    """Represents a parsed import statement."""
    module: str
    imports: List[str]
    is_type_only: bool
    is_default: bool
    line_number: int


class CodeParser:
    """Utilities for parsing TypeScript/JavaScript code."""
    
    def parse_imports(self, content: str) -> List[ParsedImport]:
        """Parse all import statements from code."""
        imports = []
        
        # Match named imports: import { x, y } from 'module'
        named_pattern = r"import\s+(?:type\s+)?{\s*([^}]+)\s*}\s+from\s+['\"]([^'\"]+)['\"]"
        for match in re.finditer(named_pattern, content):
            imports_str, module = match.groups()
            import_names = [i.strip() for i in imports_str.split(",")]
            imports.append(ParsedImport(
                module=module,
                imports=import_names,
                is_type_only="type" in match.group(0),
                is_default=False,
                line_number=content[:match.start()].count("\n") + 1,
            ))
        
        # Match default imports: import x from 'module'
        default_pattern = r"import\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]"
        for match in re.finditer(default_pattern, content):
            name, module = match.groups()
            if "{" not in match.group(0):  # Not a named import
                imports.append(ParsedImport(
                    module=module,
                    imports=[name],
                    is_type_only=False,
                    is_default=True,
                    line_number=content[:match.start()].count("\n") + 1,
                ))
        
        return imports
    
    def parse_functions(self, content: str) -> List[ParsedFunction]:
        """Parse all function declarations from code."""
        functions = []
        
        # Match function declarations
        # Handles: export async function name(params): type { body }
        pattern = r"(export\s+)?(async\s+)?function\s+(\w+)\s*\(([^)]*)\)\s*(?::\s*([^{]+))?\s*\{"
        
        for match in re.finditer(pattern, content):
            export_kw, async_kw, name, params, return_type = match.groups()
            
            # Find the matching closing brace
            start_pos = match.end() - 1  # Position of opening brace
            body_start = match.end()
            brace_count = 1
            pos = body_start
            
            while pos < len(content) and brace_count > 0:
                if content[pos] == "{":
                    brace_count += 1
                elif content[pos] == "}":
                    brace_count -= 1
                pos += 1
            
            body = content[body_start:pos - 1]
            
            functions.append(ParsedFunction(
                name=name,
                params=params.strip(),
                return_type=(return_type or "void").strip(),
                body=body.strip(),
                is_async=bool(async_kw),
                is_exported=bool(export_kw),
                start_line=content[:match.start()].count("\n") + 1,
                end_line=content[:pos].count("\n") + 1,
            ))
        
        return functions
    
    def extract_json_from_markdown(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from markdown code blocks."""
        import json
        
        # Match ```json ... ``` blocks
        pattern = r"```(?:json)?\s*\n([\s\S]*?)\n```"
        match = re.search(pattern, content)
        
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from markdown")
        
        return None
    
    def extract_code_from_markdown(
        self,
        content: str,
        language: Optional[str] = None,
    ) -> List[str]:
        """Extract code blocks from markdown."""
        if language:
            pattern = rf"```{language}\s*\n([\s\S]*?)\n```"
        else:
            pattern = r"```(?:\w+)?\s*\n([\s\S]*?)\n```"
        
        return [match.group(1) for match in re.finditer(pattern, content)]
