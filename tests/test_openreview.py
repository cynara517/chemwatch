import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts import openreview_source as source


class OpenReviewTest(unittest.TestCase):
    def setUp(self):
        self.note = {"id":"forum1","forum":"forum1","content":{"title":{"value":"Reaction yield and retrosynthesis"}},
                     "invitations":["ICLR.cc/2026/Conference/-/Submission"],
                     "cdate":1735689599000,"odate":1735689601000}

    def test_counts_submission_not_reply_or_import(self):
        item = source.normalize(self.note,"yield","reaction yield")
        self.assertEqual((item["date"],item["public_date"]),("2024-12-31","2025-01-01"))
        for change in [{"id":"reply1"},{"replyto":"forum1"},{"invitations":["dblp.org/-/record"]}]:
            self.assertIsNone(source.normalize({**self.note,**change},"yield","reaction yield"))

    def test_legacy_submission_preserves_venue_label(self):
        note = {**self.note, "invitations":[], "invitation":"Example/-/Blind_Submission",
                "content":{"title":"Advances in retrosynthesis", "venue":"Example Withdrawn Submission"}}
        row = source.normalize(note,"retrosynthesis","retrosynthesis")
        self.assertEqual(row["venue"],"Example Withdrawn Submission")

    def test_topics_and_api_versions_share_a_single_forum(self):
        with patch.object(source,"TERMS",{"retrosynthesis":["retrosynthesis"],"yield":["reaction yield"]}), patch.object(source,"query_notes",return_value=[self.note]):
            rows = source.collect()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["topics"],["retrosynthesis","yield"])

    def test_pagination_and_repeating_page(self):
        page1 = {"count":2,"notes":[self.note]}
        page2 = {"count":2,"notes":[{"id":"forum2"}]}
        with patch.object(source,"page_at",side_effect=[page1,page2]) as get:
            self.assertEqual(len(list(source.query_notes("term",source.ENDPOINTS[0]))),2)
            self.assertIn("offset=1",get.call_args.args[0])
        with patch.object(source,"page_at",side_effect=[page1,page1]), self.assertRaises(ValueError):
            list(source.query_notes("term",source.ENDPOINTS[0]))

    def test_respects_rate_limit_before_repeating_query(self):
        url="https://api2.openreview.net/notes/search"
        limited=HTTPError(url,429,"limited",{"Retry-After":"61"},None)
        with patch.object(source.time,"sleep") as sleep, patch.object(source,"api_json",side_effect=[limited,{"notes":[]}] ):
            self.assertEqual(source.page_at(url),{"notes":[]})
            self.assertEqual([call.args[0] for call in sleep.call_args_list],[3,61])

    def test_failed_refresh_preserves_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"snapshot.json"
            with patch.object(source,"collect",return_value=[{"forum":"known"}]):
                self.assertEqual(source.refresh(path),[])
            prior=json.loads(path.read_text())
            with patch.object(source,"collect",side_effect=OSError("offline")):
                self.assertTrue(source.refresh(path))
            failed=json.loads(path.read_text())
            self.assertEqual(failed["items"],prior["items"])
            self.assertEqual(failed["last_success"],prior["last_success"])
