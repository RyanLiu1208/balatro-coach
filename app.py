"""Balatro Coach: standalone Windows companion, standard-library runtime."""
import argparse
import json
import os
import shutil
import sys
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from engine import load_catalog, read_state, validate_state, advise

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
SAVE=Path(os.environ.get('APPDATA',Path.home()))/'Balatro'
BG='#101c23'; PANEL='#192a32'; FG='#e8f0ef'; MUTED='#94b1b6'; GREEN='#6ce3b5'; GOLD='#ffd17a'


def demo_state():
    return dict(schema=1,timestamp=time.time(),in_run=True,ante=4,money=18,hands=2,discards=3,
                chips=800,target=10000,joker_limit=5,blind=dict(key='bl_plant',name='植物',disabled=False),
                jokers=[dict(key=k) for k in ('j_photograph','j_hanging_chad','j_sock_and_buskin')],
                hand=[],selected=[dict(rank=13,suit='Hearts'),dict(rank=13,suit='Clubs')],
                shop=[dict(key='j_blueprint',cost=10),dict(key='j_baron',cost=8)])


class Coach(tk.Tk):
    def __init__(self,state_path=None):
        super().__init__()
        self.title('Balatro Coach · 小丑牌助手 0.1.0')
        self.geometry('1180x800'); self.minsize(900,620); self.configure(bg=BG)
        self.catalog=load_catalog(ROOT)
        self.state_path=tk.StringVar(value=str(state_path or SAVE/'balatro_coach_state.json'))
        self.mode=tk.StringVar(value='实时连接'); self.search=tk.StringVar(); self.tag=tk.StringVar(value='全部流派')
        self.pin=tk.BooleanVar(value=False); self.status=tk.StringVar(value='等待连接')
        self.metrics=tk.StringVar(value='底注 —     金钱 —     出牌 —     弃牌 —')
        self.last_signature=None; self.overlay=None; self.last_tips=[]
        self.manual=[]; self.current_key=None; self.manual_money=tk.IntVar(value=20)
        style=ttk.Style(self); style.theme_use('clam')
        style.configure('.',font=('Microsoft YaHei UI',10),background=BG,foreground=FG)
        style.configure('TFrame',background=BG); style.configure('TLabel',background=BG,foreground=FG)
        style.configure('TButton',background=PANEL,foreground=FG,padding=(12,8),borderwidth=0)
        style.map('TButton',background=[('active','#29424c')])
        style.configure('TNotebook',background=BG,borderwidth=0)
        style.configure('TNotebook.Tab',padding=(22,12),background=PANEL,foreground=MUTED)
        style.map('TNotebook.Tab',background=[('selected',BG)],foreground=[('selected',GREEN)])
        style.configure('TEntry',fieldbackground=PANEL,foreground=FG,padding=8)
        style.configure('TCombobox',fieldbackground=PANEL,foreground=FG,padding=6)
        style.map('TCombobox',fieldbackground=[('readonly',PANEL)],foreground=[('readonly',FG)])
        head=ttk.Frame(self,padding=(26,20));head.pack(fill='x')
        ttk.Label(head,text='BALATRO / COACH',font=('Segoe UI',23,'bold'),foreground=GREEN).pack(side='left')
        ttk.Checkbutton(head,text='窗口置顶',variable=self.pin,command=lambda:self.attributes('-topmost',self.pin.get())).pack(side='right')
        ttk.Button(head,text='悬浮提示',command=self.toggle_overlay).pack(side='right',padx=16)
        ttk.Label(self,text='看懂每张牌，找到下一步。',foreground=MUTED,padding=(27,0,0,14)).pack(anchor='w')
        tabs=ttk.Notebook(self);tabs.pack(fill='both',expand=True,padx=24,pady=(0,18))
        live=ttk.Frame(tabs,padding=16); library=ttk.Frame(tabs,padding=16); setup=ttk.Frame(tabs,padding=22)
        tabs.add(live,text='实时教练');tabs.add(library,text='150 张牌 · 套路库');tabs.add(setup,text='连接与安装')
        bar=ttk.Frame(live);bar.pack(fill='x')
        ttk.Combobox(bar,textvariable=self.mode,values=['实时连接','演示局面','手动组牌'],state='readonly',width=12).pack(side='left')
        ttk.Label(bar,textvariable=self.status,foreground=GREEN).pack(side='left',padx=18)
        ttk.Button(bar,text='导入局面 JSON',command=self.import_state).pack(side='right')
        ttk.Label(live,textvariable=self.metrics,font=('Microsoft YaHei UI',15,'bold'),padding=(0,22)).pack(anchor='w')
        self.live_text=self.textbox(live)
        ttk.Label(live,text='规则提示仅供决策参考 · 不计算完整结算分数 · 背面牌不读取 · 支持窗口化/无边框游戏',foreground=MUTED,padding=(0,12)).pack(anchor='w')
        filters=ttk.Frame(library);filters.pack(fill='x',pady=(0,14))
        ttk.Entry(filters,textvariable=self.search,width=36).pack(side='left')
        ttk.Label(filters,text='  搜索中文 / 英文 / 关键词',foreground=MUTED).pack(side='left')
        tags=sorted({t for r in self.catalog.values() for t in r['tags']})
        ttk.Combobox(filters,textvariable=self.tag,values=['全部流派']+tags,state='readonly',width=13).pack(side='right')
        split=ttk.Panedwindow(library,orient='horizontal');split.pack(fill='both',expand=True)
        left=ttk.Frame(split); right=ttk.Frame(split,padding=(20,0));split.add(left,weight=2);split.add(right,weight=3)
        self.cards=tk.Listbox(left,bg=PANEL,fg=FG,selectbackground='#326254',selectforeground=FG,borderwidth=0,highlightthickness=0,font=('Microsoft YaHei UI',11),activestyle='none')
        scroll=ttk.Scrollbar(left,command=self.cards.yview);scroll.pack(side='right',fill='y');self.cards.configure(yscrollcommand=scroll.set);self.cards.pack(fill='both',expand=True)
        self.detail=self.textbox(right)
        ttk.Button(right,text='＋ 加入手动牌组',command=self.add_manual).pack(fill='x',pady=(10,4))
        ttk.Button(right,text='清空手动牌组',command=self.clear_manual).pack(fill='x')
        ttk.Label(right,text='手动模式只根据已选小丑给建议，不读取游戏。',foreground=MUTED,wraplength=380).pack(pady=10)
        self.cards.bind('<<ListboxSelect>>',self.select_card)
        self.search.trace_add('write',lambda *_:self.filter_cards());self.tag.trace_add('write',lambda *_:self.filter_cards())
        self.mode.trace_add('write',lambda *_:setattr(self,'last_signature',None))
        ttk.Label(setup,text='连接本地牌局',font=('Microsoft YaHei UI',19,'bold')).pack(anchor='w',pady=(0,18))
        info=('1. 先安装 Lovely 与 Steamodded（点击下方官方教程）。\n'
              '2. 点击“安装桥接模组”，把本项目的桥接文件复制到 Mods 目录。\n'
              '3. 重启小丑牌，开始或继续一局，再选择“实时连接”。\n\n'
              '桥接每 0.5 秒导出可见局面。辅助器只读本机 JSON，不上传牌局。\n'
              '若游戏安装了其他模组，新增小丑暂未收录；完整分数预测不在此版本内。\n'
              '模组对成就、存档及兼容性的影响请参阅 Steamodded 文档，建议先备份存档。')
        ttk.Label(setup,text=info,foreground=MUTED,justify='left',wraplength=940).pack(anchor='w')
        actions=ttk.Frame(setup);actions.pack(fill='x',pady=22)
        ttk.Button(actions,text='安装桥接模组',command=self.install_bridge).pack(side='left')
        ttk.Button(actions,text='官方安装教程',command=lambda:webbrowser.open('https://docs.smods.dev/Installation/Installing%20Steamodded%20windows/')).pack(side='left',padx=12)
        ttk.Button(actions,text='打开存档文件夹',command=self.open_save).pack(side='left')
        ttk.Label(setup,text='局面文件路径（支持自定义存档位置）').pack(anchor='w',pady=(10,8))
        ttk.Entry(setup,textvariable=self.state_path).pack(fill='x')
        ttk.Button(setup,text='选择局面文件',command=self.pick_path).pack(anchor='w',pady=10)
        ttk.Label(setup,text='离线体验：实时教练 → 演示局面\n组牌实验：套路库 → 加入手动牌组 → 实时教练',foreground=GOLD).pack(anchor='w',pady=18)
        self.filter_cards();self.after(100,self.tick)

    def textbox(self,parent):
        box=tk.Text(parent,bg=PANEL,fg=FG,insertbackground=FG,borderwidth=0,highlightthickness=0,wrap='word',height=4,padx=20,pady=18,font=('Microsoft YaHei UI',11),spacing1=5,spacing3=9)
        scroll=ttk.Scrollbar(parent,command=box.yview);scroll.pack(side='right',fill='y');box.configure(yscrollcommand=scroll.set)
        box.pack(fill='both',expand=True)
        for tag,color in [('title',GREEN),('warn',GOLD),('good',GREEN),('muted',MUTED)]: box.tag_configure(tag,foreground=color,font=('Microsoft YaHei UI',12,'bold') if tag!='muted' else ('Microsoft YaHei UI',10))
        box.configure(state='disabled');return box

    def render(self,box,blocks):
        y=box.yview()[0];box.configure(state='normal');box.delete('1.0','end')
        for title,body,level in blocks:
            box.insert('end',title+'\n',level if level in ('warn','good') else 'title');box.insert('end',body+'\n\n')
        box.configure(state='disabled');box.yview_moveto(y)

    def filter_cards(self):
        q=self.search.get().strip().lower();tag=self.tag.get()
        self.filtered=[r for r in self.catalog.values() if (tag=='全部流派' or tag in r['tags']) and q in (r['name']+' '+r['english']+' '+r['key']+' '+r['strategy']+' '.join(r['tags'])).lower()]
        self.cards.delete(0,'end')
        for r in self.filtered:self.cards.insert('end',r['name']+'  /  '+r['english'])
        if self.filtered:self.cards.selection_set(0);self.select_card()
        else:self.current_key=None;self.render(self.detail,[('没有匹配的牌','试试“重触发”“经济”“同花”或英文名称。','info')])

    def select_card(self,event=None):
        selection=self.cards.curselection()
        if not selection:return
        r=self.filtered[selection[0]];self.current_key=r['key']
        self.render(self.detail,[(r['name'],r['english']+'  ·  '+r['key'],'info'),('路线标签',' / '.join(r['tags']),'info'),('怎么围绕它打',r['strategy'],'info'),('决策提示','优先考虑当前能否过关，再比较成长空间、槽位与经济成本。此库为原创策略摘要；具体数值与动态条件以游戏内说明为准。','muted')])

    def add_manual(self):
        if self.current_key:
            self.manual.append(dict(key=self.current_key));self.mode.set('手动组牌');self.status.set(f'手动牌组已有 {len(self.manual)} 张，切到实时教练查看')

    def clear_manual(self):self.manual=[];self.last_signature=None

    def import_state(self):
        path=filedialog.askopenfilename(filetypes=[('局面 JSON','*.json')])
        if path:
            try:
                s,_=read_state(path);self.imported=s;self.mode.set('导入快照');self.last_signature=None
            except (OSError,ValueError) as e:messagebox.showerror('无法读取',str(e))

    def pick_path(self):
        p=filedialog.askopenfilename(filetypes=[('局面 JSON','*.json')])
        if p:self.state_path.set(p);self.last_signature=None

    def install_bridge(self):
        target=SAVE/'Mods'/'BalatroCoachBridge'
        try:
            target.mkdir(parents=True,exist_ok=True)
            for name in ('main.lua','BalatroCoachBridge.json'):shutil.copy2(ROOT/'bridge'/name,target/name)
            messagebox.showinfo('桥接模组已安装','已复制到：'+str(target)+'\n需要 Lovely 和 Steamodded；安装后重启游戏。')
        except OSError as e:messagebox.showerror('安装失败',str(e))

    def open_save(self):
        SAVE.mkdir(parents=True,exist_ok=True)
        if os.name=='nt':os.startfile(SAVE)

    def toggle_overlay(self):
        if self.overlay and self.overlay.winfo_exists():self.overlay.destroy();self.overlay=None;return
        self.overlay=tk.Toplevel(self);self.overlay.title('Coach · 实时提示');self.overlay.geometry('420x520');self.overlay.configure(bg=BG);self.overlay.attributes('-topmost',True)
        self.overlay_status=ttk.Label(self.overlay,textvariable=self.status,padding=12);self.overlay_status.pack(fill='x')
        self.overlay_text=self.textbox(self.overlay);self.render(self.overlay_text,self.last_tips)

    def tick(self):
        try:
            mode=self.mode.get()
            if mode=='演示局面':s=demo_state();status='● 演示数据 · 非当前游戏'
            elif mode=='手动组牌':s=demo_state();s.update(jokers=self.manual,shop=[],selected=[],blind={},money=20,hands=4);status='● 手动组牌 · 非当前游戏'
            elif mode=='导入快照':s=self.imported;status='● 导入快照 · 非实时'
            else:
                s,age=read_state(self.state_path.get())
                if age>4:
                    self.show_wait(f'连接已中断 · {int(age)} 秒未更新','请检查游戏是否仍在运行、模组是否加载。旧局面建议已隐藏。');return
                status='● 已连接游戏 · 每 0.5 秒刷新'
            self.status.set(status)
            self.metrics.set(f"底注 {s.get('ante',0)}     $ {s.get('money',0)}     出牌 {s.get('hands',0)}     弃牌 {s.get('discards',0)}")
            signature=json.dumps({k:v for k,v in s.items() if k!='timestamp'},ensure_ascii=False,sort_keys=True)+mode
            if signature!=self.last_signature:
                self.last_signature=signature;self.last_tips=advise(s,self.catalog);self.render(self.live_text,self.last_tips)
                if self.overlay and self.overlay.winfo_exists():self.render(self.overlay_text,self.last_tips)
        except FileNotFoundError:self.show_wait('等待游戏连接','尚未找到局面文件。请在“连接与安装”安装桥接模组与前置依赖，并重启游戏。也可选择“演示局面”体验。')
        except (OSError,ValueError,TypeError,KeyError) as e:self.show_wait('局面暂不可用',str(e)+'\n将自动重试。')
        finally:self.after(500,self.tick)

    def show_wait(self,status,body):
        self.status.set(status);self.metrics.set('底注 —     金钱 —     出牌 —     弃牌 —')
        if self.last_signature!=status+body:
            self.last_signature=status+body;self.last_tips=[(status,body,'warn')];self.render(self.live_text,self.last_tips)
            if self.overlay and self.overlay.winfo_exists():self.render(self.overlay_text,self.last_tips)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--state');parser.add_argument('--demo',action='store_true');parser.add_argument('--smoke-test',action='store_true');args=parser.parse_args()
    app=Coach(args.state)
    if args.demo:app.mode.set('演示局面')
    if args.smoke_test:app.after(1800,app.destroy)
    app.mainloop()

if __name__=='__main__':main()
