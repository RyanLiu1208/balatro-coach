"""Pure, deterministic coaching rules. No hidden-card access or score simulation."""
import json
import math
import time
from pathlib import Path
from collections import Counter


def load_catalog(root):
    return {r['key']: r for r in json.loads((Path(root)/'data/jokers.json').read_text(encoding='utf-8'))}


def validate_state(s):
    if not isinstance(s, dict) or s.get('schema') != 1:
        raise ValueError('不支持的局面格式，需 schema=1')
    for field in ('jokers', 'hand', 'shop', 'selected'):
        if not isinstance(s.get(field, []), list) or len(s.get(field, [])) > 500:
            raise ValueError('局面列表无效：'+field)
        if any(not isinstance(c, dict) for c in s.get(field, [])):
            raise ValueError('卡牌格式无效：'+field)
    for field in ('money', 'ante', 'hands', 'discards', 'chips', 'target', 'timestamp'):
        value = s.get(field, 0)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('数值无效：'+field)
    if not isinstance(s.get('blind', {}), dict):
        raise ValueError('盲注格式无效')
    return s


def read_state(path, now=None):
    p = Path(path)
    if p.stat().st_size > 2_000_000:
        raise ValueError('局面文件过大')
    s = validate_state(json.loads(p.read_text(encoding='utf-8-sig')))
    age = max(0, (time.time() if now is None else now) - s.get('timestamp', 0))
    return s, age


def hand_type(cards, keys=()):
    """Classify selected cards only; no estimate of joker-adjusted final score."""
    if not cards:
        return '尚未选牌'
    ranks = Counter(c.get('rank', 0) for c in cards if c.get('enhancement') != 'm_stone')
    counts = sorted(ranks.values(), reverse=True)
    suits = Counter(('red' if c.get('suit') in ('Hearts', 'Diamonds') else 'black')
                    if 'j_smeared' in keys else c.get('suit')
                    for c in cards if c.get('enhancement') not in ('m_stone','m_wild'))
    wild = sum(c.get('enhancement') == 'm_wild' for c in cards)
    need = 4 if 'j_four_fingers' in keys else 5
    flush = max(suits.values(), default=0) + wild >= need
    rs = set(ranks)
    if 14 in rs:
        rs.add(1)
    run = 1
    straight = False
    prev = -99
    for rank in sorted(rs):
        run = run + 1 if 0 < rank-prev <= (2 if 'j_shortcut' in keys else 1) else 1
        if run >= need:
            straight = True
        prev = rank
    top = counts[0] if counts else 0
    if top >= 5: return '同花五条' if flush else '五条'
    if top >= 3 and len(counts)>1 and counts[1]>=2: return '同花葫芦' if flush else '葫芦'
    if straight and flush: return '同花顺'
    if top>=4: return '四条'
    if flush: return '同花'
    if straight: return '顺子'
    if top>=3: return '三条'
    if counts.count(2)>=2: return '两对'
    if top>=2: return '对子'
    return '高牌'


BOSS = {
    'bl_plant':'植物会削弱人头牌；照片、男爵与人头路线需要特别检查。',
    'bl_psychic':'灵媒要求每手出五张；小张数路线需改变出牌。',
    'bl_eye':'眼睛要求本回合牌型不重复；纸牌高手和重复牌型路线受限。',
    'bl_mouth':'嘴只允许一种牌型；第一手就确定主力牌型。',
    'bl_needle':'针只有一次出牌机会；最后一手效果可直接生效，但启动牌没有空间。',
    'bl_wall':'墙的目标分数较高；先检查筹码和乘倍率是否都已就位。',
    'bl_water':'水会移除弃牌次数；不要依赖弃牌启动。',
    'bl_manacle':'镣铐减少手牌；留K和钢铁路线的收益会下降。',
    'bl_mark':'印记将人头牌背面朝上；不要仅凭牌背猜点数。',
    'bl_flint':'燧石削减基础筹码和倍率；高等级牌型也需要额外支撑。',
    'bl_hook':'钩子会在出牌后随机弃牌；留手核心可能丢失。',
    'bl_arm':'手臂降低出牌牌型等级；长期主力牌型会受损。',
    'bl_tooth':'牙齿按打出的牌扣钱；低现金或存钱路线需留预算。',
    'bl_club':'梅花被削弱；换得分花色或解除Boss能力。',
    'bl_goad':'黑桃被削弱；箭头和黑桃倍率路线受限。',
    'bl_head':'红桃被削弱；血石路线受限。',
    'bl_window':'方块被削弱；方块经济与倍率路线受限。',
    'bl_wheel':'部分新抽牌可能背面朝上；提示不会读取未知点数。',
    'bl_house':'首批手牌背面朝上；先用弃牌改善可见信息。',
    'bl_fish':'出牌后新抽牌背面朝上；尽量利用已知的牌。',
    'bl_ox':'打指定牌型会失去金钱；先查看游戏内指定牌型。',
    'bl_serpent':'出牌和弃牌后只抽三张；少出牌张数有助于保留手牌。',
    'bl_pillar':'此前在本底注打过的牌被削弱；注意卡牌上的削弱标记。',
    'bl_final_leaf':'全部扑克牌被削弱，需出售一张小丑解除；提前选好牺牲槽。',
    'bl_final_bell':'有一张牌被强制选中；围绕它重新组织出牌。',
    'bl_final_heart':'小丑可能被随机削弱；每次出牌前重新检查核心。',
    'bl_final_acorn':'小丑位置被打乱且翻面；复制目标与乘倍率顺序可能变化。',
    'bl_final_vessel':'最终目标很高；优先落实稳定爆发，避免只追求成长。',
}


def advise(s, catalog):
    jokers = s.get('jokers', [])
    keys = {j.get('key') for j in jokers}
    tips = []
    def add(title, text, level='info'): tips.append((title, text, level))
    if not s.get('in_run', True):
        return [('等待牌局','已连接游戏；开始或继续一局后显示建议。','info')]
    selected=s.get('selected', [])
    if selected:
        known=[c for c in selected if not c.get('hidden')]
        label=hand_type(known,keys) if len(known)==len(selected) else '含背面牌，牌型未知'
        add('当前选牌 · '+label,'这里只判断可见牌型；增强、蜡封、概率和小丑结算可能改变最终得分。')
    blind=s.get('blind', {})
    if blind.get('key') in BOSS and not blind.get('disabled') and 'j_chicot' not in keys:
        add('Boss · '+blind.get('name',blind['key']),BOSS[blind['key']],'warn')
    money=s.get('money',0)
    if money<0: add('现金为负','先恢复现金流；负债会限制利息和存钱类小丑的收益。','warn')
    elif money<25 and 'j_vagabond' not in keys:
        add('保留经济','过关稳定时尽量保留每档 $5 的利息本金；默认上限常见为 $25，实际以优惠券和牌组为准。')
    hands=s.get('hands',0)
    if hands==1:
        add('最后一次出牌','先确认可以过关；杂技演员和黄昏现在可发挥末手收益。','warn')
    if {'j_banner','j_mystic_summit'}<=keys:
        add('条件冲突','旗帜需要保留弃牌，神秘之峰需要零弃牌；按当前缺筹码还是缺倍率选择。','warn')
    if 'j_burglar' in keys and keys & {'j_yorick','j_burnt','j_castle','j_hit_the_road'}:
        add('弃牌路线受限','窃贼会移除弃牌次数，当前的弃牌成长牌难以启动。','warn')
    if 'j_vagabond' in keys and keys & {'j_bull','j_bootstraps','j_to_the_moon'}:
        add('经济路线冲突','流浪者希望低现金，公牛、提靴带和登月希望储蓄；选择一个主方向。','warn')
    combos=[({'j_photograph','j_hanging_chad'},'照片 × 悬挂小丑','把人头牌放在第一张得分牌位置，重复触发照片。'),
            ({'j_baron','j_mime'},'男爵 × 哑剧演员','把K留在手里；优先钢铁K和红蜡封。'),
            ({'j_hack','j_wee'},'低点数成长','优先让2点牌参与得分并重触发，累积小小丑的筹码。'),
            ({'j_triboulet','j_sock_and_buskin'},'人头重触发','让K和Q参与得分，借重触发放大逐卡乘倍率。'),
            ({'j_hologram','j_dna'},'复制成长','每回合首手可单出关键增强牌，复制同时成长全息影像。')]
    for required,title,body in combos:
        if required<=keys: add(title,body,'good')
    for j in jokers:
        k=j.get('key'); row=catalog.get(k)
        if j.get('debuff'):
            add('被削弱 · '+j.get('name',k),'此牌当前可能无法生效，不能按正常套路依赖它。','warn')
        elif row:
            add(j.get('name') or row['name'],row['strategy'])
        else: add(j.get('name',k or '未知小丑'),'尚未收录此模组牌；请以游戏内说明为准。')
    if 'j_blueprint' in keys or 'j_brainstorm' in keys:
        add('复制位置检查','蓝图复制右侧，头脑风暴复制最左侧；需兼容且未被削弱。不同阶段可移动位置。')
    owned_tags={t for k in keys if k in catalog for t in catalog[k]['tags']}
    for card in s.get('shop',[]):
        row=catalog.get(card.get('key'))
        if not row: continue
        price=card.get('cost',0)
        shared=(owned_tags & set(row['tags']))-{'资源','成长','经济','加倍率','筹码','乘倍率','概率','消耗'}
        note='可考虑：与现有路线关联 '+ '、'.join(sorted(shared)) if shared else '需要结合当前缺口评估'
        if price>money: note='当前现金不足，避免为它放弃过关资源'
        elif s.get('joker_limit',5)<=len(jokers): note+='；槽位已满，购买前比较替换损失'
        add('商店 · '+row['name']+f'  ${price}',note+'。'+row['strategy'])
    if not jokers: add('建立得分骨架','先找稳定筹码和加倍率，再补成长与乘倍率；前期先确保过关。')
    return tips
