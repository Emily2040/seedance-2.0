# Chinese Vocabulary

**Script variant: Simplified Chinese (简体中文, zh-Hans), mainland terminology.** Every phrase below is written for the mainland surfaces this skill targets. See Script Variant before using any of it in a Traditional-script deliverable.

Use this reference for Chinese Seedance prompt wording, role binding, and compact prompt compression. Keep reference tags unchanged: `@Image1`, `@Video1`, and `@Audio1` stay literal.

| Function | Chinese | English meaning |
|---|---|---|
| Role | `@图片1 为首帧` | Image 1 is the first frame |
| Role | `@图片2 为尾帧` | Image 2 is the last frame |
| Role | `@图片1 锁定主体身份` | Image 1 locks subject identity |
| Role | `@图片2 仅参考场景氛围` | Image 2 provides scene mood only |
| Role | `@视频1 仅参考运镜` | Video 1 provides camera movement only |
| Role | `@视频1 参考动作节奏` | Video 1 provides action rhythm |
| Role | `@音频1 参考节奏和氛围` | Audio 1 provides tempo and mood |
| FirstLastFrame | `首帧保持不变` | keep first frame unchanged |
| FirstLastFrame | `自然过渡到尾帧` | transition naturally to final frame |
| FirstLastFrame | `中间动作连续，不跳切` | continuous in-between motion, no jump cut |
| FirstLastFrame | `以尾帧为最终画面目标` | use final frame as the target image |
| Camera | `缓慢推镜` | slow push-in |
| Camera | `镜头后拉揭示空间` | pull back to reveal the space |
| Camera | `横向稳定跟拍` | stable lateral tracking |
| Camera | `轨道平移` | slider / dolly lateral move |
| Camera | `固定中景` | locked medium shot |
| Camera | `微距特写` | macro close-up |
| Camera | `低角度仰拍` | low-angle shot |
| Camera | `高角度俯拍` | high-angle shot |
| Camera | `过肩镜头` | over-the-shoulder shot |
| Camera | `弧形绕摄` | arc orbit shot |
| Camera | `手持镜头，轻微呼吸晃动` | handheld shot with slight breathing sway |
| Shot | `中近景` | medium close-up |
| Shot | `远景定场镜头` | wide establishing shot |
| Shot | `四分之三侧脸` | three-quarter profile |
| Shot | `三分法构图` | rule-of-thirds composition |
| Shot | `大面积负空间，孤独感` | large negative space, isolation |
| Shot | `前景虚化遮挡` | subject seen past foreground blur |
| Shot | `引导线指向焦点` | leading lines pointing to the focus |
| Shot | `前中后景层次分明` | distinct foreground, midground, background layers |
| Camera | `一镜到底长镜头` | one continuous long take |
| Lighting | `树叶间洒下的斑驳光` | sunlight dappled through leaves |
| Lens | `长焦压缩空间` | telephoto compression |
| Lens | `广角空间感` | wide-angle spatial feel |
| Lens | `焦点从模糊过渡到清晰` | focus resolves from blur to sharpness |
| Lighting | `柔和侧逆光` | soft side backlight |
| Lighting | `暖色实用灯` | warm practical light |
| Lighting | `左侧暖色实用灯` | warm practical light from left |
| Lighting | `冷色月光轮廓光` | cool moon rim light |
| Lighting | `体积光穿过薄雾` | volumetric light through mist |
| Lighting | `潮湿地面反射霓虹` | wet ground reflects neon |
| Motion | `脚步带动薄雾扩散` | footsteps disturb fog |
| Motion | `水珠聚合后沿表面下滑` | droplets merge and slide down |
| Motion | `缓慢转头并停住` | slow head turn and stop |
| Motion | `衣料随动作自然摆动` | fabric moves naturally with action |
| VFX | `金色粒子升起后消散` | gold particles rise and dissipate |
| VFX | `蓝色电弧沿边缘游走` | blue arcs crawl along the edge |
| VFX | `光线扫过材质表面` | light sweep travels across material |
| Audio | `一句短而清晰的对白` | one short clear spoken line |
| Audio | `无配乐，仅低环境声` | no music, low ambience only |
| Audio | `对白期间镜头固定` | locked camera during dialogue |
| Audio | `脚步声卡点` | footsteps hit the beat |
| Text | `不要新增字幕、水印或无关文字` | no new subtitles, watermark, or unrelated text |
| Text | `交付字幕使用简体中文` | deliver subtitles in Simplified Chinese |
| Text | `交付字幕使用繁體中文（台灣）` | deliver subtitles in Traditional Chinese (Taiwan) |
| Text | `交付字幕使用繁體中文（香港）` | deliver subtitles in Traditional Chinese (Hong Kong) |
| Editing | `接着拍` | continue the shot |
| Editing | `延长 5 秒` | extend by five seconds |
| Editing | `只替换失败片段` | replace only the failed segment |
| Constraint | `严格保持logo、标签、形状和颜色不变` | preserve logo, label, shape, and color |
| Constraint | `仅改变动作、光线和镜头` | change only action, light, and camera |
| Constraint | `不复制人物、场景或品牌` | do not copy person, scene, or brand |
| Safety | `改为原创角色` | change to an original character |
| Safety | `仅使用已授权参考` | use only authorized references |
| Safety | `保留创意功能，不保留受保护身份` | preserve creative function, not protected identity |

## Compact Template

`@Image1为参考，严格保持[主体/产品/脸部/标志]不变；仅加入[动作/光线/镜头变化]。镜头：[一个动作]。声音：[音效或环境声]。`

## Multimodal Template

`@图片1锁定原创人物身份与服装。@视频1仅参考运镜，不复制人物、地点或品牌。@音频1仅参考节奏与氛围。`

On a Latin-tag surface, the same template with unchanged tags: `@Image1锁定原创人物身份。@Video1仅参考运镜。@Audio1仅参考节奏。` Never mix the two tag families in one prompt.

## Timeline Template

社区常用的长提示词骨架（即梦/Dreamina 平台，约 8 秒以上时使用；field-observed）。保持 `@Image1` 等引用标签不变：

```
【风格】[媒介、质感、色调，一句话]
【时间轴】0-3s：[画面+镜头+音效]；3-6s：[画面+镜头+音效]；6-10s：[画面+镜头+音效]
【声音】[对白/环境声/音效/无配乐]
【参考】@Image1 锁定主体身份；@Video1 仅参考运镜；@Audio1 仅参考节奏
```

## Sequence and Continuation Phrases

Use these when the Chinese prompt is part of a v6 sequence project, continuation, or localized delivery workflow.

| Function | Chinese | English meaning |
|---|---|---|
| Role | `本项目状态以已接受视频为准` | accepted footage is the project truth |
| Role | `从上一段真实结尾继续` | continue from the actual previous ending |
| Role | `不要重演上一段动作` | do not replay the previous action |
| Role | `本段只拍当前任务` | this clip shows only the current task |
| Role | `后续剧情暂不出现` | future story beats do not appear yet |
| FirstLastFrame | `以上一段尾帧为起点` | use previous final frame as starting point |
| FirstLastFrame | `以新尾帧状态收束` | settle into the new final state |
| Motion | `保持上一段开放动作方向` | preserve previous open motion vector |
| Motion | `动作从静止状态开始` | action starts from a still state |
| Editing | `作为 Clip 02 的接续提示词` | continuation prompt for Clip 02 |
| Editing | `只修复尾部漂移，不改前半段` | repair only tail drift, not the first half |
| Constraint | `已完成动作不得重复` | completed actions must not repeat |
| Constraint | `未发生内容不得提前出现` | unshown future events must not appear early |
| Text | `画面保持无文字，字幕后期添加` | keep image textless; subtitles added in post |
| Text | `中文标题和法务文案在剪辑中添加` | Chinese titles and legal copy added in edit |
| Safety | `保留创意功能，替换为原创身份` | preserve creative function with original identity |

## Dialogue Notes (对白注意事项)

No universal Mandarin-first ranking or character ceiling is established here. Keep the user's quoted dialogue, script, and intended voice. Measure spoken duration with pauses, and review words, performance, and sync separately. The model card's Chinese-voice tasks are not a matched language ranking; see [audio-guide](../audio-guide.md).

- 台词格式：角色名 + 动作 + 冒号 + 引号内台词。Character counts describe a line; they do not certify timing or sync.
- Check the active surface's documented audio settings; do not assume a named lip-sync toggle or its default.
- Inline bracketed audio cues are a prompting convention unless the active operation documents a parser. Keep spoken words separate from performance direction.

## Aesthetic Registers (美学语域)

Chinese genre and aesthetic terms can carry useful creative intent. Preserve the user's chosen term; when the intended shot is unclear, ask what matters or propose a scene-specific visible or audible detail. The examples below are authored possibilities, not definitions of a culture or mandatory ingredients. This is editorial guidance for making direction reviewable, not evidence that these terms destabilize Seedance output. Independent language and production-language review remains pending.

| Term | One possible scene treatment |
|---|---|
| 武侠 (wuxia) | physical craft, not the label: `竹林间的剑客、衣袂随步伐摆动、足尖点地的轻功起跳、竹叶纷落` |
| 仙侠 (xianxia) | one supernatural element grounded in physics: `御剑离地三尺悬停、云海在脚下流动、法器发出的冷光映在脸上` |
| 国风 / 水墨 (guofeng / ink-wash) | the medium itself: `水墨晕染的远山、留白的天空、毛笔笔触的边缘、淡彩点染` |
| 废土 (wasteland) | material decay: `锈蚀的车壳、沙尘掠过裂开的公路、褪色的广告牌` |
| 烟火气 (lived-in warmth) | street-level sensory detail: `路边摊的蒸汽、油锅的滋滋声、灯泡下的塑料凳` |

## Script Variant (简繁)

"Chinese" is not one script. This file is Simplified (zh-Hans); a deliverable for 台灣, 香港, or 澳門 needs Traditional (zh-Hant). Leaving it undeclared means the mainland variant ships to a Traditional-script audience by default, which reads as a foreign cut rather than a localized one.

**Prompt script and delivery script are separate decisions.** Preserve the user's chosen script and record the target audience's locale. Simplified and Traditional subtitles may require different vocabulary as well as character conversion. This repository has no controlled evidence that Simplified prompting improves lip-sync or that training geography explains language performance. Do not switch scripts merely on that assumption.

Where it bites hardest is exactly where this repo is already weakest. Hands-on tests report 字幕乱码 (garbled subtitles), and every vocab file's standing advice is to keep the frame textless and add subtitles in post - so the variant is primarily a **delivery** parameter, set on the post/subtitle path rather than requested from the model.

**Do not convert by find-and-replace.** Several Simplified characters map to more than one Traditional character by meaning, and a naive pass produces text that is wrong rather than merely foreign:

| 简体 | 繁體 — 按意思分化 |
|---|---|
| 头发 (hair) | 頭髮，不是 頭發 |
| 皇后 (queen) | 皇后，不是 皇後 |
| 干燥 (dry) / 干活 (to work) | 乾燥 / 幹活 |
| 里面 (inside) / 三里 (li, distance) | 裡面 / 三里 |
| 松开 (loosen) / 松树 (pine) | 鬆開 / 松樹 |

头发 → 頭髮 matters here specifically: hair is a named continuity anchor in the reference workflow, so it turns up in prompts and in take notes.

Vocabulary also differs beyond the characters, so a correct script conversion can still read as the wrong region:

| 简体（中国大陆） | 繁體（台灣 / 香港） |
|---|---|
| 视频 | 影片（台）／影片、短片（港） |
| 屏幕 | 螢幕 |
| 质量 | 品質 |
| 信息 | 資訊 |
| 网络 | 網路（台）／網絡（港） |
| 摄像机 | 攝影機 |

Record the variant with the delivery target, not the prompt, and keep it fixed for the life of a project - a sequence that switches variants between clips has the same continuity problem as one that switches wardrobe.

## Slop Traps

编辑建议：只有在意图不清时，才把抽象形容词补充为能看见或听见的指令；有用的风格词可以保留。这有助于核对创作要求，不代表模型必然无法理解形容词，也不保证画面更稳定或节省生成额度。以下是写法示例，不是通用配方；不要自动加入慢推镜、雾气或青橙调色。保留用户选定的风格、情绪强度、对白、参考标签和设置；若不同理解会明显改变场景，给出少量有区别的选项，或按用户授权代选。

| 套话 | 可按场景补充的指令 |
|---|---|
| `电影感` | 例如钟表匠听见滴答声后微笑的片段：`固定镜头与她的眼睛同高；滴答声响起，她才微笑；结尾停留在这个表情上`。这是该片段的一种选择，不要求其他场景也静止克制 |
| `氛围感` | 先明确场景需要哪种氛围，再选择相关声画细节；工作室可写`停下工具后，钟的滴答声仍清晰可闻`，不必添加雾或湿地反光 |
| `高级感` | 明确要展示哪种工艺或材质，例如`侧光扫过表盘上的拉丝纹理，刻度保持可读`；不要默认换成空白背景或金色装饰 |
| `大片感` | 若意图是规模，说明人物与空间的关系；若意图是紧张或惊喜，说明造成它的动作，不自动增加人群 |
| `质感`（单独使用） | 指明哪个物体、哪种表面，以及镜头需要看见什么：`近处纸张边缘露出纤维` |
| `震撼` | 指明造成冲击的对比、动作或揭示；保留用户要求的强烈表现 |
| `唯美` | 按选定风格明确构图、色彩或光的行为，不强制柔光或低饱和 |
| `史诗级` | 若指空间尺度，写出主体与环境的比例；若指风格，保留该意图并补充本场景的表现方式 |
| `超高清 / 8K / 4K` | 记录实际交付分辨率要求，在当前操作支持的设置中处理；不要把提示词里的数字当作输出分辨率保证 |
| `杰作 / 顶级品质` | 明确本片段的验收项，如表盘刻度可读、动作衔接连续；这些是要求，不是已达到的结果 |
| `绝美` | 明确最重要的视觉细节，并保留用户选定的审美方向 |
| `酷炫转场` | 明确从什么画面切到什么画面、靠哪个动作衔接；只有需要该效果时才选择匹配剪辑、硬切或甩镜 |
