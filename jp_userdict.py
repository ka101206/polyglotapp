"""
Load a user pronunciation dictionary into OpenJTalk so Style-Bert-VITS2 (and the
pitch-accent helper in jp_pitch.py) read proper nouns correctly.

OpenJTalk's built-in dictionary misreads some words — mostly rare kanji and
special "gikun" readings — e.g. 呪術廻戦 came out as ジュジュツマワリセン
(廻 read as まわり) instead of ジュジュツカイセン. Registering the word fixes it.

To add a word, append one line to jp_userdict.csv (OpenJTalk / naist-jdic
format, UTF-8, no header):

    <surface>,1348,1348,1,名詞,固有名詞,一般,*,*,*,<surface>,<reading>,<pron>,<accent>,*

where <reading>/<pron> are katakana and <accent> is "<drop>/<mora_count>"
(e.g. 0/7 for flat). 1348 is a proper-noun context id. Then rebuild the
backend (or restart it) to recompile the dictionary.
"""

import os
import logging
import tempfile
import threading

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CSV_PATH = os.path.join(_BASE_DIR, "jp_userdict.csv")

_loaded = False
_lock = threading.Lock()


def ensure_user_dict_loaded():
    """Compile jp_userdict.csv and register it globally with OpenJTalk. Idempotent
    and best-effort — failures are logged and never raised, so TTS still works."""
    global _loaded
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
        _loaded = True  # set first so a failure doesn't retry-storm on every call
        try:
            if not os.path.isfile(_CSV_PATH) or os.path.getsize(_CSV_PATH) == 0:
                return
            import pyopenjtalk

            dic_path = os.path.join(tempfile.gettempdir(), "polyglot_jp_userdict.dic")
            pyopenjtalk.mecab_dict_index(_CSV_PATH, dic_path)
            pyopenjtalk.update_global_jtalk_with_user_dict(dic_path)
            logger.info("Loaded Japanese user pronunciation dictionary: %s", _CSV_PATH)
        except Exception as e:
            logger.warning("Could not load Japanese user dictionary: %s", e)
