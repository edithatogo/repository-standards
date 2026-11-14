from __future__ import annotations

import copy
import unittest

import estate_evidence as evidence
import publish_estate_evidence as publisher
import test_estate_evidence as cases


class IssueAPI:
    def __init__(self, body):
        self.body = body
        self.writes = []

    def get(self, path):
        return evidence.Reply(200, {'body': self.body})

    def request(self, method, path, payload):
        self.writes.append((method, path, payload))
        self.body = payload['body']
        return evidence.Reply(200, {'body': self.body})


class PublishTests(unittest.TestCase):
    def test_same_report_updates_one_bounded_section_only_once(self):
        report = evidence.public_report(cases.PublicationTests().snapshot())
        api = IssueAPI('Preserve owner notes')
        self.assertTrue(publisher.publish(api, report, 16, cases.NOW))
        self.assertFalse(publisher.publish(api, report, 16, cases.NOW))
        self.assertEqual(len(api.writes), 1)
        self.assertTrue(api.body.startswith('Preserve owner notes'))
        self.assertEqual(api.body.count(evidence.START), 1)
        self.assertNotIn('very-private-project', api.body)

    def test_partial_or_stale_evidence_makes_no_issue_write(self):
        report = evidence.public_report(cases.PublicationTests().snapshot())
        for partial in (True, False):
            candidate = copy.deepcopy(report)
            if partial:
                candidate['inventory_complete_for_declared_scope'] = False
            else:
                candidate['expires_at'] = '2026-11-13T00:00:00Z'
            api = IssueAPI('Keep last accepted evidence')
            with self.assertRaises(evidence.EvidenceError):
                publisher.publish(api, candidate, 16, cases.NOW)
            self.assertEqual(api.body, 'Keep last accepted evidence')
            self.assertFalse(api.writes)


if __name__ == '__main__':
    unittest.main()
