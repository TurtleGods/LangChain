import hashlib
from pathlib import Path
from typing import Dict, List

from app.services.db_service import get_wiki_checksums, upsert_wiki_document


ALLOWED_EXTENSIONS = {".md", ".txt", ".sql"}
EXCLUDED_DIRS = {".git", ".attachments", "__pycache__"}
DEFAULT_WIKI_ROOT = Path("wiki")


def _is_allowed_file(path: Path) -> bool:
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False
    return not any(part in EXCLUDED_DIRS for part in path.parts)


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def _calc_checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _list_wiki_files(wiki_root: Path) -> List[Path]:
    files = [p for p in wiki_root.rglob("*") if p.is_file() and _is_allowed_file(p)]
    files.sort()
    return files


async def sync_wiki_documents(wiki_root: str = "wiki\MAYO-ApolloAsia-Knowledge-Management.wiki\首頁") -> Dict[str, int]:
    root = Path(wiki_root)
    if not root.exists():
        return {"scanned": 0, "upserted": 0, "skipped": 0}

    existing_checksums = await get_wiki_checksums()
    files = _list_wiki_files(root)

    scanned = 0
    upserted = 0
    skipped = 0

    for file_path in files:
        scanned += 1
        rel_path = file_path.relative_to(root).as_posix()

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="utf-8", errors="ignore")

        checksum = _calc_checksum(content)
        if existing_checksums.get(rel_path) == checksum:
            skipped += 1
            continue

        title = _extract_title(content, file_path.stem)
        doc = {
            "id": f"wiki:{rel_path}",
            "rel_path": rel_path,
            "title": title,
            "content": content,
            "checksum": checksum,
        }
        await upsert_wiki_document(doc)
        upserted += 1

    return {"scanned": scanned, "upserted": upserted, "skipped": skipped}
