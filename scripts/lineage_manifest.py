"""Bounded two-tier lineage candidate for synthetic staged bytes, not certification."""

import hashlib
import json
import re
from graphlib import CycleError, TopologicalSorter

from remediation_plan_contract import PlanError, path_inventory
from verify_receipt import ReceiptError, finite_float, strict_pairs


MAX_BYTES = 32 * 1024 * 1024
MAX_ROWS = 256
ALGORITHM = 'sha256-merkle-candidate-v1'


class LineageError(ValueError):
    """Fixed rejection reason."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, separators=(',', ':'), sort_keys=True, allow_nan=False).encode()


def hex_digest(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def closure_digest(rows):
    return digest(b'closure\0' + canonical(sorted((row['path'], row['sha256']) for row in rows)))


def registry_root(rows):
    triples = sorted((row['artifact_id'], row['raw_bytes_sha256'], row['extract_sha256']) for row in rows)
    nodes = [hashlib.sha256(b'leaf\0' + canonical(triple)).digest() for triple in triples]
    if not nodes:
        raise LineageError('empty_registry')
    while len(nodes) > 1:
        nodes = [hashlib.sha256(b'node\0' + nodes[i] + nodes[i + 1]).digest()
                 if i + 1 < len(nodes) else nodes[i] for i in range(0, len(nodes), 2)]
    return nodes[0].hex()


def inspect_manifest(raw, objects, *, expected_digest):
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= 1024 * 1024
            or not hex_digest(expected_digest) or digest(raw) != expected_digest):
        raise LineageError('manifest_identity')
    try:
        doc = json.loads(raw.decode('utf-8'), object_pairs_hook=strict_pairs,
                         parse_float=finite_float, parse_constant=finite_float)
    except (ReceiptError, ValueError, RecursionError):
        raise LineageError('invalid_manifest') from None
    if (not isinstance(doc, dict) or set(doc) != {'schema_version', 'algorithm', 'runner_files', 'artifacts',
            'runner_closure_sha256', 'evidence_registry_merkle_root'}
            or type(doc['schema_version']) is not int or doc['schema_version'] != 1
            or doc['algorithm'] != ALGORITHM):
        raise LineageError('invalid_manifest')
    closure, artifacts = doc['runner_files'], doc['artifacts']
    if any(not isinstance(rows, list) or not 0 < len(rows) <= MAX_ROWS for rows in (closure, artifacts)):
        raise LineageError('inventory_budget')
    expected = []
    graph = {}
    for row in closure:
        if not isinstance(row, dict) or set(row) != {'path', 'sha256'}:
            raise LineageError('invalid_closure')
        expected.append((row['path'], row['sha256']))
    for row in artifacts:
        if not isinstance(row, dict) or set(row) != {'artifact_id', 'raw_path', 'extract_path',
                'raw_bytes_sha256', 'extract_sha256', 'depends_on'}:
            raise LineageError('invalid_artifact')
        name, deps = row['artifact_id'], row['depends_on']
        if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', name)
                or name in graph or not isinstance(deps, list) or len(deps) > MAX_ROWS
                or any(not isinstance(d, str) for d in deps) or len(set(deps)) != len(deps)):
            raise LineageError('invalid_dependency')
        graph[name] = deps
        expected.extend(((row['raw_path'], row['raw_bytes_sha256']), (row['extract_path'], row['extract_sha256'])))
    if any(set(deps) - graph.keys() for deps in graph.values()):
        raise LineageError('unknown_dependency')
    try:
        tuple(TopologicalSorter(graph).static_order())
    except CycleError:
        raise LineageError('cyclic_dependency') from None
    paths = [path for path, _ in expected]
    try:
        path_inventory(paths)
    except PlanError:
        raise LineageError('path_collision_or_invalid') from None
    if (not isinstance(objects, dict) or set(objects) != set(paths)
            or any(not isinstance(data, bytes) for data in objects.values())
            or sum(map(len, objects.values())) > MAX_BYTES):
        raise LineageError('object_inventory')
    for path, pin in expected:
        if not hex_digest(pin) or digest(objects[path]) != pin or objects[path] == raw:
            raise LineageError('object_identity')
    runner, registry = closure_digest(closure), registry_root(artifacts)
    if doc['runner_closure_sha256'] != runner or doc['evidence_registry_merkle_root'] != registry:
        raise LineageError('root_mismatch')
    return {'runner_closure_sha256': runner, 'evidence_registry_merkle_root': registry,
            'manifest_sha256': expected_digest, 'objects_verified': len(objects),
            'provenance_verified': False, 'scientific_qualification': False, 'write_authorized': False}
