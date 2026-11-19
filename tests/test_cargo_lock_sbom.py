import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

MODULE = Path(__file__).with_name("cargo_lock_sbom.py")
if not MODULE.exists():
    MODULE = Path(__file__).resolve().parents[1] / "scripts/cargo_lock_sbom.py"
spec = importlib.util.spec_from_file_location("cargo_lock_sbom", MODULE)
sbom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbom)

SOURCE = "a" * 40
LOCK = '''version = 4
[[package]]
name = "app"
version = "0.1.0"
dependencies = ["serde", "dupe 1.0.0", "dupe 2.0.0", "local"]
[[package]]
name = "serde"
version = "1.0.228"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
dependencies = ["dupe 2.0.0"]
[[package]]
name = "dupe"
version = "1.0.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
[[package]]
name = "dupe"
version = "2.0.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
[[package]]
name = "local"
version = "0.2.0"
'''


class CargoLockInventoryTests(unittest.TestCase):
    def generate(self, content=LOCK):
        return sbom.generate(content.encode(), "test", SOURCE)

    def test_exact_transitive_versions_graph_checksums_and_determinism(self):
        result = self.generate()
        self.assertEqual(result, self.generate())
        components = result["components"]
        self.assertEqual(len(components), 5)
        refs = {component["bom-ref"] for component in components}
        self.assertEqual(len(refs), 5)
        serde = next(component for component in components if component["name"] == "serde")
        self.assertEqual(serde["purl"], "pkg:cargo/serde@1.0.228")
        self.assertEqual(serde["hashes"][0]["content"], "a" * 64)
        local = next(component for component in components if component["name"] == "local")
        self.assertNotIn("purl", local)
        app = next(component for component in components if component["name"] == "app")
        graph = {item["ref"]: item["dependsOn"] for item in result["dependencies"]}
        self.assertEqual(len(graph[app["bom-ref"]]), 4)
        self.assertTrue(all(set(deps) <= refs for deps in graph.values()))
        metadata = {item["name"]: item["value"] for item in result["metadata"]["properties"]}
        self.assertEqual(metadata["repository-standards:lockfile-sha256"], hashlib.sha256(LOCK.encode()).hexdigest())
        self.assertIn("not binary composition", metadata["repository-standards:claim-boundary"])

    def test_missing_unknown_or_ambiguous_dependency_rejected(self):
        for old, new in [('"serde",', '"missing",'), ('"dupe 1.0.0",', '"dupe",'), ('"serde",', '"serde ^1.0",')]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                self.generate(LOCK.replace(old, new))

    def test_unresolved_versions_empty_unknown_and_metadata_only_rejected(self):
        for content in [LOCK.replace('version = "1.0.228"', 'version = "^1.0"'),
                        'version = 4\n', 'version = 5\n',
                        'version = 4\n[[package]]\nname="app"\nversion="0.1.0"\n']:
            with self.subTest(content=content[:50]), self.assertRaises(ValueError):
                self.generate(content)

    def test_missing_or_bad_checksum_rejected(self):
        for content in [LOCK.replace('checksum = "' + 'a' * 64 + '"', ''), LOCK.replace('a' * 64, 'not-a-hash')]:
            with self.assertRaises(ValueError):
                self.generate(content)

    def test_duplicate_identity_rejected(self):
        with self.assertRaises(ValueError):
            self.generate(LOCK + '\n[[package]]\nname="local"\nversion="0.2.0"\n')

    def test_git_source_and_registry_source_are_not_conflated(self):
        content = LOCK.replace('"serde",', '"serde 1.0.228 (registry+https://github.com/rust-lang/crates.io-index)",')
        content += '\n[[package]]\nname="serde"\nversion="1.0.228"\nsource="git+https://example.org/serde#' + 'b' * 40 + '"\n'
        result = self.generate(content)
        serdes = [item for item in result["components"] if item["name"] == "serde"]
        self.assertEqual(len({item["bom-ref"] for item in serdes}), 2)
        self.assertEqual(sum("purl" in item for item in serdes), 1)

    def test_other_registry_identity_is_qualified(self):
        result = self.generate(LOCK.replace(sbom.CRATES_IO, "sparse+https://example.org/index"))
        serde = next(item for item in result["components"] if item["name"] == "serde")
        self.assertEqual(serde["purl"], "pkg:cargo/serde@1.0.228?repository_url=https%3A%2F%2Fexample.org%2Findex")

    def test_exact_source_commit_required(self):
        for source in ["main", "v1.0.0", "", "a" * 39]:
            with self.assertRaises(ValueError):
                sbom.generate(LOCK.encode(), "test", source)


if __name__ == "__main__":
    unittest.main()
