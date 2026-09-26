# Evidence notes: Seedance 2.0 prompt structure and series work

Compiled 2026-09-26 from two research passes (repository readers, official
ByteDance and Volcengine material, GitHub short-drama repositories, and the
community claims the maintainer asked to have checked). The passes were cut
short on purpose: broad social sweeps were stopped once the official layer
was in hand, and only four claims received an adversarial recheck. Every row
below states which of those it is.

Access note: `www.volcengine.com` and `docs.byteplus.com` are refused by this
environment's egress policy. Official quotes therefore come from two kinds of
mirror: third-party copies of the official PDFs that record the PDF's SHA-256
against the Volcengine document IDs (82379/2222480, 82379/2607689,
82379/1520757, 82379/2291680), and ByteDance's own GitHub organisation
(`bytedance/agentkit-samples`, author `volcengine/support`). Before any of
these quotes changes skill text, recheck the live page, as
`references/source-registry.md` already requires.

## A. What official material says (tier: official, via mirror unless noted)

| Topic | Official statement (quoted) | Source |
|---|---|---|
| Multi-shot structure | 使用镜头1、镜头2、镜头3等标识，按事件发生顺序（先主后次）组织内容。不强制限制每段时长，优先让模型根据剧情自然生成节奏。 | Volcengine 2.0 prompt guide, doc 82379/2222480 ([mirror](https://raw.githubusercontent.com/Jdaroro/awesome-seedance-2x-prompts/078d4d244a7b22b46156358f5afcb5fce3b4077d/docs/official-pdfs/zh-CN/%E7%81%AB%E5%B1%B1%E6%96%B9%E8%88%9F_Doubao%20Seedance%202.0%20%E7%B3%BB%E5%88%97%E6%8F%90%E7%A4%BA%E8%AF%8D%E6%8C%87%E5%8D%97_1784531609.pdf)) |
| Timestamps on 2.0 | 模型对精确时间（如 0–3 秒）的支持不稳定，强行限制时长可能导致生成结果异常。 | Same guide; repeated verbatim in ByteDance's [troubleshooting guide](https://raw.githubusercontent.com/bytedance/agentkit-samples/db8aaa98a61135cd580dbff267f0d61d93406f54/skills/byted-ark-seedance-pe/references/seedance-2-troubleshooting-guide.md) (official GitHub org; rechecked) |
| 2.0 versus 2.5 timing | 响应时间戳：Seedance 2.0 不响应时间戳只响应镜头序号，而 Seedance 2.5 响应整数秒的时间戳。 | Official 2.5 guide, doc 82379/2607689, 2026-08-07 ([mirror](https://raw.githubusercontent.com/Jdaroro/awesome-seedance-2x-prompts/078d4d244a7b22b46156358f5afcb5fce3b4077d/docs/official-pdfs/zh-CN/%E7%81%AB%E5%B1%B1%E6%96%B9%E8%88%9F_Doubao%20Seedance%202.5%20%E6%8F%90%E7%A4%BA%E8%AF%8D%E6%8C%87%E5%8D%97_1786106010.pdf)); English wording on [BytePlus 2607689](https://docs.byteplus.com/en/docs/ModelArk/2607689) |
| Volcengine's own optimizer | 顺序使用 镜头1 / 镜头2 / 镜头3 …，禁止写绝对秒数（如 0–3s）。Seedance 2.0 对精确时间支持不稳定。 | sd2-pe skill ([copy](https://raw.githubusercontent.com/oiuv/ai-short-drama/4f318097c54a2e24ea34d3c9d23d30f5ec332f11/skills/sd2-pe/SKILL.md)) |
| Per-shot block order | 每个镜头推荐按以下逻辑组织：运镜或镜头切换方式；主体动作与表情；位置或空间变化；音频信息。 | Volcengine 2.0 prompt guide |
| Shot count | No maximum or recommended count anywhere. Worked examples use three 镜头 per 15 s clip. | Volcengine 2.0 prompt guide; sd2-pe |
| Density rule | 视频时长过长但提示词剧情内容较少，会导致模型自行发挥。视频时长过短但提示词内容包含多个分镜，会导致视频内容/人物台词乱说。 Remedy in the same file: 把原来的四个镜头拆成两个视频，给够人物说英文台词的时间。 | ByteDance [typical-effect-cases](https://raw.githubusercontent.com/bytedance/agentkit-samples/db8aaa98a61135cd580dbff267f0d61d93406f54/skills/byted-ark-seedance-pe/references/typical-effect-cases.md) (official GitHub org; rechecked) |
| Prompt shape chooser | Path A, one paragraph, when time and space are both "few": 单一场景内、单一连续动作 / 一段台词 / 一次状态展示，即使台词长. Path B, a three-part storyboard with 镜头 blocks, for multi-event or multi-location content (≥2 分镜). | sd2-pe |
| Base and advanced formula | 主体+运动 + 环境（非必须）+运镜/切镜（非必须）+美学描述（非必须）+音频（非必须）; advanced: 精准主体 + 动作细节 + 场景环境 + 光影色调 + 镜头运镜 + 视觉风格 + 画质 + 约束条件 | ByteDance [prompt-guide](https://raw.githubusercontent.com/bytedance/agentkit-samples/db8aaa98a61135cd580dbff267f0d61d93406f54/skills/byted-ark-seedance-pe/references/prompt-guide.md); Volcengine 2.0 guide |
| Camera | 模型对运镜词理解力很强，直接使用标准运镜术语即可… 一个镜头里尽量只指定 1 种运镜方式，不要同时要求推拉摇移。 `camera_fixed`: 参考图场景不支持，Seedance 2.0 系列暂不支持. | Volcengine 2.0 guide; Ark create-task API doc 82379/1520757 ([mirror](https://raw.githubusercontent.com/qianfree/team-api/b4c8cfd14a82db82f07793785423a46eba61de46/docs/%E5%8D%8F%E8%AE%AE%E6%96%87%E6%A1%A3/%E8%B1%86%E5%8C%85%E7%B3%BB%E5%88%97/seedance_2.0_API_%E5%88%9B%E5%BB%BA%E8%A7%86%E9%A2%91.md)) |
| Duration | Integer in [4,15] or -1 (model-chosen), default 5. Echo tip: 时长：4秒，比例：9:16 at the start or end of the prompt, 要用中文的"秒"，不能写"s". | Ark API doc; ByteDance troubleshooting guide |
| Length ceiling | 中文提示词不超过500字，英文提示词不超过1000词。字数过多易导致信息分散… 请勿直接将完整剧本作为提示词使用。 | Ark API doc; Volcengine 2.0 guide |
| Audio symbols | （）音乐, <>音效, {}台词, 【】字幕; 台词语言需统一; 用日语说道{こんにちは}; dialogue in double quotes recommended; `generate_audio` default true; mono output. | Volcengine 2.0 guide; Ark API doc |
| Constraints | Only three templates: 保持无字幕 / 避免生成任何文字或字幕, 不要生成Logo, 不要生成水印. 目前无法直接做到 100% 避免生成字幕. No negative-prompt field on any surface. | Volcengine 2.0 guide |
| References | 素材类型+序号 (图片 n), never Asset IDs; 将<图片N>中的[特征]定义为<主体N>; 张三@图片1; 9 images, 3 videos, 3 audio; recommend 4–5 assets; multi-view sheets discouraged on 2.0. | Volcengine tutorial 82379/2291680 ([mirror](https://raw.githubusercontent.com/qianfree/team-api/b4c8cfd14a82db82f07793785423a46eba61de46/docs/%E5%8D%8F%E8%AE%AE%E6%96%87%E6%A1%A3/%E8%B1%86%E5%8C%85%E7%B3%BB%E5%88%97/seedance_2.0%E6%95%99%E7%A8%8B.md)); 2.0 guide; 2.5 guide's version-difference list |
| Model card | 4 to 15 seconds, native 480p/720p; limitations include audio distortion and lip-sync errors in multi-speaker scenes; text-based storyboards accepted as input. | [arXiv 2604.14148](https://arxiv.org/abs/2604.14148) |
| Extension | Video extension exists at model level (paper, launch post, Dreamina); the paper lists continuation defects: color consistency, multi-subject omission, subject duplication. Tutorial: up to 3 clips stitched by extension. | Paper; [launch post](https://seed.bytedance.com/en/blog/official-launch-of-seedance-2-0); [Dreamina](https://dreamina.capcut.com/tools/seedance-2-0) |

One official inconsistency must be carried honestly: the official 2.0
tutorial's showcase prompt uses 2-4 秒 / 4-6 秒 / 6-8 秒, and ByteDance's
agentkit `SKILL.md` for the same optimizer mandates time-sliced storyboards
(0-3s, 3-10s), while the guide, the 2.5 version-difference list, sd2-pe and the
bundled troubleshooting file all say shot order only. The weight of official
text is shot order; the exceptions are why the design below keeps seconds as
an internal budget rather than banning them outright.

## B. Community claims, as assessed

Status vocabulary follows `references/source-registry.md`. "Rechecked" means
one skeptic agent opened the decisive source again; "assessed" means the
status was assigned from the harvested quotes without a second opening.

| Claim circulating online | Status | Why | Repository action |
|---|---|---|---|
| Multi-shot prompts must use 【时间轴】0-3s / 3-6s or [0-3s] | field-observed only, contradicted by official text (rechecked) | Taught by the most-copied 即梦 community skills; no official document uses it; guide says precise ranges are unstable on 2.0; two community ledgers retracted it after reading the PDF | Rewrite `references/multishot-grammar.md` and the timeline template note in `references/vocab/zh.md`, `ja.md`, `ko.md` |
| `Shot 1:` / `Shot 2:` labels are parsed as hard cuts | provider-documented structure, cut claim unsupported (rechecked) | Labels organise content in event order; the cut type belongs inside the block (镜头切至…, 硬切); writers report soft control | Add the four-part block order and the "spell out the cut" rule |
| Six or more shots in 15 s work reliably | unverified, conflicts with the official density warning (rechecked) | No source supports it; official examples use three; ByteDance warns short duration plus many 分镜 garbles content and lines | State it as unlikely; use the ladder in `docs/DESIGN_TIME_STRUCTURE.md` |
| Camera first makes the model follow it | partially: official inside each shot block, unverified for the whole prompt (assessed) | Block order puts the move first; the whole-prompt formula puts camera fifth | Reword templates: camera leads each shot block |
| Keep prompts under 100 words | unverified (assessed) | Official ceiling is 500 汉字 / 1000 English words; documented failure is dropped elements, not a truncated tail | Quote the ceiling as a ceiling; keep compact drafts as a craft choice |
| Chinese beats English on 即梦, or the reverse | unverified both ways (assessed) | Official text only lists supported languages and requires uniform dialogue language | Say nothing about language performance |
| The model follows a duration written in the prompt | contradicted as a control, official as an echo (assessed) | Duration is an API or UI parameter; the echo 时长：X秒 is a documented reinforcing tip | Parameter first, prose echo second |
| Negative prompts like "no blur, no extra fingers" work | unverified (assessed) | Only 字幕 / Logo / 水印 constraint sentences are documented, with partial effect | Offer the three sentences only |
| 8K, masterpiece, cinematic improve output | unverified (assessed) | Absent from official text; guide warns redundancy confuses the model | Keep the anti-slop rule |
| Quoted dialogue always lip-syncs | contradicted as "always" (assessed) | Quotes are the documented marker; the paper lists multi-speaker lip-sync errors; over-long lines garble | Short single-speaker lines that fit the clip; never promise sync |
| Fixed seeds reproduce a video, or align clips | unverified; no seed found in 2.0 material (assessed) | Only one repo uses a seed, to iterate a single shot | Keep seeds out of continuity planning |
| 15 s on every surface | 15 s is the API maximum; surfaces differ (assessed) | Some products expose 4/8/12 s plus smart duration; Runway 5–15 s | Verify per surface |
| Chaining from the last frame guarantees continuity | field-observed, no guarantee (assessed) | Most common technique; provider admits continuation defects; benchmarks show drift | One anchor among several; only from accepted footage |
| Previous clip as a video reference keeps identity | unverified for identity (assessed) | Official framing is camera and motion guidance | Video for motion, images for identity |
| Same identity images every clip prevent drift | necessary, not sufficient (assessed) | Marketing percentages have no method; benchmarks show imperfect consistency | Keep identity slots plus scheduled re-anchors |
| A whole two-minute episode in one call | false (assessed) | 4–15 s per generation on 2.0; 30 s and 50 assets are 2.5 numbers | Series mode drafts eight or more clips |
| Native extend exists on every surface | false (assessed) | Model-level feature; several adapters expose reference mode only; degradation after 2–3 extensions | Gate on the verified surface; cap chain depth |

## C. What is 2.5, not 2.0

30-second single-pass clips, up to 50 reference assets (30 images, 10 videos,
10 audio), integer-second timestamps and time-point control, free aspect
ratios in [0.4, 2.5], multi-view subject references, MOV output. Any of these
attributed to Seedance 2.0 is a 2.5 leak. Source: the official 2.5 guide's
version-difference list (mirror above).

## D. Research and field results worth keeping

- Shot-level structured prompting beat one global prompt for Seedance in a
  2026-08 benchmark (composite 0.730 versus 0.665), and the same work rates
  Seedance weak on film-grammar continuity such as transitions, rhythm, the
  180-degree rule and eyelines ([arXiv 2608.16717](https://arxiv.org/html/2608.16717), research tier).
- Filtered, causally prior context beat a whole story bible for cross-episode
  continuity recall (0.700 to 0.946) at the text-planning layer
  ([arXiv 2608.22725](https://arxiv.org/abs/2608.22725), research tier, model-agnostic).
- Production tools converge on 2–4 sub-shots per 8–15 s segment and on
  shot-size durations of roughly 2–3 s for a close-up, 3–5 s medium, 5–7 s
  wide (field tier: huobao-drama, seedance2pro, seedance-studio).
- Vertical short drama conventions reported by Chinese press and community:
  9:16, 40–70 s per episode, a hook in the first 3 s, a small reversal every
  15 s; segment sizing by function, 过渡段 8–10 s, 叙事段 10–15 s, 爆点段
  12–15 s (field and press tiers).
- Hands-on press on the first-party one-click drama agents: long waits,
  occasional consistency flaws, garbled text, "still a probability game"
  (press tier). No consistency percentage found had a method behind it.

## E. Repositories verified on GitHub (stars and activity as read)

| Repository | Stars | Activity | What it is | Seedance 2.0 | Worth borrowing |
|---|---|---|---|---|---|
| harry0703/MoneyPrinterTurbo | 125.8k | 2026-09-24 | Narration plus stock or generated b-roll shorts | Version-mixed; native path pins 1.0 Pro | Nothing for direction; a warning about 3 s planning units |
| calesthio/OpenMontage | 61.3k | 2026-09-06 | Agentic production framework, separate 2.0 and 2.5 skill files | Yes, kept apart from 2.5 | Extend or add shots only after a clean single shot |
| HBAI-Ltd/Toonflow-app | 16.0k | 2026-09-25 | Infinite-canvas short-drama platform with stage gates | Dedicated 2.0 template (≤15 s) | Hard-cut marker, immutable locks, no-subtitles default, stage gates |
| chatfire-AI/huobao-drama | 15.5k | 2026-09-23 | One sentence to episode: storyboard breaker, per-segment prompts | First-class 2.0 adapter | 8–15 s segments of 2–4 sub-shots; runtime from script length |
| HKUDS/ViMax | 12.5k | 2026-09-20 | Academic idea-to-video pipeline | 2.0 Fast via a router only | First-frame, last-frame, motion decomposition |
| zenstory-ai/drama-skills | 2.3k | 2026-09-24 | Short-drama skill chain with per-model prompt dialects | Dedicated 2.0 dialect citing Volcengine docs | Continue only from the actual previous video plus its actual tail frame |
| liangdabiao/Seedance2-Storyboard-Generator | 2.4k | 2026-09-21 | Story to multi-episode storyboards | Yes, 即梦 tags | Final-frame record per episode; note its 3-second timelines conflict with official guidance |
| xuanyustudio/LocalMiniDrama | 1.9k | 2026-09-14 | Local desktop drama maker | Yes | ffmpeg tail-frame linking; an ending-motion handoff field |
| HITsz-TMG/VideoClaw | 1.8k | 2026-08-26 | Six-stage director skill with user checkpoints | Selectable backend | Stage gates with visible artifacts |

Most repositories that advertise Seedance 2.0 offer no output evidence; the
one cost figure found is one case at about ¥130 for a two-minute episode at
480p (Toonflow). Techniques from other model lines (SkyReels, Wan, Kling,
Sora, Veo) were dropped from consideration as evidence about Seedance 2.0.
