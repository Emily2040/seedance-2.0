# Seedance 2.0 Skill OS 快速上手

> 版本 6.6.0 · 从安装到写出第一条「有导演意图」的提示词，只要 5 分钟。
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

# 任意客户端，装到当前项目
python scripts/install_codex_skill.py --dest .claude/skills
```

脚本会打印安装位置。重启客户端后调用 `seedance-20`。只有在覆盖已有安装时才加 `--force`——它会先删掉旧副本。

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
中近景，平视；她放下信，双手静止，一记缓慢的推镜迎上来；柔和的窗光让脸保持素净；近乎无声，只有一声椅子的摩擦。
```

## 5. 两条省素材的铁律

- **参考标签一字不改**——`@Image1`、`@Video1`、`@Audio1`、`@图片1`、`@视频1`，绝不翻译、绝不改写。
- **别指望一次生成整段故事。** 先出 Clip 01，看它「实际」停在哪，再照真实的结尾写 Clip 02（`seedance-continuation`）。

## 6. 安全

- **内容安全：** 若点子里有受保护角色、明星、品牌、logo、歌曲，或真人的脸和声音，别换种语言把它藏起来——用 `seedance-copyright` 改写成原创、已授权或后期替代的版本。
- **agent 安全：** 本包**不联网、不上报任何数据**，脚本都是确定性的、离线跑。千万别把 API 密钥、账号 cookie 或私有素材粘进你不信任的 agent。详见 [SECURITY.md](../SECURITY.md)。

## 7. 想更进一步

- `references/directing-engine.md` — 读懂一场戏，锁定唯一意图（33 个完整类型示例）。
- `references/capability-map.md` — 顺着模型的强项、避开它的短板来设计。
- `references/api-workflow.md` — API、服务商、价格、模型 ID（都标了来源日期）。
- `references/examples-by-mode.md` — T2V、I2V、V2V、R2V、FLF2V、编辑、延长的示例。

---

其它语言：[English](QUICKSTART.md) · [日本語](QUICKSTART.ja.md) · [한국어](QUICKSTART.ko.md) · [Español](QUICKSTART.es.md) · [Русский](QUICKSTART.ru.md)
