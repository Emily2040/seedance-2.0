# Seedance 2.0 Skill OS 快速上手

> 版本 6.7.0 · 从安装到写出第一条「有导演意图」的提示词，只要 5 分钟。
> 完整文档见 [README](../README.md) 与 [中文指南](README.zh.md)。

## 一句话介绍

Seedance 2.0 Skill OS 是一个 agent skill：它像导演一样调度 Seedance 2.0，而不是靠堆形容词。准则只有一条——**导演模型，别去抠每一帧。** 你把这场戏「在做什么」说清楚，它就把这份意图编译成能直接用的提示词。

## 1. 安装（约 5 分钟）

把整个仓库当作**一个**名为 `seedance-20` 的根技能来装；子技能和参考资料会按相对路径自动加载。

**第一步：先把文件拿到本地。** 下面每条命令都要在仓库目录里运行：

```bash
git clone https://github.com/Emily2040/seedance-2.0.git
cd seedance-2.0
```

没装 `git` 就用仓库页面的 **Code → Download ZIP**，解压后 `cd` 进去。

**第二步：安装。** 这个脚本不只支持 Codex；用 `--dest` 指定你的客户端扫描的 skills 目录即可：

```bash
# Codex（默认 ~/.codex/skills）
python scripts/install_codex_skill.py

# Claude Code（个人安装，所有项目可用）
python scripts/install_codex_skill.py --dest ~/.claude/skills

# 装到另一个项目里——请在那个项目目录下运行
python /path/to/seedance-2.0/scripts/install_codex_skill.py --dest .claude/skills
```

脚本会打印安装位置。重启客户端后调用 `seedance-20`。只有在替换一份完整的现有安装时才加 `--force`；不完整的受管安装会自动修复。新副本会先在暂存区完成复制和校验。切换时，旧的完整副本会作为与本次事务绑定的备份保留；若切换失败，安装器会将它回滚到原位。只有新副本成功切换为正式安装后，旧备份才会被移入隔离区并安全删除。目标目录若在本仓库内部会被直接拒绝：把源码树复制进它自己会一路递归，直到路径过长而失败。

**从 GitHub 安装（客户端支持仓库地址时）**

```text
https://github.com/Emily2040/seedance-2.0
```

**手动复制（其它客户端）**

把整个文件夹复制进客户端的技能目录，名字保持 `seedance-20`。常见位置见 [README 安装表](../README.md#install)（请以自己客户端为准，并非通用保证）：如 Claude Code `.claude/skills/`、Cursor `.cursor/skills/`、GitHub Copilot `.github/skills/`、Windsurf `.windsurf/skills/`。

> 安全第一：只装进你信得过的 agent。在陌生或第三方 agent 里使用前，先读一遍 [SECURITY.md](../SECURITY.md)。

## 2. 对号入座，挑一个技能

| 你手上是… | 先加载 |
|---|---|
| 一个还很模糊的念头 | `seedance-interview` |
| 一个想清楚的场景 | `seedance-prompt` |
| 一段要分好几条拍的剧情 | `seedance-sequence` |
| 已定稿、要往下接的片段 | `seedance-continuation` |
| 效果差或被拦下的结果 | `seedance-troubleshoot` |
| 牵涉角色、品牌、明星或真人 | `seedance-copyright` |

## 3. 动笔前，先当导演——问自己四个问题

1. **这场戏在做什么？** 是转折、是揭示、是一种情绪，还是一次展示？
2. **镜头怎么把它说出来？** 远景写孤独，特写看表情，推镜带出恍然大悟。
3. **光帮你做什么？** 时辰、软硬、冷暖——都得为这份意图服务。
4. **声音在做什么？** 近乎无声、一处环境音，或是一句台词。

## 4. 一个对照

**堆料（弱）**

```
史诗级电影感镜头，一个女人在读信，很有情绪，光影很美，4K
```

**导演（强）**

```
一位穿羊毛开衫的女人坐在厨房餐桌前，读着一张信纸。她的目光在同一行上走了两遍，随后双手把信纸放到桌面，彻底静止。镜头保持平视中近景，缓慢推近，在她双手停住时停下。左侧阴天窗光压平她的脸，不做补光。声音：室内底噪，一声椅子摩擦，随后近乎无声。
```

要看的是**顺序**，不只是词。主体和她正在做的事排在**最前面**，镜头、光、声音跟在后面——因为提示词的开头正是模型锁定「这场戏是谁的」的位置。以 `中近景，平视` 开头，等于把这个位置花在了取景参数上，让模型事后再去推断主体。同样的手艺，层级更弱。

长度同理：写成一份紧凑的拍摄简报，够交代主体、动作、镜头、光和声音即可。中文按**字数**计，不按词数（见 `vocab/zh`）。太短，模型替你补空白；太长，后面的句子就落不到画面上。

## 5. 两条省素材的铁律

- **参考标签一字不改**——`@Image1`、`@Video1`、`@Audio1`、`@图片1`、`@视频1`，绝不翻译、绝不改写。
- **别指望一次生成整段故事。** 先出 Clip 01，看它「实际」停在哪，再照真实的结尾写 Clip 02（`seedance-continuation`）。

## 6. 安全

- **内容安全：** 若点子里有受保护角色、明星、品牌、logo、歌曲，或真人的脸和声音，别换种语言把它藏起来——用 `seedance-copyright` 改写成原创、已授权或后期替代的版本。
- **agent 安全：** **安装后的内容**不联网、不上报任何数据；安装进去的脚本都在本地运行，不连接外部服务。仓库工作副本里另外包含开发专用的 `scripts/eval_run.py`，它可以连接模型服务商，但安装器会排除它。千万别把 API 密钥、账号 cookie 或私有素材粘进你不信任的 agent。详见 [SECURITY.md](../SECURITY.md)。

## 7. 想更进一步

- `references/directing-engine.md` — 读懂一场戏，锁定唯一意图（33 个完整类型示例）。
- `references/capability-map.md` — 顺着模型的强项、避开它的短板来设计。
- `references/api-workflow.md` — API、服务商、价格、模型 ID（都标了来源日期）。
- `references/examples-by-mode.md` — T2V、I2V、V2V、R2V、FLF2V、编辑、延长的示例。

---

其它语言：[English](QUICKSTART.md) · [日本語](QUICKSTART.ja.md) · [한국어](QUICKSTART.ko.md) · [Español](QUICKSTART.es.md) · [Русский](QUICKSTART.ru.md)
