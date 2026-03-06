import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional

from app.services.db_service import get_wiki_checksums, load_wiki_documents, upsert_wiki_document


ALLOWED_EXTENSIONS = {".md", ".txt", ".sql"}
EXCLUDED_DIRS = {".git", ".attachments", "__pycache__"}
DEFAULT_WIKI_ROOT = Path("wiki")
DEFAULT_WIKI_FOLDER_NAME = "MAYO-ApolloAsia-Knowledge-Management.wiki"
WIKI_ROOT_ENV_KEY = "WIKI_ROOT"


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


def resolve_wiki_root(wiki_root: Optional[str] = None) -> Path:
    if wiki_root:
        return Path(wiki_root)

    env_root = os.getenv(WIKI_ROOT_ENV_KEY)
    if env_root:
        return Path(env_root)

    candidates = [
        DEFAULT_WIKI_ROOT / DEFAULT_WIKI_FOLDER_NAME,
        DEFAULT_WIKI_ROOT,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


async def sync_wiki_documents(wiki_root: Optional[str] = None) -> Dict[str, int]:
    root = resolve_wiki_root(wiki_root)
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


async def get_synced_wiki_documents(wiki_root: Optional[str] = None) -> List[Dict[str, str]]:
    await sync_wiki_documents(wiki_root)
    return await load_wiki_documents()
