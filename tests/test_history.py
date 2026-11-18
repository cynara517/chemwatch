import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import chemwatch
from scripts import discovery, timeseries


class HistoryTest(unittest.TestCase):
    def test_dedup_uses_earliest_publication_in_topic(self):
        template = {"kind":"dataset","family_id":"f","topics":["yield"],"date_source":"https://example.org/p"}
        editions = [dict(template,id=str(year),name=str(year),publication_year=year) for year in (2021,2014)]
        points=timeseries.publication_series(editions,"dataset","yield",2022)
        self.assertEqual((points[0]["year"], points[-1]["total"]), (2014,1))
        self.assertEqual(sum(p["annual"] for p in points),1)
        self.assertEqual(timeseries.publication_series(editions,"benchmark","yield",2022),[])

    def test_net_change_preserves_gap_and_correction(self):
        def release(year,count,version):
            return dict(version=version,date=year,total=count,url="https://example.org")
        rows=[release("2018-03-01",90,"a"),release("2018-08-01",100,"b"),release("2020-04-01",109,"c"),release("2021-02-02",105,"d")]
        self.assertEqual([p["annual"] for p in timeseries.chembl_years(rows)],[None,None,-4])
        self.assertEqual(timeseries.chembl_years(rows)[0]["total"],100)

    def test_parse_release_preserves_uk_dates_and_activities(self):
        row=timeseries.parse_release("prepared on 01/05/2026 contains:\n10 compounds\n22,100 activities\n","chembl_x","source")
        self.assertEqual((row["date"],row["total"]),("2026-05-01",22100))

    def test_materials_archive_reconciles_and_rejects_partial_totals(self):
        def response(url):
            return {"meta":{"total":2 if "2017" in url else 3 if "2018" in url else 5}}
        with patch.object(timeseries, "api_json", side_effect=response):
            points = timeseries.materials_series(2018)["points"]
            self.assertEqual([(p["annual"],p["total"]) for p in points],[(2,2),(3,5)])
        with patch.object(timeseries, "api_json", return_value={"meta":{"total":5}}):
            with self.assertRaisesRegex(ValueError,"reconcile"):
                timeseries.materials_series(2018)

    def test_csd_backfill_is_a_baseline(self):
        text="1923–1964 4,045\n1965 656 28\n1966 690 30\n"
        data=timeseries.parse_csd(text,1966,"source")
        self.assertEqual(data["points"][0]["total"],4701)
        self.assertEqual(data["points"][0]["annual"],656)
        with self.assertRaises(ValueError):
            timeseries.parse_csd(text.replace("1965 656 28",""),1966,"source")

    def test_data_card_changes_compare_repository_revision(self):
        response={"id":"company/data","sha":"a"*40,"lastModified":"2026-01-01"}
        with patch.object(chemwatch,"api_json",return_value=response):
            r=chemwatch.probe({"monitor":{"type":"huggingface","repo":"company/data"}})
        self.assertEqual(r["revision"],response["sha"])
        self.assertIn("datasets/company/data/commit/",r["url"])

    def test_crossref_retries_a_short_rate_limit(self):
        limited = HTTPError("https://api.crossref.org",429,"limited",{"Retry-After":"1"},None)
        with patch.object(discovery.time,"sleep"), patch.object(discovery,"api_json",side_effect=[limited, {"ok":1}]):
            self.assertEqual(discovery.crossref_json("https://api.crossref.org"),{"ok":1})

    def test_off_topic_candidates_and_failed_queries(self):
        self.assertFalse(discovery.relevant("erythromycin","robot grasp a tea cup"))
        self.assertTrue(discovery.relevant("erythromycin","fermentation batch dataset"))
        with patch.object(discovery,"api_json",side_effect=OSError("timeout")), self.assertRaises(OSError):
            discovery.search("papers","retrosynthesis")

    def test_published_series_agrees_with_catalog(self):
        catalog=json.loads((timeseries.DATA/"catalog.json").read_text())
        series=json.loads((timeseries.DATA/"timeseries.json").read_text())
        for kind, topics in series["publications"].items():
            for topic,points in topics.items():
                if not points:
                    continue
                expected=timeseries.publication_series(catalog["entries"],kind,topic,points[-1]["year"])
                self.assertEqual(points,expected)
