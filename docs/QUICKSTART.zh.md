# Seedance 2.0 Skill OS 快速上手

> 版本 6.7.0 · 从安装到写出第一条「有导演意图」的提示词，只要 5 分钟。
> 完整文档见 [README](../README.md) 与 [中文指南](README.zh.md)。

## 一句话介绍

Seedance 2.0 Skill OS 是一个 agent skill：它像导演一样调度 Seedance 2.0，而不是靠堆形容词。准则只有一条——**导演模型，别去抠每一帧。** 你把这场戏「在做什么」说清楚，它就把这份意图编译成能直接用的提示词。

## 1. 安装一个根技能

下载并解压仓库，或运行：

```sh
git clone https://github.com/Emily2040/seedance-2.0.git
cd seedance-2.0
```

在这个目录中，选择**一个**安装位置。每个位置都会得到一个 `seedance-20/` 文件夹；不要分别安装子技能。

```sh
# Codex：当前用户可用
python scripts/install_codex_skill.py --client codex --scope user

# Claude Code：当前用户可用
python scripts/install_codex_skill.py --client claude-code --scope user

# Codex：仅用于一个已存在的项目，项目必须位于本源码目录之外
python scripts/install_codex_skill.py --client codex --scope project --project-root "/path/to/project"
```

将 `/path/to/project` 换成源码目录之外已存在的项目路径；含空格的路径要保留引号。这些命令在源码目录中运行。

本节中文修订由 AI 辅助起草，独立语言审核仍待完成：[审核状态](LANGUAGE_COVERAGE.md)。

其它客户端或自定义配置可用 `--dest /path/to/client/skills` 指定技能目录。不要将它与客户端、作用域选项混用。不传安装位置选项时，仍使用历史位置 `$CODEX_HOME/skills` 或 `~/.codex/skills`；显式选择用户作用域不会迁移或禁用旧副本。

用 doctor 检查**同一个安装位置**。例如，选择第一项后运行：

```sh
python scripts/install_doctor.py --client codex --scope user --json
```

`current` 表示已检查的安装文件与这份源码一致。重启或刷新客户端后，另行核对它发现的技能路径；doctor 不能证明客户端加载了哪个副本。只有明确要替换现有安装时才使用 `--force`，并先保存本地修改和一份独立备份。 [安装位置选项](https://github.com/Emily2040/seedance-2.0/blob/main/docs/INSTALL_SCOPES.md) · [迁移与重复安装](https://github.com/Emily2040/seedance-2.0/blob/main/docs/INSTALL_MIGRATION.md).

需要手动传输时，先用安装器的 `--dest /path/to/new-staging/skills` 在源码目录之外的新位置准备文件。**只复制生成的 `seedance-20/` 目录**，保留隐藏文件和安装完成记录。直接从 GitHub 导入时，客户端可能打包不同的文件；请核对导入内容，不要假定它采用了本安装器的允许清单。 [手动传输说明](https://github.com/Emily2040/seedance-2.0/blob/main/docs/MANUAL_INSTALL.md).

<details>
<summary>替换与恢复细节</summary>

切换期间，事务会保留临时备份。如果切换失败且所需记录仍然有效，安装器会将原来的完整副本回滚到原位。切换成功后，临时备份会移入隔离区并删除；它不能替代你单独保留的备份。自动恢复仅适用于通过验证的事务状态；无法验证的文件和记录会保留，等待检查。详见[完整恢复边界](../README.md#install)。

</details>

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
