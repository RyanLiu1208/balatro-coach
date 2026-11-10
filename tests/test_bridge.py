"""Integration contract: execute real Lua exporter with a mock visible game.
Optional developer dependency: lupa. Does not require the game or game assets.
"""
import json
import tempfile
import unittest
from pathlib import Path
from engine import validate_state, load_catalog, advise
try:
    from lupa import LuaRuntime
except ImportError:
    LuaRuntime=None

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipIf(LuaRuntime is None,'Install lupa to run the Lua bridge contract test')
class BridgeTests(unittest.TestCase):
    def test_real_exporter_visible_only(self):
        with tempfile.TemporaryDirectory() as d:
            lua=LuaRuntime(unpack_returned_tuples=True)
            lua.globals().save_dir=d.replace('\\','/')
            lua.execute('''
                Game={update=function(self,dt) return 42 end}
                love={filesystem={getSaveDirectory=function() return save_dir end}}
                G={STAGE=1,STAGES={RUN=1},STATE=1,VERSION='test',
                   GAME={dollars=20,current_round={hands_left=3,discards_left=2},
                   round_resets={ante=2},blind={config={blind={key='bl_plant'}},name='Plant',chips=1000}},
                   jokers={config={card_limit=5},cards={{config={center={key='j_photograph',set='Joker',name='Photo'}}}}},
                   hand={cards={{facing='back',base={id=14,suit='Hearts'}}},highlighted={}},
                   shop_jokers={cards={}}}
            ''')
            lua.execute((ROOT/'bridge/main.lua').read_text(encoding='utf-8'))
            lua.execute('assert(Game:update(0.6)==42)')
            p=Path(d)/'balatro_coach_state.json'
            s=validate_state(json.loads(p.read_text(encoding='utf-8')))
            self.assertEqual(s['hand'],[{'hidden':True}])
            self.assertEqual(s['jokers'][0]['key'],'j_photograph')
            self.assertIn('植物',str(advise(s,load_catalog(ROOT))))
            self.assertNotIn('deck',s)
            lua.execute('G.GAME.dollars=30; Game:update(0.6)')
            self.assertEqual(json.loads(p.read_text())['money'],30)

    def test_export_error_does_not_break_update(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('Game={update=function() return 7 end}; G={}; love={}')
        lua.execute((ROOT/'bridge/main.lua').read_text(encoding='utf-8'))
        self.assertEqual(lua.eval('function() return Game:update(1) end')(),7)
