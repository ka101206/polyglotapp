# llm_config.py — hot-reloadable LLM model selection.
#
# The active model lives in a JSON file (llm_config.json) that is bind-mounted
# into the backend container. Edit the file on the host and the change is picked
# up live — no restart — because we re-read only when the file's mtime changes.
#
# This is how you "change the model at will": just edit llm_config.json.
import json
import os
import threading

_CONFIG_PATH = os.environ.get("LLM_CONFIG_PATH", "/app/llm_config.json")
_lock = threading.Lock()
_cache = {"mtime": None, "data": None}


def _load():
    """Return the parsed config dict, re-reading only when the file changes.
    Keeps the last good data if the file is temporarily missing or invalid."""
    try:
        mtime = os.stat(_CONFIG_PATH).st_mtime
    except OSError:
        return _cache["data"]
    with _lock:
        if _cache["mtime"] != mtime:
            try:
                with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                    _cache["data"] = json.load(f)
                _cache["mtime"] = mtime
            except (json.JSONDecodeError, OSError):
                # Leave the previous good value in place on a bad/partial edit.
                pass
        return _cache["data"]


def get_active_model(default=None):
    """The model string every LLM call should use right now. Falls back to
    `default` (env/AI_MODEL) if the file is missing or has no model set."""
    data = _load()
    if isinstance(data, dict):
        model = data.get("model")
        if model:
            return model
    return default


def get_config():
    """Full config dict (model + available list), for read-only inspection."""
    data = _load()
    return data if isinstance(data, dict) else {}
