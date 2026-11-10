import json
import tempfile
import time
import unittest
from pathlib import Path
from engine import load_catalog, advise, hand_type, read_state, validate_state

ROOT=Path(__file__).resolve().parents[1]


class RulesTests(unittest.TestCase):
    def setUp(self):
        self.catalog=load_catalog(ROOT)
        self.s=dict(schema=1,timestamp=time.time(),money=20,hands=4,jokers=[],hand=[],shop=[],selected=[],blind={})

    def test_catalog_complete(self):
        self.assertEqual(len(self.catalog),150)
        self.assertTrue(all(r['strategy'] and r['name'] and r['tags'] for r in self.catalog.values()))

    def test_all_jokers_can_be_coached(self):
        self.s['jokers']=[dict(key=k) for k in self.catalog]
        self.assertGreaterEqual(len(advise(self.s,self.catalog)),150)

    def test_combo_and_boss(self):
        self.s.update(jokers=[dict(key='j_photograph'),dict(key='j_hanging_chad')],blind=dict(key='bl_plant'))
        tips=str(advise(self.s,self.catalog))
        self.assertIn('照片 × 悬挂小丑',tips);self.assertIn('植物',tips)

    def test_boss_disabled(self):
        self.s['blind']=dict(key='bl_plant',disabled=True)
        self.assertNotIn('植物',str(advise(self.s,self.catalog)))

    def test_unknown_mod_and_hidden(self):
        self.s.update(jokers=[dict(key='mod_unknown',name='Mod牌')],selected=[dict(hidden=True)])
        tips=str(advise(self.s,self.catalog))
        self.assertIn('尚未收录',tips);self.assertIn('牌型未知',tips)

    def test_money_and_slots(self):
        self.s.update(money=1,jokers=[dict(key='j_joker')],joker_limit=1,shop=[dict(key='j_blueprint',cost=10)])
        self.assertIn('现金不足',str(advise(self.s,self.catalog)))
        self.s['money']=20
        self.assertIn('槽位已满',str(advise(self.s,self.catalog)))

    def test_stale_and_malformed_state(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.json';p.write_text(json.dumps(self.s),encoding='utf-8')
            _,age=read_state(p,now=self.s['timestamp']+10);self.assertEqual(age,10)
            p.write_text('{broken',encoding='utf-8')
            with self.assertRaises(ValueError):read_state(p)

    def test_reject_bad_schema_and_nan(self):
        for bad in [dict(schema=2),dict(schema=1,jokers=[None]),dict(schema=1,money=float('nan'))]:
            with self.assertRaises(ValueError):validate_state(bad)

    def test_hand_types(self):
        def cards(ranks,suit='Hearts'):return [dict(rank=r,suit=suit) for r in ranks]
        self.assertEqual(hand_type(cards([14,2,3,4,5])),'同花顺')
        self.assertEqual(hand_type(cards([5,5,5,5,5])),'同花五条')
        self.assertEqual(hand_type(cards([4,4,4,2,2])),'同花葫芦')
        c=cards([14,3,5,7]);self.assertEqual(hand_type(c,{'j_four_fingers','j_shortcut'}),'同花顺')
        c=[dict(rank=2,suit='Hearts'),dict(rank=5,suit='Diamonds'),dict(rank=8,suit='Hearts'),dict(rank=10,suit='Diamonds'),dict(rank=13,suit='Hearts')]
        self.assertEqual(hand_type(c,{'j_smeared'}),'同花')

    def test_no_run(self):
        self.s['in_run']=False
        self.assertEqual(len(advise(self.s,self.catalog)),1)


if __name__=='__main__':unittest.main()
