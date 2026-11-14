#!/usr/bin/env python3
"""Prepare a pinned native model bundle online; do not qualify or deploy it."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import urllib.request

OFFLINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OFFLINE))
from security.model_assets import MODEL_ID, read_object, validate_model_bundle

CATALOG = Path(__file__).with_name("model-sources.json")
FAILURE = "Offline model preparation failed"
LAYOUT = {
    "model_config": ("model", "gliner_config.json"),
    "checkpoint": ("model", "pytorch_model.bin"),
    "encoder_config": ("encoder", "config.json"),
    "encoder_tokenizer_config": ("encoder", "tokenizer_config.json"),
    "encoder_sentencepiece": ("encoder", "spm.model"),
}

ATTRIBUTION_LAYOUT = {
    "model_card": ("attribution/gliner-model-card.md", "model-license-declaration"),
    "encoder_card": ("attribution/mdeberta-model-card.md", "model-license-declaration"),
    "model_source_license": ("attribution/gliner-source-LICENSE.txt", "associated-source-code-license"),
    "encoder_source_license": ("attribution/deberta-source-LICENSE.txt", "associated-source-code-license"),
}
SOURCE_LICENSE_REPOS = {
    "model_source_license": "urchade/GLiNER",
    "encoder_source_license": "microsoft/DeBERTa",
}


class PreparationFailure(ValueError):
    def __init__(self, stage):
        self.stage = stage
        super().__init__(FAILURE)


@contextmanager
def preparation_stage(stage):
    try:
        yield
    except PreparationFailure:
        raise
    except Exception:
        raise PreparationFailure(stage) from None


def write_receipt(path, receipt):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".model-preparation-", delete=False) as stream:
            temporary = Path(stream.name)
            os.fchmod(stream.fileno(), 0o600)
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_catalog(path=CATALOG):
    data = read_object(path)
    if set(data) != {"schema_version", "model", "encoder", "files", "attribution"} or type(data["schema_version"]) is not int or data["schema_version"] != 2:
        raise ValueError(FAILURE)
    for kind, repo in (("model", "urchade/gliner_multi_pii-v1"), ("encoder", MODEL_ID)):
        source = data[kind]
        if (not isinstance(source, dict) or set(source) != {"repo", "revision", "license"}
                or source["repo"] != repo or not isinstance(source["revision"], str)
                or not re.fullmatch(r"[0-9a-f]{40}", source["revision"])
                or not isinstance(source["license"], str) or not source["license"]):
            raise ValueError(FAILURE)
    if not isinstance(data["files"], dict) or set(data["files"]) != set(LAYOUT):
        raise ValueError(FAILURE)
    for name, (source, filename) in LAYOUT.items():
        item = data["files"][name]
        if (not isinstance(item, dict) or set(item) != {"source", "path", "size", "sha256"}
                or item["source"] != source or item["path"] != filename
                or type(item["size"]) is not int or not 0 < item["size"] <= 2 * 1024**3
                or not isinstance(item["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])):
            raise ValueError(FAILURE)
    if not isinstance(data["attribution"], dict) or set(data["attribution"]) != set(ATTRIBUTION_LAYOUT):
        raise ValueError(FAILURE)
    for role, (filename, scope) in ATTRIBUTION_LAYOUT.items():
        item = data["attribution"][role]
        if (not isinstance(item, dict) or set(item) != {"url", "path", "scope", "size", "sha256"}
                or item["path"] != filename or item["scope"] != scope
                or not isinstance(item["url"], str)
                or type(item["size"]) is not int or not 0 < item["size"] <= 1024**2
                or not isinstance(item["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])):
            raise ValueError(FAILURE)
        if role in ("model_card", "encoder_card"):
            source = data[role.removesuffix("_card")]
            expected = f"https://huggingface.co/{source['repo']}/resolve/{source['revision']}/README.md"
            if item["url"] != expected:
                raise ValueError(FAILURE)
        else:
            repo = re.escape(SOURCE_LICENSE_REPOS[role])
            if not re.fullmatch(rf"https://raw\.githubusercontent\.com/{repo}/[0-9a-f]{{40}}/LICENSE", item["url"]):
                raise ValueError(FAILURE)
    return data


def download(url, record, destination):
    """Stream exact public source bytes; no extraction or checkpoint execution."""
    digest, count, started = hashlib.sha256(), 0, time.monotonic()
    with urllib.request.urlopen(url, timeout=30) as response, Path(destination).open("xb") as output:
        if not response.geturl().startswith("https://"):
            raise ValueError(FAILURE)
        while chunk := response.read(1024 * 1024):
            count += len(chunk)
            if count > record["size"] or time.monotonic() - started > 900:
                raise ValueError(FAILURE)
            digest.update(chunk)
            output.write(chunk)
    if count != record["size"] or digest.hexdigest() != record["sha256"]:
        raise ValueError(FAILURE)


def export_model(inputs, destination):
    """Use only built-in local tokenizer code and tensor-only checkpoint loading."""
    with preparation_stage("export-tokenizer"):
        from transformers import AutoTokenizer
        config = read_object(inputs["model_config"])
        encoder = read_object(inputs["encoder_config"])
        if config.get("model_name") != MODEL_ID or encoder.get("model_type") != "deberta-v2":
            raise ValueError(FAILURE)
        encoder_dir = destination / "encoder"
        encoder_dir.mkdir()
        shutil.copyfile(inputs["encoder_config"], encoder_dir / "config.json")
        shutil.copyfile(inputs["encoder_tokenizer_config"], encoder_dir / "tokenizer_config.json")
        shutil.copyfile(inputs["encoder_sentencepiece"], encoder_dir / "spm.model")
        tokenizer = AutoTokenizer.from_pretrained(
            str(encoder_dir), local_files_only=True, trust_remote_code=False, token=False, use_fast=True,
        )
        if not tokenizer.is_fast:
            raise ValueError(FAILURE)
        tokenizer.save_pretrained(destination)
        token_config = read_object(destination / "tokenizer_config.json")
        for key in ("name_or_path", "_name_or_path"):
            token_config.pop(key, None)
        for key in ("tokenizer_file", "vocab_file", "special_tokens_map_file", "added_tokens_file"):
            value = token_config.get(key)
            if value is not None:
                local = Path(value).name
                if not (destination / local).is_file():
                    raise ValueError(FAILURE)
                token_config[key] = local
        token_config["trust_remote_code"] = False
        (destination / "tokenizer_config.json").write_text(
            json.dumps(token_config, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        config.update(model_type="gliner_uni_encoder_span", words_splitter_type="whitespace",
                      encoder_config=encoder)
        (destination / "gliner_config.json").write_text(
            json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )

    with preparation_stage("export-weights"):
        import torch
        from safetensors.torch import save_file
        state = torch.load(inputs["checkpoint"], map_location="cpu", weights_only=True)
        if not isinstance(state, dict) or not state or any(
                not isinstance(name, str) or not torch.is_tensor(value) for name, value in state.items()):
            raise ValueError(FAILURE)
        # Keep all state keys and values while separating shared storage for safetensors.
        tensors = {name: value.contiguous().clone() for name, value in state.items()}
        del state
        save_file(tensors, str(destination / "model.safetensors"))
        del tensors

    with preparation_stage("validate-bundle"):
        validate_model_bundle(destination)


def prepare(destination, receipt_path, catalog_path=CATALOG):
    if sys.version_info[:3] != (3, 15, 1):
        raise ValueError(FAILURE)
    catalog = load_catalog(catalog_path)
    destination = Path(destination).absolute()
    receipt_path = Path(receipt_path).absolute()
    if (destination.exists() or destination.is_symlink()
            or receipt_path.exists() or receipt_path.is_symlink()
            or receipt_path.is_relative_to(destination)):
        raise ValueError(FAILURE)
    destination.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(mode=0o755)
    inputs, verified = {}, []
    common = dict(
        schema_version=1, source_catalog_sha256=sha256(catalog_path),
        source_model=catalog["model"], source_encoder=catalog["encoder"],
        attribution_sources=catalog["attribution"],
        python_version="3.15.1", model_execution_qualified=False,
        image_qualified=False, runner_registration_qualified=False,
    )
    try:
        with tempfile.TemporaryDirectory(prefix="offline-model-inputs-", dir=destination.parent) as temporary:
            for role, record in catalog["files"].items():
                source = catalog[record["source"]]
                url = f"https://huggingface.co/{source['repo']}/resolve/{source['revision']}/{record['path']}"
                path = Path(temporary) / role
                with preparation_stage("download"):
                    download(url, record, path)
                inputs[role] = path
                verified.append(dict(role=role, url=url, size=record["size"], sha256=record["sha256"]))
            attribution = {}
            for role, record in catalog["attribution"].items():
                path = Path(temporary) / role
                with preparation_stage("download-attribution"):
                    download(record["url"], record, path)
                attribution[role] = path
                verified.append(dict(role=role, url=record["url"], size=record["size"],
                                     sha256=record["sha256"], scope=record["scope"]))
            with preparation_stage("retain-attribution"):
                (destination / "attribution").mkdir()
                for role, path in attribution.items():
                    shutil.copyfile(path, destination / catalog["attribution"][role]["path"])
            with preparation_stage("export"):
                export_model(inputs, destination)
        with preparation_stage("receipt"):
            outputs = []
            for path in sorted(destination.rglob("*")):
                if path.is_dir():
                    path.chmod(0o755)
                elif path.is_file():
                    path.chmod(0o644)
                    outputs.append(dict(path=path.relative_to(destination).as_posix(),
                                        size=path.stat().st_size, sha256=sha256(path)))
            receipt = dict(
                common, status="prepared", verified_inputs=verified, derived_files=outputs,
                libraries={name: version(name) for name in
                           ("gliner", "torch", "transformers", "safetensors", "sentencepiece", "protobuf")},
            )
            write_receipt(receipt_path, receipt)
    except PreparationFailure as error:
        failed = dict(common, status="failed", failed_stage=error.stage, verified_inputs=verified)
        try:
            write_receipt(receipt_path, failed)
        except Exception:
            raise PreparationFailure("receipt") from None
        raise
    return receipt


@contextmanager
def quiet_output():
    sys.stdout.flush()
    sys.stderr.flush()
    saved = [os.dup(1), os.dup(2)]
    try:
        with open(os.devnull, "wb") as sink:
            os.dup2(sink.fileno(), 1)
            os.dup2(sink.fileno(), 2)
            yield
    finally:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            for fd, original in zip((1, 2), saved):
                os.dup2(original, fd)
                os.close(original)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        with quiet_output():
            prepare(args.destination, args.receipt)
    except Exception:
        print(FAILURE, file=sys.stderr)
        return 2
    print("Offline model bundle prepared; execution qualification remains required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
