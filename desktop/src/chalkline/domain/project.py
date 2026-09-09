"""Lossless legacy JSON envelope and versioned .chalkline document.

Keep unknown fields and all legacy shapes while their UI is being ported. Do not
normalise offset-relative tag times into already-absolute annotation times.
"""
from copy import deepcopy
from pathlib import Path
import json
import math
import os
import tempfile
import zipfile
from chalkline.domain.clips import DEFAULT_PADS

SCHEMA_VERSION = 1
MAX_DOCUMENT_BYTES = 32 * 1024 * 1024


def new_project() -> dict:
    return {"format": "chalkline", "schemaVersion": SCHEMA_VERSION,
            "media": {}, "session": {"marks": [], "pads": deepcopy(DEFAULT_PADS), "offset": 0,
                                     "tomb": [], "autoEditNew": True, "defaultPlayer": '', "tagLag": 1},
            "settings": {"autoFreeze": True, "hold": 3, "burnAll": False}}


def import_legacy(data: dict) -> dict:
    if not isinstance(data, dict) or not isinstance(data.get("marks"), list):
        raise ValueError("Expected a Chalkline marks/session JSON with a marks array")
    result = new_project()
    result["session"] = deepcopy(data)
    result["session"].setdefault("offset", 0)
    result["session"].setdefault("pads", [])
    return validate_project(result)


def validate_project(data: dict) -> dict:
    """Reject unusable documents before they replace a working session.

    Unknown fields and drawing tools remain intact for forward-compatible ports.
    """
    if not isinstance(data, dict) or data.get('format') != 'chalkline' or data.get('schemaVersion') != SCHEMA_VERSION:
        raise ValueError('Unsupported project format/version; original file was not changed')
    session = data.get('session')
    if not isinstance(session, dict) or not isinstance(session.get('marks'), list):
        raise ValueError('Project has no valid clips array')
    for key in ('media', 'settings'):
        if key not in data:
            data[key] = deepcopy(new_project()[key])
        if not isinstance(data[key], dict):
            raise ValueError(f'Project {key} must be an object')
    offset = session.get('offset', 0)
    if not isinstance(offset, (int, float)) or not math.isfinite(offset):
        raise ValueError('Project offset must be a finite number')
    seen = set()
    for mark in session['marks']:
        if not isinstance(mark, dict) or not isinstance(mark.get('id'), str) or not mark['id']:
            raise ValueError('Every clip needs a valid ID')
        if mark['id'] in seen:
            raise ValueError('Project contains duplicate clip IDs')
        seen.add(mark['id'])
        for key, default in (('t', None), ('pre', 2), ('post', 7)):
            value = mark.get(key, default)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or (key != 't' and value < 0):
                raise ValueError(f'Clip {mark["id"]} has an invalid {key} time')
        if not isinstance(mark.get('shapes', []), list) or any(not isinstance(s, dict) for s in mark.get('shapes', [])):
            raise ValueError(f'Clip {mark["id"]} has an invalid drawings array')
    if not isinstance(session.get('pads', []), list) or any(not isinstance(p, dict) for p in session.get('pads', [])):
        raise ValueError('Project has an invalid tag pads array')
    return data


def resolve_media(project: dict, document: Path) -> Path | None:
    media = project.get("media", {})
    relative = media.get("relativePath")
    if relative:
        candidate = document.parent / relative
        if candidate.is_file():
            return candidate.resolve()
    absolute = media.get("path")
    if absolute and Path(absolute).is_file():
        return Path(absolute)
    return None


def save_project(project: dict, destination: Path) -> None:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = validate_project(deepcopy(project))
    source = document.get("media", {}).get("path")
    if source:
        try:
            document["media"]["relativePath"] = os.path.relpath(source, destination.parent)
        except ValueError:  # different Windows drives
            document["media"].pop("relativePath", None)
    payload = json.dumps(document, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(payload) > MAX_DOCUMENT_BYTES:
        raise ValueError("Project document exceeds the 32 MiB limit")
    descriptor, name = tempfile.mkstemp(prefix=".chalkline-save-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w+b") as stream:
            with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("project.json", payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, destination)
    finally:
        Path(name).unlink(missing_ok=True)


def load_project(path: Path) -> dict:
    path = Path(path)
    if path.suffix.lower() == ".json":
        if path.stat().st_size > MAX_DOCUMENT_BYTES:
            raise ValueError("Legacy document too large")
        return import_legacy(json.loads(path.read_text(encoding="utf-8-sig")))
    with zipfile.ZipFile(path) as archive:
        info = archive.getinfo("project.json")
        if info.file_size > MAX_DOCUMENT_BYTES:
            raise ValueError("Project document too large")
        data = json.loads(archive.read(info))  # Never extract arbitrary archive paths.
    return validate_project(data)
