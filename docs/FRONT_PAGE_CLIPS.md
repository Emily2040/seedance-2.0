# Front-page clips: the shooting brief

Status: seven prompts written 2026-09-26, none rendered yet. The data behind
this page and the README slates is `data/front-page-clips.json`; the slates are
built by `scripts/build_clip_posters.py`, and `--check` keeps them in step.

## Why these clips exist

People share what they can see. The front page therefore shows Seedance 2.0
output made from prompts this skill wrote, in the languages the skill writes,
with the exact prompt beneath each clip and, above it, the kind of brief people
usually type. The difference is visible before it is explained. Nothing on the
page is a mock-up: a clip is either rendered from the published prompt or its
slate says it is not.

## How to render them

- Surface: Seedance 2.0, text to video, no reference assets. One generation per
  clip. No editing, colour work, sound replacement or upscaling afterwards.
- Settings live in the tool, not in the prompt: aspect ratio 16:9, the duration
  listed on each card (choose the nearest value the tool offers and note it),
  audio generation on, 720p or the tool's default. Clip 04 also carries the
  documented Chinese prose echo 时长：15秒, which is a reinforcement, not a
  control.
- Paste each prompt exactly as printed. Do not translate it, add quality words,
  or append a style name.
- One take is the default. If a take misses the review checklist, generate one
  more with the same prompt and settings; publish the better take and record
  both in the table at the end of this file. A third attempt is a decision the
  maintainer makes, not a default.
- Return the files by dragging them into a comment on the open pull request.
  GitHub converts each upload to a hosted asset URL that the README can embed;
  the session watching that pull request reads the URLs from the comment,
  replaces the slates, and writes the caption from the record below. Name the
  files as listed on each card so the mapping is unambiguous.

## What each caption will say

Once a clip is in place its caption states, in one line: the surface and model
line, the date, the duration and ratio actually set, and the take number if it
was not the first. Anything the take did not do that the prompt asked for is
written under it rather than hidden. That is the same rule the example cards
already follow.

## The seven clips

Each card gives the typical brief (what the clip would have been made from
without the skill), the internal read the skill used, the prompt as written,
the shape and ladder rung from `references/multishot-grammar.md`, and the review
checklist for the returned take.

### Clip 01: The paper fan

- Language: English. Duration 8 s. 16:9. Shape: continuous. File: `clip-01-paper-fan.mp4`.
- Typical brief: *cinematic close up of hands folding a paper fan, warm lighting, 4k, ASMR*
- Internal read (non-narrative lane). Utility intent: show one complete fold and
  the release, with the settle as the visible endpoint and the paper's dry
  sound as the only event. Refusal: no invented sentiment, no reveal of a
  face, no music cue.

> Locked tabletop shot. Two hands finish the last fold of a paper fan and let go. The fan settles on the wood. Hold still for one beat. Warm desk-lamp light; dry paper rustle and room tone. No music.

Review: the last fold completes and the hands release; the fan settles and the
frame holds with no camera move; no music, no on-screen text.

### Clip 02: Night bakery, three shots

- Language: English. Duration 15 s. 16:9. Shape: storyboard. Rung: Safe (3 beats, load 1.5, S = 3.3). File: `clip-02-night-bakery.mp4`.
- Typical brief: *artisan bakery b-roll, bread being scored, cinematic warm light, slow motion, multiple shots*
- Internal read (non-narrative lane). Utility intent: three stages of one loaf,
  each with a completed physical state (dust in light, the cut opening, the
  crust filling the frame). Refusal: no baker's face, no tired-craftsman story,
  no slow motion.
- Load: the scoring is contact that must land (1); the third shot's push-in is
  the only camera move (0.5). S = 15 ÷ 4.5 = 3.3.

> Shot 1. Locked close-up inside a dark bakery before dawn: one bare bulb throws a shaft of light across a floured wooden bench, and flour dust drifts through the beam. Shot 2. Cut to a medium shot at bench height: a baker's hands score a proofed loaf with a razor blade in one clean curve, the cut opening as the blade passes, a little flour lifting off the knuckles. Shot 3. Cut to the oven door swinging open toward camera, then a slow push-in through the heat shimmer until the loaf's dark crust fills the frame; hold there. Warm tungsten light only; the rest of the room falls to black. Sound: the blade through dough, the oven door's hinge, a low burner roar. No music, no subtitles.

Review: three distinct framings in this order with a visible cut between each;
the scoring cut opens as the blade passes; one push-in only, in the third shot,
ending on the crust.

### Clip 03: 最后一碗

- Language: Chinese. Duration 10 s. 16:9. Shape: continuous. File: `clip-03-last-bowl.mp4`.
- Typical brief: *深夜小店老板娘温暖治愈的一幕，电影感，氛围感，8K*
- Internal read (narrative lane, compressed). Turn: closing up to keeping one
  seat open. POV: the late customer at the door, so the camera sits at counter
  height facing her. Hidden want: to feed someone without admitting she waited.
  Tactic: call it the last bowl. Visible suppressed behaviour: the hand stops
  mid-fold before she looks up. Non-transferable detail: a pair of chopsticks
  already laid at one seat (authored choice). Stock solution refused: no warm
  smile close-up with music; she says the line flat and goes back to wiping.

> 固定中景，镜头与柜台同高。深夜的小粉店，卷帘门已经拉下一半，柜台上只剩一盏灯。老板娘（五十多岁，围裙，袖口挽起）正把抹布叠好，手停在半空，抬眼看向门口，把一副早就摆好的筷子往前推了推。老板娘平静地说：“还有最后一碗，坐吧。”说完低头继续擦柜台，嘴角不动。灯光只有柜台上方那一盏暖光灯，门外是冷色的路灯。声音：风扇的嗡嗡声，汤锅轻微的咕嘟声，说话时其他声音压低；无配乐。保持无字幕。

Review: the chopsticks are pushed forward before the line; the line is audible
Mandarin and the mouth matches it; no smile close-up, no music, no subtitles.

### Clip 04: 雨夜面摊，三个镜头

- Language: Chinese. Duration 15 s. 16:9. Shape: storyboard. Rung: Safe (3 beats, load 2, S = 3.0). File: `clip-04-rain-noodle-stall.mp4`.
- Typical brief: *雨夜面摊，烟火气，运镜丝滑，多个镜头，大片感*
- Internal read (non-narrative lane). Utility intent: three completed physical
  states of one bowl of noodles under one lamp in the rain. Refusal: no
  customer's face, no vendor backstory, no camera moves.
- Load: noodles landing in the water (1) and the bowl handoff (1) are contact
  that must land; every shot is locked. S = 15 ÷ 5 = 3.0. The prose echo
  时长：15秒 follows the documented tip; the duration is still set in the tool.

> 镜头1：固定特写，雨夜路边面摊，大锅上的蒸汽涌进头顶那盏白炽灯的光里，雨丝在光里划过，锅沿挂着水珠。镜头2：镜头切至摊主的中景，摊主（六十岁左右的男人，白背心，毛巾搭肩）抓起一把面甩开、抖散，落进滚水里，水面翻起一圈白沫，他随手盖上锅盖。镜头3：镜头切至柜面的低角度，一碗浇了葱花和辣油的面被推到画面前方，一只湿漉漉的手接过碗，碗停在画面中央，蒸汽继续往上冒。全片只有摊头这一盏灯，背景是雨里模糊的车灯。声音：雨声、油锅和滚水的声音、碗底在木板上划过的声音；无配乐，保持无字幕。时长：15秒。

Review: 镜头1、2、3 appear in this order with a visible cut between each; the
noodles land in the water and the handoff completes; no camera movement inside
any shot; no music; no subtitles.

### Clip 05: 새벽 세 시 편의점

- Language: Korean. Duration 10 s. 16:9. Shape: continuous. File: `clip-05-three-am-store.mp4`.
- Typical brief: *새벽 편의점 알바생 감성 영상, 시네마틱, 비 오는 날, 고양이*
- Internal read (non-narrative lane, comic timing). Utility intent: the
  habitual greeting lands on the wrong customer; the joke is the order of
  chime, line, look. Refusal: no loneliness montage, no sad music, no second
  human.

> 카메라는 계산대 높이에 고정된 미디엄 숏. 새벽 세 시의 편의점, 창밖에는 비가 내리고 냉장고 불빛이 통로를 비춘다. 야간 아르바이트생(이십 대 여성, 조끼 유니폼, 머리를 대충 묶음)이 계산대 뒤에서 컵라면 진열을 정리하고 있다. 출입문 차임벨이 울리고, 그녀는 고개를 들지 않은 채 습관처럼 말한다. 아르바이트생: “어서 오세요.” 대답이 없자 고개를 들어 문 쪽을 본다. 문 앞 매트 위에 젖은 고양이 한 마리가 앉아 그녀를 올려다보고 있다. 그녀는 아무 말 없이 반쯤 웃은 얼굴로 멈추고, 카메라는 그 표정에서 끝난다. 조명은 편의점 형광등과 창밖의 파란 새벽빛뿐. 소리: 차임벨, 유리창을 때리는 빗소리, 냉장고의 낮은 웅웅거림, 대사 중에는 다른 소리를 낮춘다. 음악 없음, 자막 없음.

Review: chime first, line second, look third; the line is Korean and audible
with a still head; one wet cat on the mat; the clip ends on her face.

### Clip 06: 踏切、夕方

- Language: Japanese. Duration 10 s. 16:9. Shape: continuous, 2D animation. File: `clip-06-railway-crossing.mp4`.
- Typical brief: *夏の夕方、踏切で電車を待つ少女、エモいアニメ風、有名スタジオっぽく*
  (the studio name people usually attach is exactly what the copyright route
  removes; the prompt names technique, era and palette instead).
- Internal read (non-narrative lane, observation). Utility intent: the train's
  passing as drawn light on a face, and the empty far side as the only event.
  Refusal: no dialogue, no tears, no photographic lens language.

> 手描きの2Dセルアニメーション。セル画で描かれた人物を、水彩で塗られた背景の上に置く。1990年代のテレビアニメ調で、フィルムの粒子がわずかに乗った質感、限られた色数。夕方の住宅地の踏切。麦わら帽子をかぶった少女（十代前半、白いワンピース、片手に金魚の入った袋）が遮断機の前で立ち止まる。警報機が鳴り、電車が画面を横切る。車窓の光が少女の顔に描かれた縞になって明滅し、髪とワンピースの裾が風で遅れて揺れ、電車が抜けた後もひと呼吸だけ揺れが残る。踏切の向こう側には誰もいない。少女は小さく息を吐き、そのまま止め絵になる。カメラは背景の絵に対して固定。動きは基本二コマ打ち、電車の通過だけ背景のスクロールとスピード線で見せる。光は描かれた二段階のセル影、電車の窓明かりは顔の上の白い帯として描く。音：踏切の警報音、電車の通過音、通り過ぎたあとは蝉の声だけが残る。音楽なし、字幕なし。

Review: reads as drawn 2D cel animation over a painted background, not
photoreal or 3D; the train passes as background scroll with light bands on her
face and the hair settles after; the far side is empty and the clip ends on a
held frame; no music.

### Clip 07: Чай ещё горячий

- Language: Russian. Duration 10 s. 16:9. Shape: continuous. File: `clip-07-tea-still-hot.mp4`.
- Typical brief: *уютная кухня, дедушка пьёт чай, кинематографично, атмосферно, 4k*
- Internal read (narrative lane, compressed). Turn: a man alone to a place
  kept for someone. POV: the person he is talking to, off-frame. Hidden want:
  not to make the invitation a moment. Visible suppressed behaviour: he does
  not look up; the hand stays on the glass a moment too long. Non-transferable
  detail: two glasses in metal подстаканники, both steaming (authored choice).
  Stock solution refused: no eye contact, no music, no close-up on a tear.

> Статичный средний план на уровне стола. Зимний вечер, маленькая кухня в старой квартире: за окном синие сумерки и снег, горит только лампа над столом. Пожилой мужчина (за шестьдесят, вязаный жилет, очки сдвинуты на лоб) сидит боком к камере и режет хлеб. На столе два стакана чая в металлических подстаканниках, над обоими пар. Не поднимая глаз, он двигает второй стакан к пустому стулу на краю кадра и говорит ровно, почти буднично. Мужчина: «Садись. Чай ещё горячий.» Потом возвращается к хлебу, и только рука на мгновение задерживается на стакане. Свет: тёплая лампа над столом и холодный свет из окна. Звук: тиканье кухонных часов, нож по доске, тихий стук стакана о клеёнку; во время реплики остальные звуки тише. Без музыки, без субтитров.

Review: the glass moves toward the empty chair before the line and his eyes
stay down; the line is Russian and audible; two glasses, both steaming; the
hand pauses after the line; no music, no subtitles.

## Optional: one true before-and-after

If credits allow one more generation, render clip 01's typical brief exactly as
printed (*cinematic close up of hands folding a paper fan, warm lighting, 4k,
ASMR*) with the same settings. Shown side by side with the directed take, it
is the clearest single image of what the skill changes. It is optional; the
text contrast on each card already carries the point.

## Render record

| Clip | Date | Surface and model line | Duration and ratio set | Take used | Deviations from the prompt |
|---|---|---|---|---|---|
| 01 | pending | | | | |
| 02 | pending | | | | |
| 03 | pending | | | | |
| 04 | pending | | | | |
| 05 | pending | | | | |
| 06 | pending | | | | |
| 07 | pending | | | | |
