"""
VortexRAG — AST-Based Code Chunker (Phase 2)

Uses tree-sitter to parse source code into semantically meaningful chunks
(functions, classes, methods) instead of arbitrary character splits.

WHY: Standard chunking destroys code context. A function split across two chunks
     loses its signature + body relationship. AST chunking preserves semantics.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import hashlib
import logging

logger = logging.getLogger("vortex")

# Supported language → file extensions mapping
LANGUAGE_EXTENSIONS: dict[str, list[str]] = {
    "python":     [".py"],
    "javascript": [".js", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx"],
    "java":       [".java"],
    "go":         [".go"],
}

# tree-sitter grammar package names
LANGUAGE_PACKAGES: dict[str, str] = {
    "python":     "tree_sitter_python",
    "javascript": "tree_sitter_javascript",
    "typescript": "tree_sitter_typescript",
    "java":       "tree_sitter_java",
    "go":         "tree_sitter_go",
}

# Node types to extract per language
CHUNK_NODE_TYPES: dict[str, list[str]] = {
    "python": [
        "function_definition",
        "async_function_definition",
        "class_definition",
    ],
    "javascript": [
        "function_declaration",
        "arrow_function",
        "method_definition",
        "class_declaration",
    ],
    "typescript": [
        "function_declaration",
        "method_definition",
        "class_declaration",
        "interface_declaration",
        "type_alias_declaration",
    ],
    "java": [
        "method_declaration",
        "class_declaration",
        "interface_declaration",
    ],
    "go": [
        "function_declaration",
        "method_declaration",
        "type_declaration",
    ],
}


@dataclass
class CodeChunk:
    """A single semantically-meaningful chunk of code."""
    id: str                          # SHA256 hash of (repo_id + file_path + start_line)
    repo_id: str                     # Identifier for the repository
    file_path: str                   # Relative path within repo
    language: str                    # Programming language
    node_type: str                   # AST node type (function_definition, class_definition, etc.)
    name: str                        # Function/class name
    code: str                        # Raw source code of the chunk
    start_line: int                  # 1-indexed start line in file
    end_line: int                    # 1-indexed end line in file
    docstring: Optional[str] = None  # Extracted docstring if present
    parent_class: Optional[str] = None  # For methods: name of containing class
    calls: list[str] = field(default_factory=list)   # Functions this chunk calls
    imports: list[str] = field(default_factory=list) # Import statements in scope

    @property
    def display_path(self) -> str:
        return f"{self.file_path}:{self.start_line}-{self.end_line}"

    def to_embed_text(self) -> str:
        """Formats chunk for embedding — combines context + code."""
        parts = [
            f"# File: {self.file_path}",
            f"# Type: {self.node_type} | Language: {self.language}",
        ]
        if self.parent_class:
            parts.append(f"# Class: {self.parent_class}")
        if self.docstring:
            parts.append(f'"""{self.docstring}"""')
        parts.append(self.code)
        return "\n".join(parts)


class ASTChunker:
    """
    Parses source files using tree-sitter and extracts semantic code chunks.

    Usage:
        chunker = ASTChunker()
        chunks = chunker.chunk_file(Path("app/main.py"), repo_id="my-repo")
    """

    def __init__(self):
        self._parsers: dict[str, object] = {}
        self._languages: dict[str, object] = {}
        self._init_parsers()

    def _init_parsers(self) -> None:
        """Lazily initialize tree-sitter parsers for all supported languages."""
        try:
            import tree_sitter_python as tspython
            import tree_sitter_javascript as tsjavascript
            import tree_sitter_typescript as tstypescript
            import tree_sitter_java as tsjava
            import tree_sitter_go as tsgo
            from tree_sitter import Language, Parser

            lang_modules = {
                "python":     tspython.language(),
                "javascript": tsjavascript.language(),
                "typescript": tstypescript.language_typescript(),
                "java":       tsjava.language(),
                "go":         tsgo.language(),
            }

            for lang_name, lang_obj in lang_modules.items():
                language = Language(lang_obj)
                parser = Parser(language)
                self._languages[lang_name] = language
                self._parsers[lang_name] = parser

            logger.info(f"✅ ASTChunker initialized for: {list(self._parsers.keys())}")

        except ImportError as e:
            logger.warning(f"⚠️  tree-sitter import failed: {e}. Install requirements.")
            raise

    def detect_language(self, file_path: Path) -> Optional[str]:
        """Detect programming language from file extension."""
        suffix = file_path.suffix.lower()
        for lang, exts in LANGUAGE_EXTENSIONS.items():
            if suffix in exts:
                return lang
        return None

    def chunk_file(
        self,
        file_path: Path,
        repo_id: str,
        repo_root: Optional[Path] = None,
    ) -> list[CodeChunk]:
        """
        Parse a single file and return all semantic chunks.

        Args:
            file_path: Absolute path to the source file.
            repo_id: Identifier for the parent repository.
            repo_root: Root of the repository (for relative path calculation).

        Returns:
            List of CodeChunk objects.
        """
        language = self.detect_language(file_path)
        if language is None or language not in self._parsers:
            return []

        try:
            source = file_path.read_bytes()
        except (OSError, PermissionError) as e:
            logger.warning(f"Cannot read {file_path}: {e}")
            return []

        if len(source) == 0 or len(source) > 500_000:  # Skip empty or huge files
            return []

        parser = self._parsers[language]
        tree = parser.parse(source)
        source_str = source.decode("utf-8", errors="replace")

        rel_path = str(file_path.relative_to(repo_root)) if repo_root else str(file_path)
        target_node_types = CHUNK_NODE_TYPES.get(language, [])

        chunks: list[CodeChunk] = []
        self._extract_chunks(
            node=tree.root_node,
            source=source_str,
            language=language,
            file_path=rel_path,
            repo_id=repo_id,
            target_types=target_node_types,
            chunks=chunks,
            parent_class=None,
        )

        return chunks

    def chunk_repository(
        self,
        repo_root: Path,
        repo_id: str,
        languages: Optional[list[str]] = None,
        exclude_dirs: Optional[set[str]] = None,
    ) -> list[CodeChunk]:
        """
        Walk an entire repository and chunk all supported source files.

        Args:
            repo_root: Root directory of the cloned repository.
            repo_id: Unique identifier for this repo.
            languages: Limit to specific languages. None = all supported.
            exclude_dirs: Directory names to skip (e.g. node_modules, .git).

        Returns:
            All extracted CodeChunks across the repo.
        """
        if exclude_dirs is None:
            exclude_dirs = {
                ".git", "node_modules", "__pycache__", ".venv", "venv",
                "dist", "build", ".next", "vendor", "target",
            }

        all_chunks: list[CodeChunk] = []
        target_langs = set(languages) if languages else set(LANGUAGE_EXTENSIONS.keys())
        file_count = 0

        for file_path in repo_root.rglob("*"):
            # Skip excluded directories
            if any(excl in file_path.parts for excl in exclude_dirs):
                continue
            if not file_path.is_file():
                continue

            lang = self.detect_language(file_path)
            if lang not in target_langs:
                continue

            chunks = self.chunk_file(file_path, repo_id=repo_id, repo_root=repo_root)
            all_chunks.extend(chunks)
            file_count += 1

        logger.info(
            f"📦 Chunked repo '{repo_id}': {file_count} files → {len(all_chunks)} chunks"
        )
        return all_chunks

    def _extract_chunks(
        self,
        node,
        source: str,
        language: str,
        file_path: str,
        repo_id: str,
        target_types: list[str],
        chunks: list[CodeChunk],
        parent_class: Optional[str],
    ) -> None:
        """Recursively walk the AST and extract target nodes."""
        if node.type in target_types:
            chunk = self._node_to_chunk(
                node=node,
                source=source,
                language=language,
                file_path=file_path,
                repo_id=repo_id,
                parent_class=parent_class,
            )
            if chunk:
                chunks.append(chunk)

            # If this is a class, set parent_class for children
            if "class" in node.type:
                class_name = self._get_node_name(node, source)
                for child in node.children:
                    self._extract_chunks(
                        child, source, language, file_path, repo_id,
                        target_types, chunks, class_name,
                    )
                return

        for child in node.children:
            self._extract_chunks(
                child, source, language, file_path, repo_id,
                target_types, chunks, parent_class,
            )

    def _node_to_chunk(
        self,
        node,
        source: str,
        language: str,
        file_path: str,
        repo_id: str,
        parent_class: Optional[str],
    ) -> Optional[CodeChunk]:
        """Convert a tree-sitter node into a CodeChunk."""
        start_line = node.start_point[0] + 1  # 1-indexed
        end_line   = node.end_point[0]   + 1

        # Skip tiny nodes (likely not meaningful)
        if end_line - start_line < 2:
            return None

        code = source[node.start_byte:node.end_byte]
        name = self._get_node_name(node, source) or f"anonymous_{start_line}"
        docstring = self._extract_docstring(node, source, language)

        # Build a stable, deterministic chunk ID
        chunk_id = hashlib.sha256(
            f"{repo_id}:{file_path}:{start_line}:{name}".encode()
        ).hexdigest()[:16]

        return CodeChunk(
            id=chunk_id,
            repo_id=repo_id,
            file_path=file_path,
            language=language,
            node_type=node.type,
            name=name,
            code=code,
            start_line=start_line,
            end_line=end_line,
            docstring=docstring,
            parent_class=parent_class,
        )

    def _get_node_name(self, node, source: str) -> Optional[str]:
        """Extract the identifier/name from a function or class node."""
        for child in node.children:
            if child.type == "identifier":
                return source[child.start_byte:child.end_byte]
            if child.type == "name":
                return source[child.start_byte:child.end_byte]
        return None

    def _extract_docstring(self, node, source: str, language: str) -> Optional[str]:
        """Extract docstring from a function or class node if present."""
        if language not in ("python",):
            return None  # Python has standard docstrings; others handled later

        body_nodes = [c for c in node.children if c.type == "block"]
        if not body_nodes:
            return None

        body = body_nodes[0]
        for stmt in body.children:
            if stmt.type == "expression_statement":
                for child in stmt.children:
                    if child.type == "string":
                        raw = source[child.start_byte:child.end_byte]
                        # Strip quotes
                        return raw.strip('"""').strip("'''").strip('"').strip("'").strip()
        return None
