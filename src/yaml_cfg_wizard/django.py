"""Optional server-rendered Django adapter; host views supply authorization."""

from __future__ import annotations

import yaml
from django.http import HttpResponseNotAllowed
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from .editor import ConflictError, Editor, EditorError, ValidationError


@never_cache
@csrf_protect
def render_editor(request, editor: Editor, template_name: str, context=None):
    """GET/POST renderer for a host-owned template and authenticated view.

    This function is not a URL endpoint. Hosts MUST enforce admin authorization
    before calling it. Never pass submitted values back into template context.
    """
    if request.method not in {"GET", "POST"}:
        return HttpResponseNotAllowed(["GET", "POST"])
    file_id = request.POST.get("file", "") if request.method == "POST" else request.GET.get("file", next(iter(editor.files), ""))
    status, error, saved, snapshot = 200, None, False, None
    try:
        if request.method == "POST":
            path = request.POST.get("path", "")
            action = request.POST.get("action", "")
            revision = request.POST.get("revision", "")
            if action == "set":
                text = request.POST.get("value", "")
                if len(text) > 8192:
                    raise ValidationError("Submitted value is too large.")
                try:
                    # A blank text input is an empty string, not deletion/null.
                    value = yaml.safe_load(text) if text else ""
                except (yaml.YAMLError, RecursionError):
                    raise ValidationError("Submitted value is not valid YAML.") from None
                snapshot = editor.save(file_id, revision, {path: value})
            elif action == "remove":
                snapshot = editor.save(file_id, revision, {}, remove=[path])
            else:
                raise EditorError("Unknown edit action.")
            saved = True
        else:
            snapshot = editor.snapshot(file_id)
    except EditorError as exc:
        status = 409 if isinstance(exc, ConflictError) else 400
        error = str(exc)
        if file_id in editor.files:
            try:
                snapshot = editor.snapshot(file_id)
            except EditorError:
                pass
    # Broken on-disk configuration can also break host context processors.
    # Render the recovery/error page without them if resolution failed.
    return render(request if snapshot is not None else None, template_name, {
        **(context or {}), "file_id": file_id if file_id in editor.files else "",
        "files": {name: str(path) for name, path in editor.files.items()},
        "snapshot": snapshot, "rows": snapshot.rows if snapshot else [],
        "error": error, "saved": saved,
    }, status=status)
