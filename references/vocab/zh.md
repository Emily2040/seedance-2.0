# Chinese Vocabulary

Use this reference for Chinese Seedance prompt wording, role binding, and compact prompt compression. Keep reference tags unchanged: `[Image1]`, `[Video1]`, and `[Audio1]` stay literal.

| Function | Chinese | English meaning |
|---|---|---|
| Role | `@图1 为首帧` | Image 1 is the first frame |
| Role | `@图2 为尾帧` | Image 2 is the last frame |
| Role | `@图1 锁定主体身份` | Image 1 locks subject identity |
| Role | `@图2 参考场景氛围` | Image 2 provides scene mood only |
| Role | `@视频1 仅参考运镜` | Video 1 provides camera movement only |
| Role | `@视频1 参考动作节奏` | Video 1 provides action rhythm |
| Role | `@音频1 参考节奏和氛围` | Audio 1 provides tempo and mood |
| FirstLastFrame | `首帧保持不变` | keep first frame unchanged |
| FirstLastFrame | `自然过渡到尾帧` | transition naturally to final frame |
| FirstLastFrame | `中间动作连续，不跳切` | continuous in-between motion, no jump cut |
| FirstLastFrame | `以尾帧为最终画面目标` | use final frame as the target image |
| Camera | `缓慢推镜` | slow push-in |
| Camera | `后退揭示镜头` | pull back to reveal the space |
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
| Shot | `宽幅远景` | wide establishing shot |
| Shot | `三分之二侧脸` | three-quarter profile |
| Lens | `长焦压缩空间` | telephoto compression |
| Lens | `广角空间感` | wide-angle spatial feel |
| Lens | `焦点从模糊过渡到清晰` | focus resolves from blur to sharpness |
| Lighting | `柔和侧逆光` | soft side backlight |
| Lighting | `暖色实用灯` | warm practical light |
| Lighting | `左侧暖色实用灯` | warm practical light from left |
| Lighting | `冷色月光轮廓光` | cool moon rim light |
| Lighting | `体积光穿过薄雾` | volumetric light through mist |
| Lighting | `湿地反射霓虹` | wet ground reflects neon |
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

`[Image1]为参考，严格保持[主体/产品/脸部/标志]不变；仅加入[动作/光线/镜头变化]。镜头：[一个动作]。声音：[音效或环境声]。`

## Timeline Template

社区常用的长提示词骨架（即梦/Dreamina 表面，约 8 秒以上时使用；field-observed）。保持 `[Image1]` 等引用标签不变：

```
【风格】[媒介、质感、色调，一句话]
【时间轴】0-3s：[画面+镜头+音效]；3-6s：[画面+镜头+音效]；6-10s：[画面+镜头+音效]
【声音】[对白/环境声/音效/无配乐]
【参考】[Image1] 锁定主体身份；[Video1] 仅参考运镜；[Audio1] 仅参考节奏
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

## Slop Traps

社区共识：抽象的"感觉词"会让模型无法判断该强调哪个元素。把感觉词拆解成制造这种感觉的物理元素——材质、光线、色彩、空气——画面立即变稳。

| 套话 | 改写为 |
|---|---|
| `电影感` | 写出景别、运镜、光源和调色：`宽幅远景，缓慢推镜，低角度暖阳，低饱和青橙调` |
| `氛围感` | 写出制造氛围的物理元素：`薄雾、逆光轮廓、湿地反光、低环境声` |
| `高级感` | 写出光线与材质行为：`柔和侧光、受控反光、干净背景、金属拉丝纹理` |
| `大片感` | 写出物理规模：人群数量、镜头距离、建筑高度 |
| `质感`（单独使用） | 指明哪种质感：`磨砂玻璃、丝绒吸光、纸张纤维` |
| `震撼` | 写出造成震撼的那一个画面对比或揭示 |
| `唯美` | 写出色彩、构图与光的具体行为 |
| `史诗级` | 删除，或换成具体的空间尺度与人数 |
| `超高清 / 8K / 4K` | 删除；分辨率是参数，不是描述 |
| `杰作 / 顶级品质` | 删除；质量不是请求出来的 |
| `绝美` | 写出最重要的那一个视觉细节 |
| `酷炫转场` | 写出转场名称：`匹配剪辑、硬切、甩镜` |
