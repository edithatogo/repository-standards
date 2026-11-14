"""Native GLiNER bundle contracts; synthetic bytes never qualify a real model."""
from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

OFFLINE = Path(__file__).resolve().parents[1] / "security/offline-ai"
sys.path.insert(0, str(OFFLINE))


class NativeModelTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="native-model-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "model"
        self.fixtures = json.loads((OFFLINE / "tests/fixtures/native_model.json").read_text())
        for name, value in self.fixtures.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value if isinstance(value, str) else json.dumps(value))
        self.contract = importlib.import_module("security.model_assets")

    def rewrite(self, name, mutate):
        path = self.root / name
        payload = json.loads(path.read_text())
        mutate(payload)
        path.write_text(json.dumps(payload))

    def rejected(self):
        with self.assertRaisesRegex(ValueError, "^Offline model bundle is invalid$"):
            self.contract.validate_model_bundle(self.root)

    def test_complete_native_bundle_accepts_real_config_name(self):
        self.assertFalse((self.root / "config.json").exists())
        self.contract.validate_model_bundle(self.root)

    def test_legacy_config_alias_cannot_replace_native_config(self):
        (self.root / "gliner_config.json").rename(self.root / "config.json")
        self.rejected()

    def test_every_native_component_is_required(self):
        for name in self.fixtures:
            with self.subTest(component=name):
                path = self.root / name
                original = path.read_bytes()
                path.unlink()
                self.rejected()
                path.write_bytes(original)

    def test_encoder_must_be_embedded_and_match_local_source(self):
        self.rewrite("gliner_config.json", lambda cfg: cfg.pop("encoder_config"))
        self.rejected()
        self.rewrite("gliner_config.json", lambda cfg: cfg.update(encoder_config={"model_type": "deberta-v2"}))
        self.rejected()

    def test_unqualified_architectures_and_auxiliary_models_are_rejected(self):
        original = (self.root / "gliner_config.json").read_text()
        for update in ({"model_name": "unreviewed/encoder"}, {"labels_encoder": "remote/model"},
                       {"labels_decoder": "remote/model"}, {"span_mode": "token_level"},
                       {"words_splitter_type": "spacy"}, {"model_type": "gliner_streaming_span"}):
            with self.subTest(update=update):
                self.rewrite("gliner_config.json", lambda cfg: cfg.update(update))
                self.rejected()
                (self.root / "gliner_config.json").write_text(original)

    def test_remote_code_and_external_tokenizer_paths_are_rejected(self):
        original = (self.root / "tokenizer_config.json").read_text()
        for update in ({"auto_map": {"AutoTokenizer": "remote.Code"}},
                       {"trust_remote_code": True}, {"tokenizer_class": "CustomTokenizer"},
                       {"tokenizer_file": "../private/tokenizer.json"},
                       {"vocab_file": "https://example.invalid/vocab"}):
            with self.subTest(update=update):
                self.rewrite("tokenizer_config.json", lambda cfg: cfg.update(update))
                self.rejected()
                (self.root / "tokenizer_config.json").write_text(original)

    def test_duplicate_config_keys_and_non_finite_json_are_rejected(self):
        for text in ('{"model_type": "gliner", "model_type": "gliner_uni_encoder_span"}',
                     '{"private-marker": NaN}', '{broken'):
            with self.subTest(text=text):
                (self.root / "gliner_config.json").write_text(text)
                self.rejected()

    def test_model_files_must_be_regular_unaliased_files(self):
        weights = self.root / "model.safetensors"
        original = weights.read_bytes()
        weights.unlink()
        outside = self.root.parent / "outside"
        outside.write_bytes(original)
        weights.symlink_to(outside)
        self.rejected()
        weights.unlink()
        os.link(outside, weights)
        self.rejected()

    def test_adapters_and_remote_python_are_not_bundle_components(self):
        for name in ("encoder/adapter_config.json", "custom_model.py"):
            with self.subTest(name=name):
                path = self.root / name
                path.write_text("synthetic-private-marker")
                self.rejected()
                path.unlink()

    def test_loader_selects_builtin_model_and_explicit_local_tokenizer(self):
        calls = {}

        class Tokenizer:
            @classmethod
            def from_pretrained(cls, path, **kwargs):
                calls["tokenizer"] = (path, kwargs)
                return object()

        class BuiltinSpan:
            @classmethod
            def _load_config(cls, path, **kwargs):
                return types.SimpleNamespace(model_name="microsoft/mdeberta-v3-base")

            @classmethod
            def _set_tokenizer_spec_tokens(cls, tokenizer):
                return tokenizer

            @classmethod
            def from_pretrained(cls, path, **kwargs):
                calls["model"] = (path, kwargs)
                calls["encoder"] = cls._load_config(Path(path) / "gliner_config.json").model_name
                cls._load_tokenizer(None, Path(path), local_files_only=True)
                return object()

        fake_model = types.ModuleType("gliner.model")
        fake_model.UniEncoderSpanGLiNER = BuiltinSpan
        fake_gliner = types.ModuleType("gliner")
        fake_transformers = types.ModuleType("transformers")
        fake_transformers.AutoTokenizer = Tokenizer
        with patch.dict(sys.modules, {"gliner": fake_gliner, "gliner.model": fake_model,
                                      "transformers": fake_transformers}), \
                patch.object(self.contract, "version", return_value="0.2.30"):
            self.contract.load_local_model(self.root)
        self.assertEqual(calls["encoder"], str(self.root / "encoder"))
        self.assertEqual(calls["model"][0], str(self.root))
        self.assertTrue(calls["model"][1]["local_files_only"])
        self.assertTrue(calls["model"][1]["strict"])
        self.assertEqual(calls["model"][1]["map_location"], "cpu")
        self.assertFalse(calls["model"][1]["token"])
        self.assertTrue(calls["tokenizer"][1]["local_files_only"])
        self.assertFalse(calls["tokenizer"][1]["trust_remote_code"])

    def test_unqualified_gliner_version_is_rejected_before_importing_model(self):
        with patch.object(self.contract, "version", return_value="0.2.29"):
            with self.assertRaisesRegex(ValueError, "^Offline model runtime is unavailable$"):
                self.contract.load_local_model(self.root)


if __name__ == "__main__":
    unittest.main()
