<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/hero-light.svg">
  <img alt="Seedance 2.0 Skill OS — Direct the model. Don't micro-manage the frame." src="assets/hero-dark.svg" width="100%">
</picture>

**Turn an idea into a directed video prompt.** Seedance 2.0 Skill OS is an agent
skill for planning shots, binding references and continuing from an accepted
clip. Your video provider handles generation and its costs.

[Watch the clips](#seen-not-told) · [Try a first prompt](#start-here) · [Install](#install) · [Choose a workflow](#choose-a-workflow) · [Evidence status](#evidence-status)

`v6.7.0` · [MIT](LICENSE) · [Changelog](CHANGELOG.md) · [Emily / Iamemily2050](https://github.com/Emily2040)

**Languages:** English (this page) · [中文](docs/README.zh.md) · [日本語](docs/README.ja.md) · [한국어](docs/README.ko.md) · [Español](docs/README.es.md) · [Русский](docs/README.ru.md)

Five-minute quickstarts: [English](docs/QUICKSTART.md) · [中文](docs/QUICKSTART.zh.md) · [日本語](docs/QUICKSTART.ja.md) · [한국어](docs/QUICKSTART.ko.md) · [Español](docs/QUICKSTART.es.md) · [Русский](docs/QUICKSTART.ru.md)

## Seen, not told

Seven scenes, seven prompts, five languages. Each is a complete fifteen-second story: the
situation legible by shot two, a reversal, and a hold on whoever lost, cut like short drama in
four or five shots. Each clip is generated on Seedance 2.0 from the exact prompt beneath it:
text to video, no reference assets, one take, no post work. Above each prompt sits the kind of
brief people usually type, so the difference is visible before it is explained. Every prompt
went through the [moderation pre-screen](references/moderation-prescreen.md) before publication,
because a classifier refuses words, not intent, and every prompt is [directed for the
model](references/direct-for-the-model.md): one action per shot while everyone else keeps
living, reactions written as a feeling plus one physical anchor, prop work written as a hand,
and a lock line closing every shot that restates the light, the people and where they stand,
because the model keeps nothing across a cut that the prompt does not repeat. Where a clip has
not been rendered yet, its slate stands in its place.

<table>
<tr>
<td width="50%" valign="top"><a href="#clip-01-by-appointment-only"><img src="assets/clips/clip-01-by-appointment-only.svg" alt="Slate for clip 01, English: Paint-stained overalls in a luxury boutique. “The new owner is standing in the shop now.”" width="100%"></a></td>
<td width="50%" valign="top"><a href="#clip-02-hold-the-line"><img src="assets/clips/clip-02-hold-the-line.svg" alt="Slate for clip 02, English: “Let it go, Tom! It's only a boat!” “It's my father's!” The wave breaks." width="100%"></a></td>
</tr>
<tr>
<td width="50%" valign="top"><a href="#clip-03-这杯茶"><img src="assets/clips/clip-03-this-cup-of-tea.svg" alt="Slate for clip 03, 中文: 寿宴上，没人请她来。 “这杯茶，我妈等了二十年。”" width="100%"></a></td>
<td width="50%" valign="top"><a href="#clip-04-超时二十分钟"><img src="assets/clips/clip-04-twenty-minutes-late.svg" alt="Slate for clip 04, 中文: “超时二十分钟，我要给差评。” 头盔摘下来，是一头花白的短发。" width="100%"></a></td>
</tr>
<tr>
<td width="50%" valign="top"><a href="#clip-05-사직서"><img src="assets/clips/clip-05-resignation.svg" alt="Slate for clip 05, 한국어: 사직서를 그의 서류 위에 올려놓는다. “제 보고서, 이름만 바꾸셨더군요.”" width="100%"></a></td>
<td width="50%" valign="top"><a href="#clip-06-最後の一球"><img src="assets/clips/clip-06-last-pitch.svg" alt="Slate for clip 06, 日本語: 夏の決勝、九回裏、雨。 最後の一球はミットに収まる。" width="100%"></a></td>
</tr>
<tr>
<td width="50%" valign="top"><a href="#clip-07-ещё-один-раунд"><img src="assets/clips/clip-07-one-more-round.svg" alt="Slate for clip 07, Русский: «Хочешь бросить — бросай. Только мать смотрит.»" width="100%"></a></td>
<td width="50%" valign="top"></td>
</tr>
</table>

#### Clip 01: By appointment only

<sub>English · 15 s · 16:9 · storyboard · slate: not rendered yet · ladder: Stretch: 4.5 beats (one insert at half), load 3, S = 2.0</sub>

**What people usually type:** *rich woman disguised as poor gets humiliated at luxury store, plot twist, satisfying, cinematic, 4k*

**What you know by shot two:** Shot one is a soaked woman in work clothes stopped inside a boutique door by a voice that says appointment only; shot three is a phone call that says the new owner is standing in the shop.

<details>
<summary>The prompt the skill wrote</summary>

> Shot 1. Wide shot from the back of a hushed luxury boutique looking toward the glass front
> door, on a rainy afternoon: cream carpet, glass shelves of shoes along the left wall, the
> counter on the right with two assistants in black behind it, one folding tissue paper, one
> glancing up at the door. A woman pushes the glass door open, steps inside dripping, and stops
> on the mat, water running off her sleeves. From just off frame right, by the counter, the
> manager's voice, polite and thin: "We're by appointment only, ma'am." She turns her head
> toward the voice, calm, almost amused, and says nothing. Light: soft grey daylight from the
> front window, warm spotlights on the shelves. The woman: thirties, dark hair tied back, white
> overalls stained with paint, tan work boots, standing just inside the door, facing into the
> shop.
>
> Shot 2. Cut to a medium shot from the counter side: she walks across the carpet to the white
> display chaise in the middle of the shop, sits down on it facing the counter, crosses one
> muddy boot over the other, and looks slowly along the shelves, unhurried. Behind her the two
> assistants exchange a glance. Same light: soft grey daylight from the front window, warm
> spotlights on the shelves. The woman: thirties, dark hair tied back, white overalls stained
> with paint, tan work boots, seated on the white chaise in the middle of the shop, facing the
> counter. Camera on the counter side.
>
> Shot 3. Cut to a close shot of the manager from the chaise side, standing by the counter, a
> phone at his ear, listening. Embarrassed, the polite smile fades and he swallows; then he says
> quietly: "Yes, sir. The new owner is... standing in the shop now." His eyes go past the camera
> to her, off frame, and stay there. Same light: soft grey daylight from the front window, warm
> spotlights on the shelves. The manager: fifties, grey suit, steel-rimmed glasses, standing by
> the counter, facing the chaise. Camera on the chaise side.
>
> Shot 4. Cut to a two-shot from behind the chaise, her shoulder in the foreground, the manager
> by the counter and the wall of shoes beyond him: she lifts one arm and points at a single pair
> of shoes on the wall; he walks from the counter to the wall and lifts that pair down with both
> hands, careful now. Same light: soft grey daylight from the front window, warm spotlights on
> the shelves. The woman: thirties, dark hair tied back, white overalls stained with paint, tan
> work boots, seated on the chaise, facing the counter. The manager: fifties, grey suit,
> steel-rimmed glasses, walking from the counter to the wall of shoes. Camera behind the chaise.
>
> Shot 5. Cut to a close insert of the cream carpet: a trail of wet bootprints from the door to
> the chaise, rain running down the glass door behind. Hold on the bootprints. Same light: soft
> grey daylight from the front window.
>
> Sound: rain on the glass door, her boots on the carpet, the murmur of the phone line, his
> voice dropping; no music, no subtitles.

</details>

#### Clip 02: Hold the line

<sub>English · 15 s · 16:9 · storyboard · slate: not rendered yet · ladder: Stretch: 4 beats, load 3, S = 2.1</sub>

**What people usually type:** *epic storm at sea, fisherman fights giant wave, slow motion, dramatic music, 8k*

**What you know by shot two:** Shot two tells the audience what the rope is worth: an off-screen voice says it is only a boat, and his answer says whose boat.

<details>
<summary>The prompt the skill wrote</summary>

> Shot 1. Wide shot from the landward end of a wooden pier at night in a storm, looking out
> along it: a small fishing boat straining at a single mooring rope off the far end, its bow
> lifting and slamming with each swell, rain driven sideways through one sodium lamp, and behind
> the boat a wave building higher than the mast. At the far end of the pier a man leans back
> against the rope with both hands, boots sliding on the wet planks, holding on, his back to the
> camera. Light: one orange sodium lamp on its post at the end of the pier, black water beyond,
> nothing else. The man: forties, short beard streaked grey, yellow oilskin with the hood down,
> black rubber boots, at the end of the pier with the rope in both hands, facing the boat.
> Camera at the landward end.
>
> Shot 2. Cut to a medium shot at deck height from the side of the pier: the man has both hands
> on the rope, boots braced against a cleat, arms shaking with the strain, the rope creaking as
> the boat pulls. From the dark behind the camera, landward, a voice shouts over the wind: "Let
> it go, Tom! It's only a boat!" He hears it, keeps his eyes on the rope, and his grip tightens.
> Same light: one orange sodium lamp overhead, black water beyond. The man: forties, short beard
> streaked grey, yellow oilskin with the hood down, black rubber boots, braced at the cleat,
> facing the boat. Camera at his side.
>
> Shot 3. Cut to a close shot of his face from in front of him, the boat behind the camera: rain
> running off his brow, eyes on the rope, teeth clenched; without turning his head he shouts
> back over his shoulder, angry and close to tears: "It's my father's!" Same light: one orange
> sodium lamp overhead, black water beyond. The man: forties, short beard streaked grey, yellow
> oilskin with the hood down, braced at the cleat, facing the boat. Camera in front of him.
>
> Shot 4. Cut to a low angle from the pier planks in front of him, looking up at him with the
> boat's bow behind him: the wave breaks over the end of the pier and buries him in white water.
> When the water drains through the planks he is still there, bent double and coughing, both
> hands on the rope, the rope taut, the boat still there behind him. Hold on this frame as the
> next swell lifts the bow. Same light: one orange sodium lamp overhead, black water beyond. The
> man: forties, short beard streaked grey, yellow oilskin with the hood down, black rubber
> boots, still braced at the cleat, facing the boat. Camera low, in front of him.
>
> Sound: wind, the rope creaking, the two shouts, the wave's impact, water draining through the
> planks, his coughing. No music, no subtitles.

</details>

#### Clip 03: 这杯茶

<sub>中文 · 15 s · 16:9 · storyboard · slate: not rendered yet · ladder: Stretch at the boundary: 5 beats (two inserts at half), load 3 with the recalibrated person row, S = 1.9</sub>

**What people usually type:** *豪门寿宴反转名场面，女主打脸全场，短剧爆点，电影感，高级感*

**What you know by shot two:** Shot one is a birthday toast, seen over the old man's shoulder toward the door, that goes quiet when the door opens on a woman nobody invited; shot two is his face from the door's side, recognising her. Her walk up the table is shot three; the line in shot five says whose daughter she is.

<details>
<summary>The prompt the skill wrote</summary>

> 镜头1：固定全景，机位在老爷子身后偏高，越过他的肩膀拍向厅堂尽头正对着主位的大门。老宅厅堂里的寿宴，红色横幅下一张大圆桌坐满了宾客，主位的老爷子背对镜头举着茶杯，宾客们跟着举杯、碰杯，有说有笑。画面尽头的大门被推开，一个女人站在门口，面对着主位。笑声停下来，宾客们一个一个转头看向门口，互相压低声音说话，没有人站起来。灯光：头顶一盏暖黄的老式吊灯，桌布和人脸都在同一种暖黄光里，门外是深蓝的夜色。老爷子：七十多岁，白发向后梳，深棕色缎面唐装，坐在主位，面对大门，背对镜头。女人：三十多岁，黑色长发淋湿贴在脸侧，旧的深灰色呢子大衣，站在画面尽头的门口。机位在老爷子身后。
>
> 镜头2：反打，机位在大门方向，正面拍老爷子的近景，身边的宾客在虚焦里转头看向镜头方向的门口、小声议论。他看见她，愣住，惊慌，眼睛越过镜头一直盯着门口的她，喉结动了一下，然后把手里的茶杯慢慢放回面前的桌布上，手收回来握在桌边。灯光不变：头顶暖黄吊灯，脸在同一种暖黄光里。老爷子：七十多岁，白发向后梳，深棕色缎面唐装，坐在主位，面对大门和镜头。机位在大门方向。
>
> 镜头3：中景，机位在老爷子身旁稍后方，拍向大门：女人从门口沿着桌边朝镜头走来，脚步不快不慢，宾客们的目光跟着她转，她走到主位旁边停下，低头看着画面前景里坐着的他的侧影。灯光不变：头顶暖黄吊灯，她的脸从门外的蓝光走进桌上的暖黄光。女人：三十多岁，黑色长发淋湿贴在脸侧，旧的深灰色呢子大衣，从门口走到主位旁边站定。老爷子：深棕色缎面唐装的肩膀和白发在画面前景，坐在主位。机位在老爷子身旁。
>
> 镜头4：切至桌面特写，机位在桌边：白桌布，老爷子面前那只满杯茶，他的手握成拳放在桌边。女人的右手从画面右侧伸进来，握住杯身，把杯子提到桌布上方一掌高，杯口朝他那一侧倾斜，茶水从杯沿流到白桌布上，冒着热气，一直流到杯里没有茶；整个过程杯底一直在下。他的拳头在桌布上收紧了一下。灯光不变：头顶暖黄吊灯。女人的手：袖口是旧的深灰色呢子，手背上有雨水。
>
> 镜头5：切至女人的近景，机位在桌边略低，她站在主位旁边，身后是虚焦里转头看她的宾客和红色横幅，头顶是同一盏暖黄吊灯。她低头看着画面外坐着的他，眼睛没有离开他，声音很轻，每个字都清楚，说：“这杯茶，我妈等了二十年。”说完她的眼眶红了，没有眼泪，嘴唇抿住。灯光不变：头顶暖黄吊灯，脸在暖黄光里。女人：三十多岁，黑色长发淋湿贴在脸侧，旧的深灰色呢子大衣，站在主位旁边，低头面对他。机位在桌边。
>
> 镜头6：切回桌面特写，机位同镜头4。她的右手转动手腕，把空杯杯口朝下扣在湿桌布上，松开手，手退出画面。画面停在倒扣的杯子和布上漫开的茶水上，他的拳头在桌边慢慢松开。灯光不变：头顶暖黄吊灯。
>
> 声音：碰杯声和说笑声，门推开的一声之后全场安静，她的脚步声，杯子放到桌布上的一声，茶水落在布上的声音，说话时全场无声；无配乐。保持无字幕。时长：15秒。

</details>

#### Clip 04: 超时二十分钟

<sub>中文 · 15 s · 16:9 · storyboard · slate: not rendered yet · ladder: Stretch at the boundary: 5 beats, load 3, S = 1.9</sub>

**What people usually type:** *外卖员被差评感人反转，正能量短剧，泪目，电影感*

**What you know by shot two:** Shot one is a soaked delivery rider at a door and a man in the doorway with his phone out; shot two is the threat of a bad review. Shot three shows who is under the helmet.

<details>
<summary>The prompt the skill wrote</summary>

> 镜头1：固定中景，机位在走廊一侧，同时拍到门外的外卖员和门里的男人，两人隔着门槛面对面。深夜住宅楼的走廊，雨声很大。外卖员站在门外，浑身滴水，左手提着一袋外卖，右手刚按完门铃收回来，还在喘气。门被从里面打开，一个男人站在门里，右手握着手机，不耐烦，眉头皱着，上下打量她。灯光：走廊顶上一盏白色日光灯，门里透出暖黄的灯光。外卖员：黄色雨衣，黑色头盔，面罩抬起，站在门外，面对门里。男人：四十多岁，短黑发，深蓝色睡衣，站在门里，面对她。机位在走廊一侧。
>
> 镜头2：切至男人的近景，机位在门外她的位置，正面拍他。他把手机屏幕转向镜头方向的她，语气又急又冲，说：“超时二十分钟，我要给差评。”说完盯着她，等她回答。灯光不变：走廊的白色日光灯在他脸的一侧，门里的暖黄光在另一侧。男人：四十多岁，短黑发，深蓝色睡衣，右手握着手机，站在门里，面对门外。机位在门外。
>
> 镜头3：切至外卖员的近景，机位在门里他的位置，正面拍她。她没有争辩，右手解开头盔的卡扣，把头盔从头上摘下来，垂在身侧：头盔下是一头花白的短发，六十岁上下，雨水顺着脸往下流，还在喘气，又累又不好意思。灯光不变：走廊的白色日光灯在头顶，门里的暖黄光在脸的一侧。外卖员：黄色雨衣，花白短发，六十岁上下，左手提着外卖袋，站在门外，面对门里。机位在门里。
>
> 镜头4：同一机位，外卖员的近景。她把左手的外卖袋举到胸前递向镜头方向的门里，声音低但清楚，带着歉意，说：“对不起，钱我退给您。”说完看着他，手举着等他接。灯光不变：走廊的白色日光灯在头顶，门里的暖黄光在脸的一侧。外卖员：黄色雨衣，花白短发，六十岁上下，右手垂着头盔，站在门外，面对门里。机位在门里。
>
> 镜头5：切至固定中全景，机位在门外她的位置稍后，拍向门，她不在画面里。男人看了一眼镜头方向她湿透的鞋，然后侧身退到门边，把门拉到全开，门里的暖黄光照到门口湿的地砖上；他站在门边等她进来。画面停在敞开的门和门口地砖上的一小滩雨水上。灯光不变：走廊的白色日光灯在头顶，门里的暖黄光照出来。男人：四十多岁，短黑发，深蓝色睡衣，右手握着手机，站在门边，面对门外。机位在门外。
>
> 声音：雨声，头盔卡扣打开的一声，塑料袋的窸窣声，门轴的声音，说话时其他声音压低；无配乐，保持无字幕。时长：15秒。

</details>

#### Clip 05: 사직서

<sub>한국어 · 15 s · 16:9 · storyboard · slate: not rendered yet · ladder: Stretch: 4 beats (two at half), load 3, S = 2.1</sub>

**What people usually type:** *사이다 사직서 장면, 직장인 드라마, 시네마틱, 4K, 감동*

**What you know by shot two:** Shot one is a CEO signing at night and an employee walking in; shot two is her envelope landing on the page he is signing. Her line says he stole her report and was promoted for it.

<details>
<summary>The prompt the skill wrote</summary>

> 샷 1: 밤의 유리벽 임원실, 카메라는 문 쪽에서 책상을 향한다. 넓은 책상 뒤에서 대표가 문을 마주 보고 앉아 서류에 서명하고 있고, 문이 열려도 고개를 들지 않는다. 직원이 카메라 옆의 문을 열고 들어와 카메라에 등을 보인 채 책상 앞까지 걸어가 선다. 조명: 책상 스탠드 하나의 따뜻한 빛과 창밖 도시의 불빛. 대표: 오십 대 남성, 백발이 섞인 짧은 머리, 소매를 걷은 흰 셔츠, 책상 뒤에 앉아 문을 향해 있다. 직원: 이십 대 후반 여성, 어깨까지 오는 검은 머리, 회색 정장, 목에 건 사원증, 책상 앞에 서서 그를 향해 있다. 카메라는 문 쪽.
>
> 샷 2: 책상 위 클로즈업, 카메라는 책상 옆에서 낮게. 그녀의 손이 흰 봉투 하나를 그가 서명하던 서류 바로 위에 올려놓는다. 그의 펜이 종이 위에서 멈춘다. 같은 조명: 책상 스탠드 하나의 따뜻한 빛. 그녀의 손: 회색 정장 소매. 그의 손: 걷어 올린 흰 셔츠 소매, 검은 만년필.
>
> 샷 3: 그녀의 미디엄 숏, 카메라는 책상 뒤 그의 어깨 옆에서 낮게 올려다본다. 책상 앞에 선 그녀가 물러서지 않고 카메라 아래의 그를 내려다보며, 차분하지만 분명한 목소리로 말한다. 직원: “제 보고서, 이름만 바꾸셨더군요. 승진 축하드려요.” 말을 끝내고 잠시 그를 본다. 눈은 흔들리지 않고, 숨을 한 번 고른다. 같은 조명: 책상 스탠드 하나의 따뜻한 빛과 창밖 도시의 불빛. 직원: 이십 대 후반 여성, 어깨까지 오는 검은 머리, 회색 정장, 목에 건 사원증, 책상 앞에 서서 그를 내려다본다. 카메라는 책상 뒤.
>
> 샷 4: 대표의 클로즈업, 카메라는 그녀가 선 자리에서 그를 향한다. 펜을 쥔 손은 종이 위에 멈춘 채, 그가 천천히 고개를 들어 카메라 너머의 그녀를 올려다본다. 당황한 얼굴, 할 말을 찾지 못해 입술이 살짝 벌어진다. 같은 조명: 책상 스탠드 하나의 따뜻한 빛. 대표: 오십 대 남성, 백발이 섞인 짧은 머리, 소매를 걷은 흰 셔츠, 책상 뒤에 앉아 그녀를 올려다본다. 카메라는 책상 앞.
>
> 샷 5: 복도 쪽에서 본 와이드 숏, 유리문과 그 너머의 임원실. 그녀가 유리문을 밀고 나와 카메라 옆을 지나 화면 밖으로 걸어가고, 문이 천천히 닫힌다. 유리 너머 책상의 그는 앉은 채 봉투를 내려다보고 있다. 화면은 닫힌 유리문과 그 너머의 그에게서 멈춘다. 같은 조명: 책상 스탠드 하나의 따뜻한 빛과 창밖 도시의 불빛, 복도는 어둡다. 대표: 오십 대 남성, 백발이 섞인 짧은 머리, 소매를 걷은 흰 셔츠, 책상 뒤에 앉아 있다. 직원: 이십 대 후반 여성, 어깨까지 오는 검은 머리, 회색 정장, 문을 나선다. 카메라는 복도.
>
> 소리: 펜이 멈추는 순간, 봉투가 종이 위에 놓이는 소리, 구두 소리, 유리문이 닫히는 소리. 대사 중에는 다른 소리를 낮춘다. 음악 없음, 자막 없음.

</details>

#### Clip 06: 最後の一球

<sub>日本語 · 15 s · 16:9 · storyboard · slate: not rendered yet · ladder: Stretch: 4 beats (two at half), load 3, S = 2.1</sub>

**What people usually type:** *高校野球決勝ラストボール神作画、感動、エモい、有名アニメスタジオ風、4K*

**What you know by shot two:** Shot one is a pitcher on the mound in the rain with the crowd behind him; the sign, the wind-up and the swing say final pitch without a caption.

<details>
<summary>The prompt the skill wrote</summary>

> 手描きの2Dセルアニメーション。セル画のキャラクターを、水彩で描かれた背景画の上に置く。作画の密度が高く、限られた色数、フィルムの粒子が乗った質感。夏の決勝戦の九回裏、雨が降り始めた球場。
>
> ショット1：ホームベース側からマウンドの投手を正面に捉えたミディアムショット。肩で大きく息をして、帽子のつばから落ちる雨を見上げる。疲れているが、目は引かない。背景の観客席は塗りの中でざわめきの色が揺れ、旗が小さくはためく。光：曇天の平坦な光、濡れた土の反射。投手：泥だらけの白いユニフォーム、紺の帽子、帽子のつばから雨が落ちる、マウンドの上でホームベースを向いている。カメラはホームベース側。
>
> ショット2：カットして、マウンド側から見た捕手のミットのクローズアップ。低く構えたミットの横で、指が一度だけサインを出し、ミットが小さく二度叩かれる。作画は変わらない：手描きのセル画、水彩の背景。光は変わらない：曇天の平坦な光。ミット：濡れた茶色の革、ホームベースの後ろ、マウンドを向いている。カメラはマウンド側。
>
> ショット3：カットして、ホームベース側から投手のワインドアップ。振りかぶりからリリースまでを一コマ打ちのフルアニメーションで描き、腕の軌道は一枚のスミア、雨粒が腕の動きに引かれて流れる。カメラは背景画に対して固定。作画は変わらない：手描きのセル画、水彩の背景。光は変わらない：曇天の平坦な光、濡れた土の反射。投手：泥だらけの白いユニフォーム、紺の帽子、マウンドの上でホームベースを向いている。カメラはホームベース側。
>
> ショット4：カットして、捕手の後ろから見た打者の空振り。バットが空を切った瞬間、ボールがミットに収まる音と同時に画面全体を白黒反転のインパクトフレームにする。作画は変わらない：手描きのセル画、水彩の背景。光は変わらない：曇天の平坦な光。打者：白いヘルメット、灰色のユニフォーム、バッターボックスの中でマウンドを向いている。カメラは捕手の後ろ。
>
> ショット5：カットして、ホームベース側から、止め絵に近いショット。投手がマウンドで片膝をつき、顔を空に向けている。泣きそうな、しかし笑っている顔。動くのは雨と、息で上下する肩だけ。その前後のショットは二コマ打ち。作画は変わらない：手描きのセル画、水彩の背景。光は変わらない：曇天の平坦な光、濡れた土の反射。投手：泥だらけの白いユニフォーム、紺の帽子、帽子のつばから雨が落ちる、マウンドの上。カメラはホームベース側。
>
> 音：雨音、観客のざわめき、ミットの乾いた一音、そのあとは雨音と投手の息だけ。音楽なし、字幕なし。

</details>

#### Clip 07: Ещё один раунд

<sub>Русский · 15 s · 16:9 · storyboard · slate: not rendered yet · ladder: Stretch: 4 beats (two at half), load 3.5, S = 2.0</sub>

**What people usually type:** *тренер и боксёр перед решающим раундом, драма, кинематографично, эпично, 4k*

**What you know by shot two:** Shot one is a corner between rounds and a fighter who has stopped looking up; shot two is the trainer's line, and shot three shows who is watching from the stands.

<details>
<summary>The prompt the skill wrote</summary>

> Кадр 1. Статичный средний план на уровне канатов, камера со стороны зала: угол ринга между
> раундами, ночной боксёрский зал, зал в темноте. Боксёр сидит на табурете лицом к камере и к
> трибунам, тяжело дышит и смотрит в пол; плечи ходят от дыхания. Тренер стоит над ним,
> прижимает к его брови пакет со льдом и второй рукой держит его за затылок. Свет: одна лампа
> над рингом, жёсткий белый свет сверху, всё остальное в темноте. Боксёр: лет двадцать пять,
> короткие тёмные волосы, опухшая левая бровь, капа во рту, красные перчатки, сидит на табурете
> в углу лицом к трибунам. Тренер: за шестьдесят, седая щетина, серая футболка, стоит над ним,
> боком к камере. Белое полотенце висит на верхнем канате рядом с табуретом. Камера со стороны
> зала.
>
> Кадр 2. Крупный план тренера снизу, камера у плеча сидящего боксёра; тренер один в кадре,
> смотрит вниз, мимо камеры, на боксёра. Говорит ровно, без крика, устало и с любовью: «Хочешь
> бросить — бросай. Только мать смотрит.» Тот же свет: одна лампа над рингом, жёсткий белый свет
> сверху. Тренер: за шестьдесят, седая щетина, серая футболка, стоит в углу ринга над боксёром,
> лицом к нему. Камера снизу, у боксёра.
>
> Кадр 3. Кадр с трибун, камера из угла ринга смотрит в зал: среди сидящих зрителей стоит одна
> маленькая пожилая женщина, тёмное пальто накинуто на плечи, руки сцеплены у груди, губы
> беззвучно шевелятся. Зрители вокруг сидят и переговариваются. Тот же свет: лампа над рингом
> освещает ринг, трибуны в полутьме. Женщина: маленькая, пожилая, тёмное пальто на плечах, стоит
> среди сидящих зрителей лицом к рингу. Камера из угла ринга.
>
> Кадр 4. Крупный план боксёра, камера со стороны трибун; он один в кадре, сидит на табурете. Он
> поднимает глаза мимо камеры в сторону трибун, находит её и один раз кивает: тяжело, но решив.
> Тот же свет: одна лампа над рингом, жёсткий белый свет сверху. Боксёр: лет двадцать пять,
> короткие тёмные волосы, опухшая левая бровь, капа во рту, сидит на табурете в углу лицом к
> трибунам. Камера со стороны трибун.
>
> Кадр 5. Тот же средний план, что в первом кадре, камера со стороны зала. Гонг. Тренер хлопает
> его по плечу; боксёр встаёт и выходит из кадра вперёд, к центру ринга. Камера остаётся на
> пустом табурете под лампой и на полотенце, висящем на верхнем канате. Тот же свет: одна лампа
> над рингом, жёсткий белый свет сверху. Тренер: за шестьдесят, седая щетина, серая футболка,
> стоит в углу. Боксёр: красные перчатки, капа во рту, уходит из угла к центру ринга. Камера со
> стороны зала.
>
> Звук: тяжёлое дыхание, шум зала за кадром, звон гонга; во время реплики остальные звуки тише.
> Без музыки, без субтитров.

</details>

How the clips are made, the settings, the internal read behind each prompt and the render record are in the [front-page clip brief](https://github.com/Emily2040/seedance-2.0/blob/main/docs/FRONT_PAGE_CLIPS.md). A rendered clip proves that one take; it is not a promise about the next one.

## Start Here

After installation, tell your agent what happens and what must stay fixed:

> Use seedance-20. A person finishes a paper fan at a workbench. Keep it quiet,
> with one static shot and no music. Give me the prompt only.

One possible draft:

```text
Locked tabletop shot. Two hands
finish the last fold of a paper
fan and let go. The fan settles
on the wood. Hold still for one
beat. Warm desk-lamp light;
dry paper rustle and room tone.
No music.
```

**Why these choices:** one visible action, a clear endpoint, a fixed camera and
an explicit sound choice. Duration and aspect ratio belong in your provider's
controls when that surface owns them. This is an unrendered teaching example;
it does not establish successful folding, motion or audio generation.

For another treatment, choose calm observation, a playful gag or a step-by-step
demonstration. Tell the agent which one you want to keep. A draft can be revised
without submitting a paid generation request.

<!-- teaching-image:placement -->
<!-- installed-readme-gallery:start -->

![Slender hands with long pearl-blush nails, ivory tips and gold accents hold an ivory paper fan under a desk lamp.](assets/paper-fan-teaching.png)

*AI-generated teaching concept, not Seedance output.* The still illustrates
material, framing and light; it does not prove the action or sound will render.
[Image provenance and prompts](docs/PAPER_FAN_ART.md).

<!-- installed-readme-gallery:end -->

More examples: [performance and dialogue](references/performance-example-cards.md),
[product and process](references/product-example-cards.md),
[reference and continuity](references/continuity-example-cards.md).

## Choose a workflow

| What you have | What to provide next |
|---|---|
| A rough idea | The action, feeling and delivery format; ask for a few distinct choices. |
| A prompt to improve | The draft and constraints you want preserved. |
| Image, video or audio references | Actual files and the role each should control. |
| An accepted clip to continue | Its observed ending and the next action. |
| A result that missed | The failed requirement and your remaining revision budget. |

Start with the [quickstart](docs/QUICKSTART.md),
[reference workflow](references/reference-workflow.md),
[continuation guide](skills/seedance-continuation/SKILL.md) or
[retake protocol](references/retake-protocol.md).

## Install

Get a local copy, then run the installer from that folder. This example selects
Codex user scope; other clients are in the table below.

```bash
git clone https://github.com/Emily2040/seedance-2.0.git
cd seedance-2.0
python scripts/install_codex_skill.py --client codex --scope user
```

Download ZIP also works: extract it and run the installer inside that folder.
Restart your client, then select `seedance-20`. Review the
[security policy](SECURITY.md) before configuring optional provider tools.
Prompt preparation does not authorize paid generation.

Treat the table below as common local targets to verify in your own client, not a universal support guarantee.

| Platform | Typical install target (verify in your client) |
|---|---|
| Claude Code | `~/.claude/skills/seedance-20/` (personal) or `.claude/skills/seedance-20/` (project) — both via `scripts/install_codex_skill.py --dest` |
| Codex | project `.agents/skills/seedance-20/` or user `~/.agents/skills/seedance-20/`; no-option installer keeps its historical path |
| Google Antigravity | `.agents/skills/seedance-20/` (workspace) or `~/.gemini/config/skills/seedance-20/` (global across Antigravity products) |
| OpenClaw | workspace `skills/seedance-20/` or `~/.openclaw/skills/seedance-20/` via `openclaw skills install` (ClawHub-compatible; skills already carry `openclaw:` metadata) |
| Hermes Agent | `~/.hermes/skills/seedance-20/` (primary); a project `skills/seedance-20/` directory is discovered only after its parent is added to `skills.external_dirs` in `~/.hermes/config.yaml` |
| Gemini CLI-style workspace | `.gemini/skills/seedance-20/` |
| GitHub Copilot workspace | `.github/skills/seedance-20/` |
| Cursor workspace | `.cursor/skills/seedance-20/` |
| Windsurf workspace | `.windsurf/skills/seedance-20/` |
| Trae (ByteDance) | `.trae/skills/seedance-20/` |
| Qwen Code (Alibaba) | `.qwen/skills/seedance-20/` or `~/.qwen/skills/seedance-20/` |
| OpenCode | `.opencode/skills/seedance-20/` (also reads `.claude/skills/` and `.agents/skills/`) |
| Amp (Sourcegraph) | `.agents/skills/seedance-20/` or `~/.config/agents/skills/seedance-20/` |
| Goose (Block) | `.agents/skills/seedance-20/` (also `.goose/skills/seedance-20/`) |
| Junie (JetBrains) | `.junie/skills/seedance-20/` or `~/.junie/skills/seedance-20/` |

Several of these clients share the `.agents/skills/` convention — Codex, Google Antigravity, OpenCode, Amp, and Goose all read it — so one install under `.agents/skills/seedance-20/` can serve them together, and `.claude/skills/` is read by many as a compatibility path. Install once as the `seedance-20` root skill; its sub-skills and references resolve by relative path.

<details>
<summary>Installation by client, replacement and recovery details</summary>

Client support for Agent Skills is still tool-specific. See [observed compatibility and the host smoke protocol](https://github.com/Emily2040/seedance-2.0/blob/main/docs/HOST_COMPATIBILITY.md) for tested revisions and explicit gaps. Codex documents a skill as a directory with a required `SKILL.md`, optional `scripts/`, `references/`, `assets/`, and optional `agents/` metadata.

Codex scans `.agents/skills` locations from the working directory upward, plus user/admin/system skill locations. A repository root with `SKILL.md` is shaped like a skill folder, but it still needs to be installed/copied under a scanned skills directory or distributed as a plugin for automatic discovery.

### Step 1 — get the files

Every install path below runs from inside a local copy of this repository, so start here:

```bash
git clone https://github.com/Emily2040/seedance-2.0.git
cd seedance-2.0
```

Without `git` installed, use the green **Code → Download ZIP** button on the repository page, unzip it, and change into the unzipped folder instead. Nothing else on this page works until one of those two has happened.

### Step 2 — install it into your client

The installer is not Codex-only. Choose a client and scope below, or point `--dest` at another client's documented skills parent directory:

```bash
# Codex — user scope at ~/.agents/skills
python scripts/install_codex_skill.py --client codex --scope user

# Claude Code — personal install at ~/.claude/skills
python scripts/install_codex_skill.py --client claude-code --scope user

# One existing project, outside this source checkout
python scripts/install_codex_skill.py --client codex --scope project --project-root /path/to/project

# Any other client — use its documented skills parent directory
python scripts/install_codex_skill.py --dest /path/to/client/skills
```

Choose either `--dest` or `--client` with `--scope`; project scope requires an
existing `--project-root` and never guesses from your current directory. The
[scope guide](https://github.com/Emily2040/seedance-2.0/blob/main/docs/INSTALL_SCOPES.md)
explains the paths. No-option commands preserve the historical
`$CODEX_HOME/skills` or `~/.codex/skills` default for existing workflows; they do
not migrate old copies. Use the same destination options with the read-only
`install_doctor.py` before deciding on replacement.

The command stages and validates the repository before promoting it to
`<dest>/seedance-20`, then prints where it landed. Concurrent installers
sharing that destination are serialized. Add `--force` only to replace a
complete existing install; the previous copy remains available for rollback
until the validated stage is promoted. The durability, recovery and same-account
trust boundaries of that transaction are documented in
[installer internals](https://github.com/Emily2040/seedance-2.0/blob/main/docs/INSTALL_INTERNALS.md).
Restart your client afterwards so `seedance-20` appears in its skill list.

Installs skip the quarantined `references/migrated/` history, the image gallery (about 18 MB of PNGs), the test suite, and the network-capable evaluator. The installer replaces the omitted gallery embeds with one repository link, so the installed README does not contain broken local asset targets.

A destination inside this repository is refused rather than attempted because it would mutate the source authority domain while the payload is being authenticated. For a project-local install, run the script from the project you are installing into, by absolute path, as above.

For a client that imports a local skill folder, first prepare the filtered payload in a new staging directory outside this checkout:

```bash
python scripts/install_codex_skill.py --dest /absolute/path/to/new-staging/skills
```

Import the resulting `skills/seedance-20/` folder, or run the installer with
`--dest` set directly to the skills parent directory your client scans. Keep the
directory name `seedance-20` and its relative layout. A raw repository clone or
a client-managed GitHub import may include the evaluator, provider helpers, tests
and archives; it does not carry the installer's filtered-payload guarantee.
Inspect how that client packages files before using a direct import. See
[manual transfer and verification](https://github.com/Emily2040/seedance-2.0/blob/main/docs/MANUAL_INSTALL.md).

</details>

## Evidence status

- Repository checks cover routing, state, packaging, source integrity and
  declared document structure. Passing them is not a rendered-quality verdict.
- Live model scores and rendered-pilot results remain pending. The
  [comparison protocol](https://github.com/Emily2040/seedance-2.0/blob/main/references/outcome-comparison.md)
  and [48-attempt pilot plan](https://github.com/Emily2040/seedance-2.0/blob/main/evals/capped-rendered-pilot.md)
  describe how to collect evidence without inventing results.
- Six languages have full pages, quickstarts and vocabulary. Independent
  review is pending for all of them, and the
  [coverage contract](docs/LANGUAGE_COVERAGE.md) currently flags every
  language for review after recent edits. Availability is not parity.
- Provider capabilities are surface-specific and dated. Check the
  [surface matrix](references/platform-surface-matrix.md) before choosing controls.

## What it routes

Describe the situation; the root skill loads what that situation needs.

<details>
<summary>The common cases, and what each returns</summary>

| You say | It loads | You get |
|---|---|---|
| “I have a vague idea.” | [`seedance-interview-short`](skills/seedance-interview-short/SKILL.md) | A brief and a first draft, or one blocking question. |
| “I know the scene I want.” | [`seedance-prompt`](skills/seedance-prompt/SKILL.md) | A production-ready prompt. |
| “Make it short and strong.” | [`seedance-prompt-short`](skills/seedance-prompt-short/SKILL.md) | A compressed 30–100 word prompt. |
| “This is a longer story.” | [`seedance-sequence`](skills/seedance-sequence/SKILL.md) | Story spine, continuity bible, sequence map, and the Clip 01 contract and prompt. |
| “Continue this video.” | [`seedance-continuation`](skills/seedance-continuation/SKILL.md) | A continuation from accepted footage, or a request for the missing clip or final frame. |
| “I have image, video or audio references.” | [`reference-workflow`](references/reference-workflow.md) | A role map for every asset and what each must not transfer. |
| “Use this as first frame and that as last.” | [`first-last-frame-guide`](references/first-last-frame-guide.md) | A continuous transition with endpoint locks. |
| “Make it feel directed, not just cinematic.” | [`directing-engine`](references/directing-engine.md) | One intention per scene and a coherent camera, light, blocking, performance and sound setup. |
| “The take is 80% right.” | [`retake-protocol`](references/retake-protocol.md) | A triage verdict, a one-variable retake, and an attempt budget. |
| “It failed or looks bad.” | [`seedance-troubleshoot`](skills/seedance-troubleshoot/SKILL.md) | A root-cause diagnosis and a repaired prompt. |
| “This uses a character, brand or real person.” | [`seedance-copyright`](skills/seedance-copyright/SKILL.md) | A safer rewrite that keeps the creative function. |
| “I need this for a client, campaign or delivery.” | [`pro-filmmaking-standards`](references/pro-filmmaking-standards.md) | The production object the role needs, then the prompt that fits inside it. |
| “API, pricing, model ID, provider?” | [`api-workflow`](references/api-workflow.md) | A source-gated operational checklist. |

</details>

![Seedance 2.0 Skill OS operating diagram: seven gates feed the seedance-20 root, which routes to the core pipeline, governance, and multilingual vocabulary clusters, backed by the reference library and validators](assets/skill-map.svg)

The diagram is the contract: every request passes the gates, the root routes it,
and the validators hold the line. The complete map of 28 sub-skills and every
reference is in the [reference index](https://github.com/Emily2040/seedance-2.0/blob/main/docs/REFERENCE_INDEX.md);
the runtime authority is the load map in [`SKILL.md`](SKILL.md).

## Longer than one generation

Do not ask the skill to extend the original prompt. A continuation is based on
accepted generated footage, because Seedance may not end where the plan expected.

1. Describe the complete idea and how it ends.
2. The skill divides it into connected clips.
3. Generate Clip 01.
4. Return the generated clip or its final frame.
5. The skill records what actually happened.
6. It writes Clip 02 from the real ending.
7. Repeat until the planned final outcome is reached.

The project state is the source of truth, the clip contract is the current task,
and the prompt is compiled for that task only.

## Model line and platform facts

**This is a Seedance 2.0 skill.** ByteDance's
[official Seedance 2.5 model page](https://seed.bytedance.com/en/seedance2_5)
confirms a separate newer line, and
[Dreamina's official product page](https://dreamina.capcut.com/seedance/seedance-2-5)
says it is live on Dreamina.
Neither primary page gives an exact launch date, and API or other-surface availability was unconfirmed in the 2026-08-01 review.
The 2026-09-07 source review adds that Runway's API catalog now lists
`seedance2_5` separately, which does not establish account entitlement. Every
platform number in this repository is a 2.0 number. Establish which line a
surface runs before quoting one.

Before any factual claim about API availability, upload limits, pricing,
regions or model names, load [`api-status.md`](references/api-status.md) and
check its `last_verified` date. Treat every endpoint, model ID, price,
account requirement, face or reference policy, and output-rights claim as
provider-specific and recheck it live before implementation.

## Validation

<!-- installed-readme-validation:start -->

The validation toolchain supports **CPython 3.11 through 3.13**. CI exercises
both endpoints on Ubuntu and Windows; intermediate CPython 3.12 releases remain
inside the supported range. Python 3.10 and 3.14 are outside this lock's
supported range.

Install the two hash-pinned toolchains once, then run the release suite. The
offline source-metadata check runs with `--enforce-freshness` here so an old
checked-in registry stamp blocks a release; per-pull-request CI omits that flag
because metadata age depends on the calendar, not on the change under test.

```bash
python -m pip install --require-hashes --requirement requirements-validation.lock
python -I -S -B scripts/build_masthead_outlines.py --install-build-deps
```

```bash
python -I -S -B scripts/build_masthead_outlines.py --check
python scripts/validate_repo.py --release
```

`validate_repo.py` resolves the repository from its own file location and does
not call Git, so this also works from a Download ZIP extraction, from a nested
caller directory, and from a path containing spaces.
`python -I -S -B scripts/build_hero.py --check` proves the committed masthead
SVGs still match their generator; it runs in CI. What each check proves, and
what it cannot, is in the
[validation guide](https://github.com/Emily2040/seedance-2.0/blob/main/docs/VALIDATION.md).
Schema checks are not lineage proofs. The source-registry check does not fetch URLs
and does not prove that any upstream claim is still true. The architecture stress
gate is a structural gate, not a creativity judge.

### Git checkout-only hygiene

After the archive-safe checks, a maintainer working in a Git checkout should
also run:

```bash
git diff --check
```

This whitespace check requires Git metadata. Do not run it in a Download ZIP
extraction.

### Checked-in source metadata age

Whether `references/source-registry.md` is stale depends on today's date, not
on the change being tested, so it is not asked per pull request. The release
checklist asks it with `--enforce-freshness`, which blocks a release when the
checked-in stamp is older than 30 days, and `source-freshness-review.yml` asks
it every Monday on the default branch, keeping one tracking issue open while the
registry drifts. The job never edits the registry: re-stamping `last_verified`
without re-reading the sources would record a verification that never happened.

Model-in-the-loop evaluation lives outside offline CI. `python scripts/eval_run.py --limit 1`
prints an offline plan without network, credential read or ledger write. A live
run needs `--live`, an explicit `--max-calls` ceiling and a provider key from the
environment, and only a complete run may replace
[`evals/eval-run-ledger.md`](evals/eval-run-ledger.md). The validation guide
documents the frozen source manifest, blind discovery scoring and ledger
publication rules.

<!-- installed-readme-validation:end -->

## Design Standard

The front page follows an editorial design system rather than default AI
styling: warm ink and paper themes, an outlined serif wordmark with monospace
specification labels, a single amber accent and hairline rules. No gradients,
no glow, no badges, and no camera costume: no viewfinder marks, timecode,
record dots or aspect badges. Tokens and rules live in the
[frontend design system](references/frontend-design-system.md); the manual
acceptance pass is in [README design acceptance](docs/frontend-redesign.md).

The masthead pair is generated from one geometry by
[`scripts/build_hero.py`](scripts/build_hero.py), so the dark and light
variants cannot drift apart, and `python -I -S -B scripts/build_hero.py --check`
proves the committed SVGs still match the generator. The outlined display type
has its own sealed build toolchain: run
`python -I -S -B scripts/build_masthead_outlines.py --install-build-deps` once,
then `--check`; the full trust chain is in the
[masthead build guide](https://github.com/Emily2040/seedance-2.0/blob/main/docs/MASTHEAD_BUILD.md).

The clip gallery follows one rule: a clip on this page is Seedance 2.0 output
rendered from the prompt printed beneath it, captioned with surface, date and
settings, or its slate says it is not rendered yet. Slates are generated from
`data/front-page-clips.json` by `scripts/build_clip_posters.py`, whose
`--check` keeps them in step with the data.

The masthead is served through a `prefers-color-scheme` picture element; the
operating diagram `assets/skill-map.svg` carries its own background so it reads
on both themes. The page must stay readable on GitHub mobile, in dark mode and
at narrow widths. SVG assets carry `<title>` and `<desc>`, use internal CSS
only, and load no external fonts, scripts or resources.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history and [open issues](https://github.com/Emily2040/seedance-2.0/issues) to contribute.

## License

[MIT](LICENSE). Maintained by [Emily / Iamemily2050](https://github.com/Emily2040).
