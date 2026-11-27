import hashlib
import json
import unittest

import lineage_manifest as lineage


def digest(value):
    return hashlib.sha256(value).hexdigest()


def fixture():
    objects = {'runner/parser.py': b'parser', 'raw/a.csv': b'raw a', 'extract/a.csv': b'extract a',
               'raw/b.csv': b'raw b', 'extract/b.csv': b'extract b'}
    closure = [{'path': 'runner/parser.py', 'sha256': digest(objects['runner/parser.py'])}]
    rows = [{'artifact_id': item, 'raw_path': f'raw/{item}.csv', 'extract_path': f'extract/{item}.csv',
             'raw_bytes_sha256': digest(objects[f'raw/{item}.csv']),
             'extract_sha256': digest(objects[f'extract/{item}.csv']),
             'depends_on': ['a'] if item == 'b' else []} for item in ('a', 'b')]
    document = dict(schema_version=1, algorithm='sha256-merkle-candidate-v1',
                    runner_files=closure, artifacts=rows,
                    runner_closure_sha256=lineage.closure_digest(closure),
                    evidence_registry_merkle_root=lineage.registry_root(rows))
    return document, objects


class LineageTests(unittest.TestCase):
    def check(self, doc, objects, expected=None):
        raw = json.dumps(doc, separators=(',', ':')).encode()
        return lineage.inspect_manifest(raw, objects, expected_digest=expected or digest(raw))

    def test_reordered_registry_reproduces_root_but_not_manifest_digest(self):
        doc, objects = fixture()
        original = self.check(doc, objects)
        doc['artifacts'].reverse()
        result = self.check(doc, objects)
        self.assertEqual(result['evidence_registry_merkle_root'], original['evidence_registry_merkle_root'])
        self.assertFalse(result['provenance_verified'])
        self.assertFalse(result['scientific_qualification'])

    def test_raw_extract_or_runner_tampering_and_missing_objects_fail(self):
        doc, objects = fixture()
        for path in ('raw/a.csv', 'extract/a.csv', 'runner/parser.py'):
            with self.subTest(path=path), self.assertRaises(lineage.LineageError):
                self.check(doc, dict(objects, **{path: b'tampered'}))
        del objects['raw/a.csv']
        with self.assertRaises(lineage.LineageError):
            self.check(doc, objects)

    def test_self_reference_dependency_cycle_and_unknown_dependency_fail(self):
        for dep in ('b', 'a', 'missing'):
            doc, objects = fixture()
            doc['artifacts'][0]['depends_on'] = [dep]
            with self.subTest(dep=dep), self.assertRaises(lineage.LineageError):
                self.check(doc, objects)

    def test_manifest_substitution_requires_independent_digest(self):
        doc, objects = fixture()
        expected = digest(json.dumps(doc, separators=(',', ':')).encode())
        doc['artifacts'][1]['depends_on'] = []
        with self.assertRaises(lineage.LineageError):
            self.check(doc, objects, expected)

    def test_cross_tier_alias_and_unlisted_object_fail(self):
        doc, objects = fixture()
        with self.assertRaises(lineage.LineageError):
            self.check(doc, dict(objects, **{'extra.txt': b'unknown'}))
        doc['artifacts'][0]['raw_path'] = 'runner/parser.py'
        with self.assertRaises(lineage.LineageError):
            self.check(doc, objects)
