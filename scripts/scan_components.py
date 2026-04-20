#!/usr/bin/env python3
"""
scan_components.py
Scans Next.js frontend TSX files and outputs an ASCII component hierarchy
with layout-relevant Tailwind classes. Appends result to UI-REVIEW.md.

Usage:
    python scripts/scan_components.py
    python scripts/scan_components.py --print-only   # skip UI-REVIEW.md update
"""

import re
import sys
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
REVIEW_FILE = ROOT / "UI-REVIEW.md"
MAX_DEPTH = 3  # max component nesting levels to follow

# ─── Patterns ────────────────────────────────────────────────────────────────

# Layout-relevant Tailwind classes only (skip color, font, etc.)
LAYOUT_RE = re.compile(
    r'(?<![a-zA-Z:-])('
    r'flex(?:-(?:col|row|wrap|nowrap|1|auto|none))?'
    r'|grid(?:-cols-\w+)?'
    r'|inline-flex|inline-block|block|hidden'
    r'|absolute|relative|fixed|sticky'
    r'|(?:w|h|min-h|max-h|max-w|min-w)-[\w\[\]\.%/:+()-]+'
    r'|(?:mt|mb|ml|mr|mx|my|pt|pb|pl|pr|px|py)-[\w\[\]\.+-]+'
    r'|gap(?:-[xy])?-[\w\[\]\.+-]+'
    r'|z-\d+'
    r'|(?:top|bottom|left|right)-[\w\[\]\.+-]+'
    r'|justify-\w+|items-\w+'
    r'|overflow(?:-[xy])?-\w+'
    r'|grow|shrink|basis-\w+'
    r')(?![a-zA-Z:-])'
)

# import { Foo, Bar } from './x'  OR  import Foo from './x'
IMPORT_RE = re.compile(
    r'import\s+(?:\{([^}]+)\}|([A-Z]\w*))\s+from\s+[\'"]([^\'"]+)[\'"]'
)

# JSX component usage: <ComponentName
COMP_USE_RE = re.compile(r'<([A-Z][A-Za-z0-9_]*)\b')

# className extraction (covers string literals and template literals)
CN_RE = re.compile(
    r'className=(?:"([^"]+)"|\'([^\']+)\'|\{`([^`]*)`\}|\{["\']([^"\']+)["\']\})'
)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def layout_classes(classname: str) -> list[str]:
    """Return layout-relevant classes from a className string, capped at 6."""
    seen, result = set(), []
    for m in LAYOUT_RE.finditer(classname):
        cls = m.group(1)
        if cls not in seen:
            seen.add(cls)
            result.append(cls)
        if len(result) == 6:
            break
    return result


def resolve(from_file: Path, import_path: str) -> Path | None:
    """Resolve a @/ or relative import to an absolute Path."""
    if import_path.startswith("@/"):
        base = FRONTEND / import_path[2:]
    elif import_path.startswith("."):
        base = from_file.parent / import_path
    else:
        return None
    for ext in ("", ".tsx", ".ts", "/index.tsx", "/index.ts"):
        p = Path(str(base) + ext)
        if p.exists() and p.is_file():
            return p
    return None


def parse_imports(content: str, from_file: Path) -> dict[str, Path]:
    """Map component name → resolved file for all local imports."""
    result: dict[str, Path] = {}
    for m in IMPORT_RE.finditer(content):
        named_str = m.group(1) or ""
        default_name = m.group(2) or ""
        import_path = m.group(3)

        names: list[str] = []
        if named_str:
            for part in named_str.split(","):
                part = part.strip()
                if " as " in part:
                    part = part.split(" as ")[-1].strip()
                if part and part[0].isupper():
                    names.append(part)
        if default_name and default_name[0].isupper():
            names.append(default_name)

        resolved = resolve(from_file, import_path)
        if resolved:
            for name in names:
                result[name] = resolved
    return result


def used_components(content: str) -> set[str]:
    return set(COMP_USE_RE.findall(content))


def extract_classnames_per_component(content: str) -> dict[str, list[str]]:
    """
    Best-effort: for each component tag, look at the surrounding 3 lines
    for a className and extract layout classes.
    """
    lines = content.splitlines()
    result: dict[str, list[str]] = {}
    for i, line in enumerate(lines):
        for m in COMP_USE_RE.finditer(line):
            comp = m.group(1)
            if comp in result:
                continue
            # Scan this line + next 2 lines for className
            window = "\n".join(lines[i : i + 3])
            for cn_m in CN_RE.finditer(window):
                val = next((g for g in cn_m.groups() if g), "")
                classes = layout_classes(val)
                if classes:
                    result[comp] = classes
                    break
    return result

# ─── Tree rendering ───────────────────────────────────────────────────────────

def render_tree(
    file_path: Path,
    registry: dict[str, Path],
    depth: int,
    visited: set[Path],
    prefix: str,
) -> list[str]:
    """Recursively render child components of file_path as ASCII tree lines."""
    if depth >= MAX_DEPTH:
        return []

    content = read(file_path)
    imports = parse_imports(content, file_path)
    used = used_components(content)
    classmap = extract_classnames_per_component(content)

    # Only components that are both imported locally AND used in JSX
    children = [(n, p) for n, p in imports.items() if n in used]

    lines: list[str] = []
    for idx, (name, path) in enumerate(children):
        is_last = idx == len(children) - 1
        connector = "└── " if is_last else "├── "
        child_prefix = prefix + ("    " if is_last else "│   ")

        classes = classmap.get(name, [])
        cls_str = f" ({' '.join(classes)})" if classes else ""
        file_str = f" - {rel(path)}"
        recursive_mark = " ↺" if path in visited else ""

        lines.append(f"{prefix}{connector}[{name}]{file_str}{cls_str}{recursive_mark}")

        if path not in visited:
            lines.extend(
                render_tree(path, registry, depth + 1, visited | {file_path}, child_prefix)
            )

    return lines

# ─── Page discovery ───────────────────────────────────────────────────────────

def find_pages() -> list[tuple[str, Path]]:
    """Return (route, page.tsx path) for every Next.js page."""
    pages: list[tuple[str, Path]] = []
    for p in sorted(FRONTEND.rglob("page.tsx")):
        if any(part in p.parts for part in ("node_modules", ".next")):
            continue
        rel_parts = p.relative_to(FRONTEND / "app").parts[:-1]  # drop page.tsx
        # Strip Next.js route groups like (auth), (protected)
        route_parts = [s for s in rel_parts if not (s.startswith("(") and s.endswith(")"))]
        route = "/" + "/".join(route_parts) if route_parts else "/"
        pages.append((route, p))
    return pages

# ─── Tree generation ──────────────────────────────────────────────────────────

def build_registry() -> dict[str, Path]:
    """Map PascalCase stem → file path for quick lookup (not used in traversal)."""
    registry: dict[str, Path] = {}
    for tsx in FRONTEND.rglob("*.tsx"):
        if any(part in tsx.parts for part in ("node_modules", ".next")):
            continue
        if tsx.stem[0:1].isupper():
            registry[tsx.stem] = tsx
    return registry


def generate() -> str:
    registry = build_registry()
    pages = find_pages()

    tsx_count = sum(
        1 for p in FRONTEND.rglob("*.tsx")
        if not any(x in p.parts for x in ("node_modules", ".next"))
    )

    lines: list[str] = []
    lines += [
        "## Component Hierarchy Map",
        "",
        f"> Generated: {date.today()}  ",
        f"> Scanned {tsx_count} TSX files across {len(pages)} routes.  ",
        f"> Layout classes shown: flex · grid · position · sizing · spacing · z-index",
        "",
    ]

    for route, page_file in pages:
        content = read(page_file)
        imports = parse_imports(content, page_file)
        used = used_components(content)
        classmap = extract_classnames_per_component(content)

        children = [(n, p) for n, p in imports.items() if n in used]

        lines.append(f"### Route `{route}`")
        lines.append("")
        lines.append("```")
        lines.append(f"[Page: {route}] - {rel(page_file)}")

        for idx, (name, path) in enumerate(children):
            is_last = idx == len(children) - 1
            connector = "└── " if is_last else "├── "
            child_prefix = "    " if is_last else "│   "

            classes = classmap.get(name, [])
            cls_str = f" ({' '.join(classes)})" if classes else ""
            file_str = f" - {rel(path)}"

            lines.append(f"{connector}[{name}]{file_str}{cls_str}")
            lines.extend(
                render_tree(path, registry, depth=1, visited={page_file}, prefix=child_prefix)
            )

        lines.append("```")
        lines.append("")

    return "\n".join(lines)

# ─── UI-REVIEW.md update ──────────────────────────────────────────────────────

SECTION_MARKER = "## Component Hierarchy Map"


def update_review(tree_text: str) -> None:
    content = read(REVIEW_FILE)

    if SECTION_MARKER in content:
        # Replace existing section (everything from marker to end of file)
        idx = content.index(SECTION_MARKER)
        updated = content[:idx] + tree_text
    else:
        updated = content.rstrip() + "\n\n---\n\n" + tree_text

    REVIEW_FILE.write_text(updated, encoding="utf-8")
    print(f"✓ Updated {rel(REVIEW_FILE)}")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print_only = "--print-only" in sys.argv

    print("◆ Scanning frontend components...")
    tree = generate()

    print()
    print(tree)

    if not print_only:
        update_review(tree)


if __name__ == "__main__":
    main()
