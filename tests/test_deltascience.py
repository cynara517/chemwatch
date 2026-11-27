import json
import unittest
from unittest.mock import patch
import chemwatch as cw


def row(code, group='化学', title='A title'):
    fields = dict(code=code, group=group, discipline='计算化学', author='', organization='', focus='模拟', title=title)
    return '{'+','.join(k+':'+json.dumps(v,ensure_ascii=False) for k,v in fields.items())+',position:1}'


class DeltaScienceTests(unittest.TestCase):
    def test_primary_category_and_escaped_titles(self):
        items, total = cw.parse_deltascience('const renamed=['+row('C-1',title='A "quoted" title')+','+row('P-1','物理学')+'];')
        self.assertEqual(total,2)
        self.assertEqual([i['id'] for i in items],['C-1'])
        self.assertEqual(items[0]['title'],'A "quoted" title')
        self.assertEqual(items[0]['url'],'https://deltascience.bohrium.com/questions/C-1')

    def test_changed_schema_and_duplicates_fail_closed(self):
        for body in ['', row('C-1')+','+row('C-2').replace('position:1','position:null'), row('C-1')+','+row('C-1'),row('P-1','物理学')]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                cw.parse_deltascience('const table=['+body+'];')

    def test_revision_tracks_tasks_not_bundle_name_or_order(self):
        def run(asset, rows):
            with patch.object(cw,'fetch_public_text',side_effect=[f'<script src="/assets/{asset}.js"></script>', 'const x=['+','.join(rows)+'];']):
                return cw.probe({'monitor':{'type':'deltascience'}})
        first=run('a',[row('C-1'),row('C-2')])
        self.assertEqual(first['revision'],run('b',[row('C-2'),row('C-1')])['revision'])
        self.assertNotEqual(first['revision'],run('b',[row('C-1',title='Revised'),row('C-2')])['revision'])
        self.assertNotEqual(first['revision'],run('b',[row('C-1')])['revision'])

    def test_unexpected_external_script_is_not_fetched(self):
        with patch.object(cw,'fetch_public_text',return_value='<script src="https://other.example/app.js"></script>') as fetch:
            with self.assertRaises(ValueError):cw.probe_deltascience()
            self.assertEqual(fetch.call_count,1)
