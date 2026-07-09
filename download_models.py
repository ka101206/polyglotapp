"""Build-time pre-download of TTS models.

Run during the Docker image build so the Style-Bert-VITS2 (Japanese) models are
baked directly into an image layer instead of being downloaded at runtime on
first use. This makes cold starts instant and the container self-contained /
offline-capable — no dependency on HuggingFace being reachable at run time.

Paths and repo IDs are imported from tts_sbv2 so they always match what the
application loads at runtime.
"""
import sys

from huggingface_hub import snapshot_download

from tts_sbv2 import _VOICE_CONFIG, _ASSETS_DIR

# Japanese BERT model that Style-Bert-VITS2 loads via the HF cache at runtime.
BERT_REPO = "ku-nlp/deberta-v2-large-japanese-char-wwm"


def main() -> None:
    # --- SBV2 voice model(s) -> /app/model_assets/<local_dir> ---
    seen = set()
    for gender, cfg in _VOICE_CONFIG.items():
        repo_id = cfg["repo_id"]
        local_dir = _ASSETS_DIR / cfg["local_dir"]
        key = (repo_id, str(local_dir))
        if key in seen:
            continue
        seen.add(key)
        print(f"[bake] SBV2 voice model {repo_id} -> {local_dir}", flush=True)
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(local_dir),
            local_dir_use_symlinks=False,
        )

    # --- Japanese BERT -> default HF cache (/root/.cache/huggingface) ---
    print(f"[bake] BERT model {BERT_REPO} -> HF cache", flush=True)
    snapshot_download(repo_id=BERT_REPO)

    print("[bake] ✅ All TTS models baked into the image.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 - surface any failure to the build
        print(f"[bake] ❌ Model download failed: {e}", file=sys.stderr, flush=True)
        raise
