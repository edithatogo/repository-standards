"""Native, self-contained GLiNER 0.2.30 / mDeBERTa PII model contract.

This validates the selected uni-encoder model format, not detector recall.
The asset manifest binds bytes separately; real model tests qualify execution.
"""
from __future__ import annotations

from importlib.metadata import version
import json
import os
from pathlib import Path
import stat

MODEL_FILES = frozenset({"gliner_config.json", "encoder/config.json",
                         "tokenizer_config.json", "tokenizer.json", "model.safetensors"})
MODEL_ID = "microsoft/mdeberta-v3-base"
GLINER_VERSION = "0.2.30"
INVALID_BUNDLE = "Offline model bundle is invalid"
INVALID_RUNTIME = "Offline model runtime is unavailable"


def _unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError(INVALID_BUNDLE)
        result[name] = value
    return result


def _reject_constant(_value):
    raise ValueError(INVALID_BUNDLE)


def read_object(path: Path) -> dict:
    if not 0 < path.stat().st_size <= 16 * 1024 * 1024:
        raise ValueError(INVALID_BUNDLE)
    value = json.loads(path.read_text(encoding="utf-8"),
                       object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    if not isinstance(value, dict):
        raise ValueError(INVALID_BUNDLE)
    return value


def _reject_remote_fields(value):
    if isinstance(value, dict):
        for name, item in value.items():
            if name in {"auto_map", "custom_pipelines", "code_revision"}:
                raise ValueError(INVALID_BUNDLE)
            if name == "trust_remote_code" and item is not False:
                raise ValueError(INVALID_BUNDLE)
            _reject_remote_fields(item)
    elif isinstance(value, list):
        for item in value:
            _reject_remote_fields(item)


def validate_model_bundle(root: Path) -> None:
    """Require native config, a built-in encoder, local tokenizer and safe weights."""
    try:
        root = Path(root).absolute()
        for parent in (*reversed(root.parents), root):
            if stat.S_ISLNK(parent.lstat().st_mode):
                raise ValueError(INVALID_BUNDLE)
        pending, names, inodes = [root], set(), set()
        while pending:
            directory = pending.pop()
            if not stat.S_ISDIR(directory.lstat().st_mode):
                raise ValueError(INVALID_BUNDLE)
            for child in directory.iterdir():
                info = child.lstat()
                if stat.S_ISDIR(info.st_mode):
                    pending.append(child)
                elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                    identity = (info.st_dev, info.st_ino)
                    if identity in inodes or not info.st_size:
                        raise ValueError(INVALID_BUNDLE)
                    inodes.add(identity)
                    names.add(child.relative_to(root).as_posix())
                    if child.name == "adapter_config.json" or child.suffix in {".py", ".pyc"}:
                        raise ValueError(INVALID_BUNDLE)
                else:
                    raise ValueError(INVALID_BUNDLE)
        if not MODEL_FILES.issubset(names):
            raise ValueError(INVALID_BUNDLE)
        config = read_object(root / "gliner_config.json")
        encoder = read_object(root / "encoder/config.json")
        tokenizer = read_object(root / "tokenizer_config.json")
        for payload in (config, encoder, tokenizer):
            _reject_remote_fields(payload)
        if (config.get("model_type") != "gliner_uni_encoder_span"
                or config.get("model_name") != MODEL_ID
                or config.get("span_mode") != "markerV0"
                or config.get("words_splitter_type") != "whitespace"
                or any(config.get(key) is not None for key in
                       ("labels_encoder", "labels_decoder", "relations_layer"))
                or config.get("encoder_config") != encoder
                or encoder.get("model_type") != "deberta-v2"):
            raise ValueError(INVALID_BUNDLE)
        for key in ("hidden_size", "num_hidden_layers", "num_attention_heads", "vocab_size"):
            if type(encoder.get(key)) is not int or encoder[key] <= 0:
                raise ValueError(INVALID_BUNDLE)
        if tokenizer.get("tokenizer_class") not in {"DebertaV2Tokenizer", "DebertaV2TokenizerFast"}:
            raise ValueError(INVALID_BUNDLE)
        for key in ("tokenizer_file", "vocab_file", "special_tokens_map_file", "added_tokens_file"):
            value = tokenizer.get(key)
            if value is not None and (not isinstance(value, str) or value not in names or "/" in value):
                raise ValueError(INVALID_BUNDLE)
        token_data = read_object(root / "tokenizer.json")
        if (token_data.get("version") != "1.0" or not isinstance(token_data.get("model"), dict)
                or token_data["model"].get("type") != "Unigram"
                or not isinstance(token_data["model"].get("vocab"), list)
                or not token_data["model"]["vocab"]):
            raise ValueError(INVALID_BUNDLE)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        raise ValueError(INVALID_BUNDLE) from None


def load_local_model(root: Path):
    """Load only the selected built-in Deberta uni-encoder, with no Hub fallback.

    GLiNER's generic AutoModel branches enable remote code. This selected class and
    validated embedded Deberta config use its built-in DebertaV2Model constructor.
    The explicit tokenizer override disables remote code in the remaining auto API.
    """
    validate_model_bundle(root)
    root = Path(root).resolve(strict=True)
    try:
        if version("gliner") != GLINER_VERSION or os.environ.get("USE_FLASHDEBERTA"):
            raise ValueError(INVALID_RUNTIME)
        from gliner.model import UniEncoderSpanGLiNER
        from transformers import AutoTokenizer

        class OfflineSpanGLiNER(UniEncoderSpanGLiNER):
            @classmethod
            def _load_config(cls, config_file, **kwargs):
                config = super()._load_config(config_file, **kwargs)
                # Adapter detection must never inspect the consumer's working directory.
                config.model_name = str(root / "encoder")
                return config

            @classmethod
            def _load_tokenizer(cls, config, model_dir, cache_dir=None, local_files_only=True):
                if Path(model_dir).resolve(strict=True) != root:
                    raise ValueError(INVALID_RUNTIME)
                tokenizer = AutoTokenizer.from_pretrained(
                    str(root), local_files_only=True, trust_remote_code=False, token=False,
                )
                return cls._set_tokenizer_spec_tokens(tokenizer)

        return OfflineSpanGLiNER.from_pretrained(
            str(root), local_files_only=True, token=False, map_location="cpu",
            strict=True, load_tokenizer=True,
        )
    except Exception:
        raise ValueError(INVALID_RUNTIME) from None
