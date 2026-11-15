"""Bounded source preparation contracts; no real model is downloaded in these tests."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
OFFLINE = ROOT / "security/offline-ai"
SCRIPT = OFFLINE / "provision/prepare_model.py"
spec = importlib.util.spec_from_file_location("offline_prepare_model", SCRIPT)
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)


class ModelPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="model-preparation-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_catalog_pins_complete_model_and_encoder_closure(self):
        catalog = preparation.load_catalog()
        self.assertEqual(set(catalog["files"]), {
            "model_config", "checkpoint", "encoder_config",
            "encoder_tokenizer_config", "encoder_sentencepiece",
        })
        self.assertEqual(catalog["model"]["revision"], "1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d")
        self.assertEqual(catalog["encoder"]["revision"], "a0484667b22365f84929a935b5e50a51f71f159d")
        self.assertEqual(catalog["schema_version"], 2)
        self.assertEqual(set(catalog["attribution"]), {
            "model_card", "encoder_card", "model_source_license", "encoder_source_license",
        })
        for role, record in catalog["attribution"].items():
            expected = "model-license-declaration" if role.endswith("_card") else "associated-source-code-license"
            self.assertEqual(record["scope"], expected)

    def test_other_runtime_patches_fail_before_model_acquisition(self):
        for version in ((3, 15, 1), (3, 15, 3)):
            with self.subTest(version=version), patch.object(
                    preparation.sys, "version_info", version), patch.object(preparation, "load_catalog") as load:
                with self.assertRaisesRegex(ValueError, "Offline model preparation failed"):
                    preparation.prepare(self.root / "model", self.root / "receipt.json")
                load.assert_not_called()
        self.assertFalse((self.root / "model").exists())

    def test_incomplete_or_unpinned_catalog_is_rejected(self):
        original = json.loads(preparation.CATALOG.read_text())
        path = self.root / "sources.json"
        for change in (
            lambda data: data["files"].pop("encoder_sentencepiece"),
            lambda data: data["model"].update(revision="main"),
            lambda data: data["files"]["checkpoint"].update(path="../unreviewed"),
            lambda data: data["files"]["checkpoint"].update(size=True),
            lambda data: data["files"]["checkpoint"].update(sha256=None),
            lambda data: data["attribution"].pop("model_card"),
            lambda data: data["attribution"]["model_card"].update(url="https://huggingface.co/urchade/gliner_multi_pii-v1/resolve/main/README.md"),
            lambda data: data["attribution"]["model_source_license"].update(url="https://raw.githubusercontent.com/urchade/GLiNER/main/LICENSE"),
            lambda data: data["attribution"]["encoder_source_license"].update(scope="model-license-declaration"),
            lambda data: data["attribution"]["model_card"].update(path="../README.md"),
            lambda data: data["attribution"]["model_card"].update(size=True),
            lambda data: data["attribution"]["model_card"].update(sha256=None),
        ):
            data = json.loads(json.dumps(original))
            change(data)
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                preparation.load_catalog(path)

    def test_download_requires_exact_length_digest_and_https(self):
        payload = b"synthetic verified source"
        record = dict(size=len(payload), sha256=hashlib.sha256(payload).hexdigest())

        class Response(io.BytesIO):
            def geturl(self):
                return "https://huggingface.co/synthetic/resolve/commit/file"

        with patch.object(preparation.urllib.request, "urlopen", return_value=Response(payload)):
            destination = self.root / "valid"
            preparation.download("https://huggingface.co/source", record, destination)
            self.assertEqual(destination.read_bytes(), payload)
        for name, body, digest in (("short", payload[:-1], record["sha256"]),
                                   ("long", payload + b"x", record["sha256"]),
                                   ("changed", payload, "0" * 64)):
            with self.subTest(case=name), patch.object(
                    preparation.urllib.request, "urlopen", return_value=Response(body)):
                with self.assertRaises(ValueError):
                    preparation.download("https://huggingface.co/source",
                        dict(size=len(payload), sha256=digest), self.root / name)

    def test_download_rejects_non_https_redirect(self):
        class Response(io.BytesIO):
            def geturl(self):
                return "http://example.invalid/source"
        with patch.object(preparation.urllib.request, "urlopen", return_value=Response(b"x")):
            with self.assertRaises(ValueError):
                preparation.download("https://huggingface.co/source",
                    dict(size=1, sha256=hashlib.sha256(b"x").hexdigest()), self.root / "http")

    def test_existing_outputs_are_preserved_before_download(self):
        destination, receipt = self.root / "model", self.root / "receipt.json"
        destination.mkdir()
        marker = destination / "existing"
        marker.write_text("preserved")
        with patch.object(preparation.sys, "version_info", (3, 15, 2)), \
                patch.object(preparation, "download") as download:
            with self.assertRaises(ValueError):
                preparation.prepare(destination, receipt)
        download.assert_not_called()
        self.assertEqual(marker.read_text(), "preserved")

    def test_preparation_records_source_and_derived_hashes_without_qualification(self):
        fixture = json.loads((OFFLINE / "tests/fixtures/native_model.json").read_text())
        calls = []
        catalog = preparation.load_catalog()
        attribution_bytes = {
            record["path"]: (f"synthetic attribution: {role}\nCopyright café\n").encode("utf-8")
            for role, record in catalog["attribution"].items()
        }

        def download(url, record, path):
            calls.append((url, record))
            path.write_bytes(attribution_bytes.get(record["path"], b"synthetic source"))

        def export(inputs, destination):
            self.assertEqual(set(inputs), set(preparation.LAYOUT))
            for name, value in fixture.items():
                path = destination / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(value if isinstance(value, str) else json.dumps(value))
            preparation.validate_model_bundle(destination)

        destination, receipt = self.root / "model", self.root / "receipt.json"
        with patch.object(preparation.sys, "version_info", (3, 15, 2)), \
                patch.object(preparation, "download", side_effect=download), \
                patch.object(preparation, "export_model", side_effect=export), \
                patch.object(preparation, "version", return_value="synthetic"):
            result = preparation.prepare(destination, receipt)
        self.assertEqual(len(calls), 9)
        self.assertEqual(result["status"], "prepared")
        self.assertFalse(result["model_execution_qualified"])
        self.assertFalse(result["image_qualified"])
        self.assertFalse(result["runner_registration_qualified"])
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        for record in result["derived_files"]:
            self.assertEqual(record["sha256"], preparation.sha256(destination / record["path"]))
        self.assertEqual(result["attribution_sources"], catalog["attribution"])
        derived = {record["path"]: record for record in result["derived_files"]}
        verified = {record["role"]: record for record in result["verified_inputs"]}
        for role, source in catalog["attribution"].items():
            payload = attribution_bytes[source["path"]]
            self.assertEqual((destination / source["path"]).read_bytes(), payload)
            self.assertEqual(derived[source["path"]]["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(verified[role]["url"], source["url"])
            self.assertEqual(verified[role]["sha256"], source["sha256"])
            self.assertEqual(verified[role]["scope"], source["scope"])

    def test_failures_write_private_value_free_stage_receipts(self):
        for stage in ("download", "download-attribution", "export-tokenizer", "export-weights", "validate-bundle"):
            with self.subTest(stage=stage):
                destination = self.root / stage
                receipt = self.root / f"{stage}.json"

                def download(url, record, path):
                    if stage == "download" or (stage == "download-attribution" and "scope" in record):
                        raise ValueError("synthetic-private-download-marker")
                    path.write_bytes(b"synthetic source")

                def export(inputs, output):
                    with preparation.preparation_stage(stage):
                        raise ValueError("synthetic-private-export-marker")

                with patch.object(preparation.sys, "version_info", (3, 15, 2)), \
                        patch.object(preparation, "download", side_effect=download), \
                        patch.object(preparation, "export_model", side_effect=export):
                    with self.assertRaises(preparation.PreparationFailure) as caught:
                        preparation.prepare(destination, receipt)

                self.assertEqual(str(caught.exception), preparation.FAILURE)
                self.assertEqual(caught.exception.stage, stage)
                result = json.loads(receipt.read_text())
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["failed_stage"], stage)
                completed = {"download": 0, "download-attribution": 5}.get(stage, 9)
                self.assertEqual(len(result["verified_inputs"]), completed)
                self.assertFalse(result["model_execution_qualified"])
                self.assertFalse(result["image_qualified"])
                self.assertFalse(result["runner_registration_qualified"])
                self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
                self.assertNotIn("synthetic-private", receipt.read_text())
                self.assertNotIn("derived_files", result)

    def test_export_uses_local_tokenizer_and_tensor_only_checkpoint_loading(self):
        fixture = json.loads((OFFLINE / "tests/fixtures/native_model.json").read_text())
        raw = self.root / "inputs"
        raw.mkdir()
        inputs = {}
        for role in preparation.LAYOUT:
            path = raw / role
            value = fixture["gliner_config.json"] if role == "model_config" else (
                fixture["encoder/config.json"] if role == "encoder_config" else (
                fixture["tokenizer_config.json"] if role == "encoder_tokenizer_config" else "synthetic"))
            path.write_text(value if isinstance(value, str) else json.dumps(value))
            inputs[role] = path
        output = self.root / "export"
        output.mkdir()
        calls = {}

        class Tensor:
            def contiguous(self):
                return self
            def clone(self):
                return self

        def load(path, **kwargs):
            calls["checkpoint"] = (path, kwargs)
            return {"weight": Tensor()}

        class Tokenizer:
            is_fast = True
            def save_pretrained(self, destination):
                for name in ("tokenizer.json", "tokenizer_config.json"):
                    (destination / name).write_text(json.dumps(fixture[name]))

        def tokenizer(path, **kwargs):
            calls["tokenizer"] = (path, kwargs)
            return Tokenizer()

        def save_file(tensors, path):
            self.assertEqual(set(tensors), {"weight"})
            Path(path).write_bytes(b"synthetic safetensors")

        torch = types.ModuleType("torch")
        torch.load = load
        torch.is_tensor = lambda value: isinstance(value, Tensor)
        safetensors = types.ModuleType("safetensors")
        safe_torch = types.ModuleType("safetensors.torch")
        safe_torch.save_file = save_file
        transformers = types.ModuleType("transformers")
        transformers.AutoTokenizer = types.SimpleNamespace(from_pretrained=tokenizer)
        with patch.dict(sys.modules, {"torch": torch, "safetensors": safetensors,
                                      "safetensors.torch": safe_torch, "transformers": transformers}):
            preparation.export_model(inputs, output)
        self.assertEqual(calls["checkpoint"][1], {"map_location": "cpu", "weights_only": True})
        self.assertTrue(calls["tokenizer"][1]["local_files_only"])
        self.assertFalse(calls["tokenizer"][1]["trust_remote_code"])
        self.assertFalse((output / "config.json").exists())
        config = json.loads((output / "gliner_config.json").read_text())
        self.assertEqual(config["encoder_config"], fixture["encoder/config.json"])
        preparation.validate_model_bundle(output)

        for stage, target, attribute in (
                ("export-tokenizer", transformers.AutoTokenizer, "from_pretrained"),
                ("export-weights", torch, "load"),
                ("validate-bundle", preparation, "validate_model_bundle")):
            with self.subTest(stage=stage):
                failed_output = self.root / stage
                failed_output.mkdir()
                with patch.dict(sys.modules, {"torch": torch, "safetensors": safetensors,
                                              "safetensors.torch": safe_torch, "transformers": transformers}), \
                        patch.object(target, attribute, side_effect=ValueError("synthetic-private-marker")):
                    with self.assertRaises(preparation.PreparationFailure) as caught:
                        preparation.export_model(inputs, failed_output)
                self.assertEqual(caught.exception.stage, stage)
                self.assertEqual(str(caught.exception), preparation.FAILURE)

    def test_cli_suppresses_buffered_and_native_failure_output(self):
        code = (
            "import importlib.util, os, sys\n"
            "spec=importlib.util.spec_from_file_location('preparation', sys.argv[1])\n"
            "module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)\n"
            "def fail(*args):\n"
            " print('synthetic-private-marker', end='')\n"
            " os.write(2,b'synthetic-native-marker')\n"
            " raise ValueError('synthetic-exception-marker')\n"
            "module.prepare=fail\n"
            "raise SystemExit(module.main(['--destination',sys.argv[2],'--receipt',sys.argv[3]]))\n"
        )
        result = subprocess.run([sys.executable, "-c", code, str(SCRIPT),
                                 str(self.root / "model"), str(self.root / "receipt")],
                                capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "Offline model preparation failed\n")


if __name__ == "__main__":
    unittest.main()
