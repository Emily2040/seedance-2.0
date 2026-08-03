# Japanese Vocabulary

Use this reference for Japanese Seedance prompt wording, role binding, and compact prompt compression. Keep reference tags unchanged: `@Image1`, `@Video1`, and `@Audio1` stay literal.

| Function | Japanese | English meaning |
|---|---|---|
| Role | `@Image1を最初のフレームとして使う` | use Image1 as the first frame |
| Role | `@Image2を最後のフレームとして使う` | use Image2 as the last frame |
| Role | `@Image1で人物の同一性を固定する` | Image1 locks character identity |
| Role | `@Video1はカメラの動きのみ参照` | Video1 controls camera movement only |
| Role | `@Video1は動作リズムのみ参照` | Video1 controls action rhythm only |
| Role | `@Audio1はテンポと雰囲気のみ参照` | Audio1 controls tempo and mood only |
| FirstLastFrame | `最初のフレームを変更しない` | keep the first frame unchanged |
| FirstLastFrame | `最後のフレームを最終目標にする` | use the last frame as the final target |
| FirstLastFrame | `途中の動きを連続させ、ジャンプカットしない` | continuous in-between motion, no jump cut |
| FirstLastFrame | `同じ人物、服装、部屋の構造を保つ` | preserve same character, outfit, and room layout |
| Camera | `ゆっくりドリーイン` | slow push-in |
| Camera | `後退して空間を見せる` | pull back to reveal the space |
| Camera | `安定した横移動トラッキング` | stable lateral tracking |
| Camera | `固定の中景` | locked medium shot |
| Camera | `マクロのクローズアップ` | macro close-up |
| Camera | `低いアングルから見上げる` | low-angle shot |
| Camera | `肩越しのショット` | over-the-shoulder shot |
| Camera | `軽い手持ちの呼吸感` | handheld shot with slight breathing sway |
| Shot | `中近景` | medium close-up |
| Shot | `広い導入ショット` | wide establishing shot |
| Shot | `四分の三の横顔` | three-quarter profile |
| Shot | `三分割法で構図` | rule-of-thirds composition |
| Shot | `日の丸構図、主体中央` | centered composition, subject in the middle |
| Shot | `大きな余白、孤独感` | large negative space, isolation |
| Shot | `前ボケ越しに被写体` | subject seen past foreground blur |
| Shot | `誘導線で奥へ` | leading lines pulling into depth |
| Camera | `ワンカット長回し` | one continuous long take |
| Camera | `ピン送りで視線を移す` | rack focus shifts the eye |
| Lighting | `木漏れ日` | sunlight dappled through leaves |
| Lens | `24mmの広角で空間を強調` | 24mm wide lens spatial feel |
| Lens | `50mmの自然なポートレート感` | 50mm natural portrait feel |
| Lens | `マクロレンズで素材の細部を見せる` | macro lens for material detail |
| Lighting | `柔らかい逆光` | soft backlight |
| Lighting | `左からの暖かいプラクティカルライト` | warm practical light from left |
| Lighting | `冷たい月明かりの輪郭光` | cool moon rim light |
| Lighting | `薄い霧を通るボリュームライト` | volumetric light through mist |
| Lighting | `濡れた路面にネオンが反射する` | wet pavement reflects neon |
| Motion | `足元の霧が静かに広がる` | fog spreads around the feet |
| Motion | `水滴が集まり下へ流れる` | droplets merge and slide down |
| Motion | `ゆっくり振り向いて止まる` | slow head turn and stop |
| Motion | `布が動きに合わせて自然に揺れる` | fabric moves naturally with action |
| VFX | `金色の粒子が舞い上がり消えていく` | gold particles rise and dissipate |
| VFX | `青い電気アークが縁を這う` | blue arcs crawl along the edge |
| VFX | `光の筋が素材の表面を横切る` | light sweep crosses the material surface |
| Audio | `短く明瞭な一言` | one short clear spoken line |
| Audio | `音楽なし、低い環境音のみ` | no music, low ambience only |
| Audio | `セリフ中はカメラを固定する` | locked camera during dialogue |
| Audio | `足音をビートに合わせる` | footsteps hit the beat |
| Audio | `台詞はです・ます体で` | dialogue in polite です・ます体 |
| Audio | `台詞は敬語で、格式高く` | dialogue in formal 敬語 |
| Audio | `台詞は普通体で、くだけて` | dialogue in plain 普通体 |
| Audio | `一人称は「僕」で統一する` | first-person pronoun fixed to 僕 |
| Audio | `二人の文体の関係を保つ` | keep the register relationship between the two characters |
| Text | `字幕、透かし、余計な文字を追加しない` | no subtitles, watermark, or extra text |
| Editing | `ショットを続ける` | continue the shot |
| Editing | `5秒延長する` | extend by five seconds |
| Editing | `失敗した部分だけ置き換える` | replace only the failed segment |
| Constraint | `ロゴ、ラベル、形、色を厳密に保つ` | preserve logo, label, shape, and color |
| Constraint | `変化は動き、光、カメラだけにする` | change only motion, light, and camera |
| Constraint | `人物、場所、ブランドをコピーしない` | do not copy people, place, or brands |
| Safety | `オリジナルの人物に置き換える` | replace with an original character |
| Safety | `許可済みの参照だけを使う` | use only authorized references |
| Safety | `創作上の役割を残し、保護された同一性は残さない` | preserve creative function, not protected identity |

## Compact Template

`@Image1を参照として、[被写体/商品/顔/ロゴ]を正確に維持する。変化は[動き/光/カメラ]のみ。カメラ：[一つの動き]。音：[音声指示]。`

## Multimodal Template

`@Image1でオリジナル人物を固定する。@Video1はカメラの動きのみ参照し、人物・場所・ブランドはコピーしない。@Audio1はテンポと雰囲気のみ参照する。`

## Timeline Template

The bracket-timeline skeleton is the Chinese community's long-prompt pattern (`vocab/zh` Timeline Template, field-observed on 即梦/Dreamina). Below is the same structure in Japanese: the *structure* is what is field-observed, a Japanese-specific version is not independently reported, so treat it as a starting scaffold rather than a community guarantee.

```
【スタイル】[媒介・質感・色調を一文で]
【タイムライン】0-3s：[画面＋カメラ＋音]；3-6s：[画面＋カメラ＋音]；6-10s：[画面＋カメラ＋音]
【音】[台詞／環境音／効果音／音楽なし]
【参照】@Image1で人物の同一性を固定；@Video1はカメラの動きのみ参照；@Audio1はテンポのみ参照
```

## Sequence and Continuation Phrases

Use these when the Japanese prompt is part of a v6 sequence project, continuation, or localized delivery workflow.

| Function | Japanese | English meaning |
|---|---|---|
| Role | `採用済み動画をプロジェクトの正史にする` | accepted footage is the project truth |
| Role | `前の実際の終点から続ける` | continue from the actual previous ending |
| Role | `前の動作を繰り返さない` | do not replay the previous action |
| Role | `このクリップでは現在のタスクだけを見せる` | this clip shows only the current task |
| Role | `後の展開はまだ見せない` | future story beats do not appear yet |
| FirstLastFrame | `前クリップの最後のフレームを開始点にする` | use previous final frame as starting point |
| FirstLastFrame | `新しい終点の姿勢で止まる` | settle into the new final pose |
| Motion | `前の進行中の動きの方向を保つ` | preserve previous open motion vector |
| Motion | `静止状態から動き始める` | action starts from a still state |
| Editing | `Clip 02の続き用プロンプト` | continuation prompt for Clip 02 |
| Editing | `終端のズレだけを修正し、前半は変えない` | repair only tail drift, not the first half |
| Constraint | `完了した動作を繰り返さない` | completed actions must not repeat |
| Constraint | `未発生の内容を先に出さない` | unshown future events must not appear early |
| Text | `画面内の文字は入れず、字幕は後処理で追加` | keep image textless; subtitles added in post |
| Text | `日本語コピーと法務文言は編集で追加` | Japanese copy and legal text added in edit |
| Safety | `創作上の役割だけ残し、オリジナル人物に置き換える` | preserve creative function with original identity |

## Dialogue Notes

Field-observed from 2026 community testing (note.com, Qiita); test per surface, never promise results. Japanese lip-sync is weaker than Mandarin and English.

- No separate word-count is documented; treat Japanese as the weaker tier. Keep to one short line (一言), about one breath.
- Japanese is mora-timed, so "word count" misleads - judge by sentence length and clarity, not word number.
- 台詞の書式: 話者名＋動作＋「台詞」. Example: `男：ゆっくり顔を上げて「もう一度だけ」`. Keep the spoken line inside 「 」 so the model can separate performance direction from the words to be spoken.
- Reference tags stay Latin inside a Japanese prompt: `@Image1`, never `@画像1`. No surface documents translated Japanese tags; the localized `@图片1` family belongs to Chinese-UI surfaces only.
- For reliable Japanese voice, prefer a voice reference (attach the spoken line so the model lip-syncs to it) or plan a post-dub.

## Register (文体)

Japanese dialogue commits to a register the same way Korean commits to a speech level: leaving it unstated does not avoid the decision, it hands the decision to the model. Declare one per speaker.

This is a budget decision as well as a characterization one. Japanese is mora-timed, the sync budget in [audio-guide](../audio-guide.md) is spent per mora, and the same sentence costs a different number of them at each register:

| 同じ意味 (same meaning) | 普通体 → です・ます体 → 敬語, モーラ数 (mora count) |
|---|---|
| thank you | ありがとう (5) → ありがとうございます (10) |
| understood | 分かった (4) → 分かりました (6) → かしこまりました (8) |
| please come | 来て (2) → 来てください (6) → お越しください (7) |
| I'll do it | やる (2) → やります (4) → いたします (5) |

です・ます体 runs roughly 1.5x the morae of 普通体 for identical content, and full 敬語 can double it. On a language already flagged as the weaker sync tier, an unconsidered formal register can spend the whole budget on politeness endings.

Choosing:

- **敬語 (尊敬語・謙譲語)** - service staff to customers, corporate and public-facing VO, formal announcements, a subordinate addressing a superior. Most morae.
- **です・ます体** - the safe default for a single-line commercial, presenter-to-camera, or a stranger-to-stranger exchange. Polite without the full honorific cost.
- **普通体 (だ体)** - close friends, family, internal monologue, an older speaker to a younger one. Shortest, and too blunt for a Japanese viewer where the relationship does not license it.

One axis is unique to Japanese: the first-person pronoun is itself register. 私 / 僕 / 俺 / わたくし each cast a different speaker, and a pronoun that contradicts the declared register (俺 inside 敬語, わたくし inside 普通体) reads as a dubbing error, not a character choice.

With two speakers, the pair of registers *is* the relationship: a boss in 普通体 answered in です・ます体 reads as hierarchy, both in です・ます体 reads as peers or strangers. Keep each character's register and pronoun consistent across a sequence - drifting mid-project reads as a translation error, and it is the kind of continuity that no frame-level QC catches.

If the user has not stated a register and the relationship does not imply one, ask once rather than defaulting silently; it is one question and it changes both the performance and the mora budget.

## Aesthetic Registers (美学)

Japanese carries aesthetic concepts with no one-word English equivalent. They are legitimate intent words — but they are intent, not instruction: alone in a prompt they behave like any feel-word and destabilize the output. Use them the way the Slop Traps table repairs feel-words — name the register, then spend the words on the physical elements that produce it.

| Register | Decompose into |
|---|---|
| 間 (ma — the charged pause) | a held frame, an action that stops before the cut, one beat of room tone with no dialogue: `動作が止まり、二拍の沈黙、その後カットせずに保持` |
| 侘び寂び (imperfect, weathered beauty) | material and age, not mood: `欠けた陶器、古い木の質感、苔、曇天の柔らかい光` |
| もののあわれ (the pathos of passing things) | one transient physical event given the whole shot: `散る桜が一枚、水面に落ちて波紋が消えるまで` |
| 幽玄 (profound, veiled depth) | occlusion and distance: `薄い霧、遠景の人影、輪郭だけの照明、音は遠い鐘のみ` |
| 粋 (understated urban elegance) | restraint in costume and gesture: `無地の着流し、最小限の所作、視線だけの反応` |
| 木漏れ日 (light through leaves) | already physical — usable as-is in the Lighting slot |

## Slop Traps

コミュニティの共通認識：抽象的な形容詞は、モデルがどの要素を強調すべきか判断できないため、出力を不安定にする。感覚語は、その感覚を生む物理要素（動作動詞＋速度＋視点、光源＋方向＋挙動）に分解する。

| 決まり文句 | 書き換え |
|---|---|
| `映画のような / 映画的` | ショットサイズ・カメラの動き・光源・色調で書く：`広い導入ショット、ゆっくりドリーイン、低い夕陽、ティール＆オレンジ` |
| `エモい` | 感情を生む物理要素で書く：`夕暮れの逆光、長い影、遠くの電車の音` |
| `雰囲気のある` | 雰囲気を作る要素を名指しする：`薄い霧、濡れた路面の反射、低い環境音` |
| `美しい` | 色・質感・構図・光の挙動で書く |
| `壮大な` | 物理的スケールで書く：群衆の人数、被写体との距離、建物の高さ |
| `高品質 / 高画質 / 8K` | 削除する。解像度は設定であり、文章ではない |
| `圧倒的な` | 圧倒する一つの対比か種明かし（リビール）を書く |
| `幻想的な`（単独） | 幻想を作る要素を書く：`漂う塵、ボリュームライト、ゆっくりした浮遊` |
| `神作画` | 動きで書く：`滑らかなフルアニメーションの一連の動き、そのあと静止` |
| `かっこいい` | 具体的なポーズ・動き・カメラで書く |
| `ダイナミック` | 動きの種類・速度・終点で書く |
