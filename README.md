# Balatro Coach · 小丑牌助手

Windows 中文桌面辅助器：查询 150 张基础小丑牌的玩法，在牌局变化时显示搭配、冲突、Boss 与商店提示。MIT 开源，Python + Tkinter，无需 API Key，EXE 无需安装 Python。

## 使用

下载 Release 中的 `BalatroCoach.exe`，双击启动。先在“实时教练”选择“演示局面”，可立即体验界面。到“150 张牌 · 套路库”搜索中英文名称或流派标签，也可加入手动牌组查看组合提示。

### 实时连接

1. 按 [Steamodded 官方 Windows 教程](https://docs.smods.dev/Installation/Installing%20Steamodded%20windows/) 安装 Lovely 与 Steamodded。建议先备份 `%APPDATA%/Balatro`。请自行了解模组对成就、存档与兼容性的影响。
2. 辅助器 → “连接与安装” → “安装桥接模组”。该按钮仅复制本项目的两个桥接文件，不会自动下载或安装第三方加载器。
3. 重启 Balatro，确认模组列表有 **Balatro Coach Bridge**，开始或继续一局。
4. 辅助器 → “实时教练” → “实时连接”。默认读取 `%APPDATA%/Balatro/balatro_coach_state.json`，也可更改路径。
5. 点击“悬浮提示”打开可移动、置顶的提示窗。游戏使用窗口或无边框模式；独占全屏可能盖住提示窗。

每 0.5 秒导出与刷新；超过 4 秒未更新会隐藏旧建议，显示断线提示。切换界面、后台降帧或游戏暂停可能延迟更新。

## 已实现

- 150 张基础小丑牌：中文、英文、关键词搜索，流派筛选，每张独立原创策略摘要。
- 当前小丑逐牌建议；照片 × 悬挂小丑、男爵 × 哑剧演员等组合提示；经济与弃牌条件冲突。
- 可见选牌的牌型分类，四指、捷径、模糊小丑的部分规则适配。
- Boss 对路线的影响、最后一手提醒、商店路线关联、现金与槽位提示。
- 手动组牌、演示局面、导入 JSON 快照、可自定义实时文件路径。
- 本地读取，不上传局面；不导出牌库顺序、随机数种子或背面牌内容；不自动出牌或购买。

## 范围与限制

这是一版规则型教练，不是求解器。不模拟完整计分、概率期望、最佳弃牌或所有小丑的动态能力；商店建议基于路线标签，未做全局优化。牌型判断不等于最终得分。自定义牌、特殊大数模组与复杂跨模组交互未完整支持。策略库针对基础 150 张小丑，新版本新增牌需补充。

本项目与 LocalThunk、Playstack 无隶属关系。Balatro 名称与卡牌名称属于其权利人。仓库不包含游戏源码、图片、音频或完整游戏效果文案；卡牌策略为本项目原创概述。

## 开发与构建

Windows，Python 3.13（包含 Tkinter）。运行源码仅依赖标准库：

```powershell
python app.py
python app.py --demo
python app.py --state "D:\custom\balatro_coach_state.json"
```

安装开发依赖、运行测试、生成单文件 EXE：

```powershell
./build.ps1
```

输出 `dist/BalatroCoach.exe`。程序使用 PyInstaller，首次启动需要解压内置资源。没有代码签名证书；发布校验和用于核对下载完整性。

### 验证

`python -m unittest discover -s tests -v` 测试所有策略记录、组合、Boss、商店限制、牌型、断线时间和无效输入。安装 `lupa` 后还会执行真实 Lua 导出器的契约测试，验证背面牌隔离、重复写入及错误不影响原更新函数。`python app.py --demo --smoke-test` 检查窗口启动与刷新。

Lua 契约测试使用模拟游戏对象；它不代替真实游戏内兼容性测试。项目当前处于 0.1.0 预发布阶段。

## 局面协议

UTF-8 JSON，`schema: 1`，`timestamp` 为 Unix 秒。核心字段 `in_run, ante, money, hands, discards, blind, jokers, hand, selected, shop, joker_limit`。卡牌通过原生 `key` 对应策略库；背面牌仅输出 `{ "hidden": true }`。写入使用临时文件和重命名，Windows 文件替换间隙由客户端下次刷新重试。

结构见 `bridge/main.lua`，规则见 `engine.py`，数据见 `data/jokers.json`。游戏资料与安装参考：[Steamodded G 对象文档](https://docs.smods.dev/Guides/G/)、[模组元数据规范](https://docs.smods.dev/API%20Documentation/Mod-Metadata/)。

欢迎通过 Issue 反馈具体牌局和规则差异；提交局面前请自行检查内容。
