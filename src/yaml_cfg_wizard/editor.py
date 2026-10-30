"""Allowlisted, framework-independent editing of configuration overrides.

The host supplies the actual layered resolver and the complete effective schema.
Only scalar fields explicitly registered by the host can be returned or changed.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
import tempfile
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit

import yaml
from jsonschema import Draft7Validator, FormatChecker


class EditorError(ValueError):
    """Safe, value-free error suitable for display to an administrator."""


class ConflictError(EditorError):
    """The file has changed since it was displayed."""


class ValidationError(EditorError):
    """The candidate effective configuration is invalid."""


@dataclass(frozen=True)
class Field:
    path: str
    label: str
    description: str = ""


@dataclass(frozen=True)
class Snapshot:
    revision: str
    rows: list[dict[str, Any]]


_MISSING = object()
_MAX_BYTES = 1024 * 1024
_SECRET = re.compile(r"(^|_)(secret|password|passwd|token|credential|credentials|api_key|dsn)($|_)", re.I)


def _get(data: Mapping, path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return _MISSING
        value = value[part]
    return value


def _unsafe_url(path: str, value: Any) -> bool:
    if not path.lower().endswith("url") or not isinstance(value, str) or not value:
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
        return bool(parsed.username or parsed.password or parsed.query or parsed.fragment or
                    (port is not None and not 0 < port <= 65535))
    except ValueError:
        return True


def _display(path: str, value: Any) -> Any:
    if value is _MISSING:
        return None
    if not isinstance(value, (str, int, float, bool, type(None))) or _unsafe_url(path, value):
        return "[hidden: unsafe value]"
    return value


class Editor:
    """Edit registered scalar paths in registered files, never request paths.

    Saves use a same-directory atomic replacement and an advisory sidecar lock.
    The lock serializes cooperating editor processes on Unix; external editors
    must still honor the lock to eliminate the final check/replace race.
    """

    def __init__(
        self,
        files: Mapping[str, Path],
        fields: Sequence[Field],
        resolve: Callable[[str, dict[str, Any]], dict[str, Any]],
        schema: Mapping[str, Any],
    ) -> None:
        self.files = {name: Path(path).absolute() for name, path in files.items()}
        self.fields = tuple(fields)
        self.resolve = resolve
        self.schema = deepcopy(dict(schema))
        Draft7Validator.check_schema(self.schema)
        self.validator = Draft7Validator(self.schema, format_checker=FormatChecker())
        paths = [field.path for field in fields]
        if len(paths) != len(set(paths)):
            raise ValueError("Duplicate editor field")
        for path in paths:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*", path):
                raise ValueError("Invalid editor field path")
            if any(_SECRET.search(part) for part in path.split(".")):
                raise ValueError("Secret fields cannot be registered")
            if any(other != path and other.startswith(path + ".") for other in paths):
                raise ValueError("Overlapping editor fields")
        self._paths = set(paths)

    def _target(self, file_id: str) -> Path:
        if file_id not in self.files:
            raise EditorError("File is not editable.")
        target = self.files[file_id]
        for path in (target, *target.parents):
            if path.is_symlink():
                raise EditorError("Symlinked configuration paths are not editable.")
        if target.exists() and not target.is_file():
            raise EditorError("Configuration target is not a regular file.")
        return target

    def _read(self, file_id: str) -> tuple[Path, bytes | None, dict[str, Any]]:
        target = self._target(file_id)
        try:
            if not target.exists():
                return target, None, {}
            with target.open("rb") as stream:
                raw = stream.read(_MAX_BYTES + 1)
            if len(raw) > _MAX_BYTES:
                raise EditorError("Configuration file is too large.")
            data = yaml.safe_load(raw)
        except (OSError, UnicodeError, yaml.YAMLError, RecursionError):
            raise EditorError("Configuration file cannot be read.") from None
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise EditorError("Configuration root must be a mapping.")
        return target, raw, data

    @staticmethod
    def _revision(raw: bytes | None) -> str:
        return hashlib.sha256(b"missing" if raw is None else b"file:" + raw).hexdigest()

    def _effective(self, file_id: str, data: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.resolve(file_id, deepcopy(data))
        except EditorError:
            raise
        except Exception:
            # Resolver/parser/schema exceptions may embed credential values.
            raise ValidationError("Effective configuration could not be resolved.") from None
        if not isinstance(result, dict):
            raise ValidationError("Effective configuration must be a mapping.")
        return result

    def _snapshot(self, raw: bytes | None, data: dict, effective: dict) -> Snapshot:
        rows = []
        for field in self.fields:
            override = _get(data, field.path)
            rows.append({
                "path": field.path, "label": field.label, "description": field.description,
                "overridden": override is not _MISSING,
                "override": _display(field.path, override),
                "effective": _display(field.path, _get(effective, field.path)),
            })
        return Snapshot(self._revision(raw), rows)

    def snapshot(self, file_id: str) -> Snapshot:
        _target, raw, data = self._read(file_id)
        return self._snapshot(raw, data, self._effective(file_id, data))

    @contextmanager
    def _lock(self, target: Path):
        import fcntl

        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._target(next(name for name, path in self.files.items() if path == target))
        lock = target.with_name(target.name + ".editor.lock")
        fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise EditorError("Configuration lock is not a regular file.")
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def _validate_changes(self, changes: Mapping[str, Any]) -> None:
        """Validate transport values; subclasses may support schema-safe containers."""
        for path, value in changes.items():
            if not isinstance(value, (str, int, float, bool, type(None))) or _unsafe_url(path, value):
                raise ValidationError("Override must be a safe scalar value.")

    def _file_mode(self, target: Path, raw: bytes | None) -> int:
        return stat.S_IMODE(target.stat().st_mode) if raw is not None else 0o600

    def _validate_effective_values(self, effective: Mapping[str, Any]) -> None:
        if any(_unsafe_url(field.path, _get(effective, field.path)) for field in self.fields):
            raise ValidationError("Effective configuration contains an unsafe URL.")

    def save(
        self, file_id: str, revision: str, changes: Mapping[str, Any],
        remove: Sequence[str] = (),
    ) -> Snapshot:
        if (set(changes) | set(remove)) - self._paths:
            raise EditorError("Field is not editable.")
        if set(changes) & set(remove):
            raise EditorError("Cannot set and remove the same override.")
        self._validate_changes(changes)
        target = self._target(file_id)
        temporary: str | None = None
        try:
            with self._lock(target):
                _target, raw, data = self._read(file_id)
                if revision != self._revision(raw):
                    raise ConflictError("Configuration changed. Reload before saving.")
                candidate = deepcopy(data)
                for path in (*changes, *remove):
                    parts = path.split(".")
                    node = candidate
                    for part in parts[:-1]:
                        if part not in node:
                            if path in remove:
                                break
                            node[part] = {}
                        if not isinstance(node[part], dict):
                            raise ValidationError("Override parent must be a mapping.")
                        # YAML aliases must not propagate an allowlisted edit
                        # into an unrelated, nonallowlisted subtree.
                        node[part] = deepcopy(node[part])
                        node = node[part]
                    else:
                        if path in changes:
                            node[parts[-1]] = deepcopy(changes[path])
                        else:
                            node.pop(parts[-1], None)
                effective = self._effective(file_id, candidate)
                if next(self.validator.iter_errors(effective), None) is not None:
                    raise ValidationError("Effective configuration violates its schema.")
                self._validate_effective_values(effective)
                # Check unmasked overrides too, so env/creds cannot hide an
                # invalid value that would become active after a later restart.
                for path, value in changes.items():
                    field_schema = self.schema
                    for part in path.split("."):
                        field_schema = field_schema.get("properties", {}).get(part, {})
                    if next(self.validator.evolve(schema=field_schema).iter_errors(value), None) is not None:
                        raise ValidationError("Override violates its field schema.")
                output = yaml.safe_dump(candidate, sort_keys=False, allow_unicode=True).encode("utf-8")
                if len(output) > _MAX_BYTES:
                    raise ValidationError("Configuration file is too large.")
                if self._read(file_id)[1] != raw:
                    raise ConflictError("Configuration changed. Reload before saving.")
                fd, temporary = tempfile.mkstemp(prefix="." + target.name + ".", dir=target.parent)
                with os.fdopen(fd, "wb") as stream:
                    os.fchmod(stream.fileno(), self._file_mode(target, raw))
                    stream.write(output)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
                temporary = None
                directory_fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
                return self._snapshot(output, candidate, effective)
        except OSError:
            raise EditorError("Configuration could not be saved.") from None
        finally:
            if temporary is not None:
                os.unlink(temporary)
