# Japanese Vocabulary

Use this reference for Japanese Seedance prompt wording, role binding, and compact prompt compression. Keep reference tags unchanged: `[Image1]`, `[Video1]`, and `[Audio1]` stay literal.

| Function | Japanese | English meaning |
|---|---|---|
| Role | `[Image1]を最初のフレームとして使う` | use Image1 as the first frame |
| Role | `[Image2]を最後のフレームとして使う` | use Image2 as the last frame |
| Role | `[Image1]で人物の同一性を固定する` | Image1 locks character identity |
| Role | `[Video1]はカメラの動きのみ参照` | Video1 controls camera movement only |
| Role | `[Video1]は動作リズムのみ参照` | Video1 controls action rhythm only |
| Role | `[Audio1]はテンポと雰囲気のみ参照` | Audio1 controls tempo and mood only |
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
| Shot | `三分の二の横顔` | three-quarter profile |
| Lens | `24mmの広角で空間を強調` | 24mm wide lens spatial feel |
| Lens | `50mmの自然なポートレート感` | 50mm natural portrait feel |
| Lens | `マクロレンズで素材の細部を見せる` | macro lens for material detail |
| Lighting | `柔らかい逆光` | soft backlight |
| Lighting | `左からの暖かい実用照明` | warm practical light from left |
| Lighting | `冷たい月明かりの輪郭光` | cool moon rim light |
| Lighting | `薄い霧を通るボリューム光` | volumetric light through mist |
| Lighting | `濡れた路面にネオンが反射する` | wet pavement reflects neon |
| Motion | `足元の霧が静かに広がる` | fog spreads around the feet |
| Motion | `水滴が集まり下へ流れる` | droplets merge and slide down |
| Motion | `ゆっくり顔を向けて止まる` | slow head turn and stop |
| Motion | `布が動きに合わせて自然に揺れる` | fabric moves naturally with action |
| VFX | `金色の粒子が舞い上がり消えていく` | gold particles rise and dissipate |
| VFX | `青い電気の弧が縁を這う` | blue arcs crawl along the edge |
| VFX | `光の筋が素材の表面を横切る` | light sweep crosses the material surface |
| Audio | `短く明瞭な一言` | one short clear spoken line |
| Audio | `音楽なし、低い環境音のみ` | no music, low ambience only |
| Audio | `セリフ中はカメラを固定する` | locked camera during dialogue |
| Audio | `足音をビートに合わせる` | footsteps hit the beat |
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

`[Image1]を参照として、[主体/商品/顔/ロゴ]を正確に維持する。変化は[動き/光/カメラ]のみ。カメラ：[一つの動き]。音：[音声指示]。`

## Multimodal Template

`[Image1]でオリジナル人物を固定する。[Video1]はカメラの動きのみ参照し、人物・場所・ブランドはコピーしない。[Audio1]はテンポと雰囲気のみ参照する。`

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
| Motion | `前の開いた動きの方向を保つ` | preserve previous open motion vector |
| Motion | `静止状態から動き始める` | action starts from a still state |
| Editing | `Clip 02の続き用プロンプト` | continuation prompt for Clip 02 |
| Editing | `終端のズレだけを修正し、前半は変えない` | repair only tail drift, not the first half |
| Constraint | `完了した動作を繰り返さない` | completed actions must not repeat |
| Constraint | `未発生の内容を先に出さない` | unshown future events must not appear early |
| Text | `画面内の文字は入れず、字幕は後処理で追加` | keep image textless; subtitles added in post |
| Text | `日本語コピーと法務文言は編集で追加` | Japanese copy and legal text added in edit |
| Safety | `創作上の役割だけ残し、オリジナル人物に置き換える` | preserve creative function with original identity |

## Slop Traps

コミュニティの共通認識：抽象的な形容詞は、モデルがどの要素を強調すべきか判断できず、出力を不安定にする。感覚語は、その感覚を生む物理要素（動作動詞＋速度＋視点、光源＋方向＋挙動）に分解する。

| 決まり文句 | 書き換え |
|---|---|
| `映画のような / 映画的` | ショットサイズ・カメラの動き・光源・色調で書く：`広い導入ショット、ゆっくりドリーイン、低い夕陽、ティール＆オレンジ` |
| `エモい` | 感情を生む物理要素で書く：`夕暮れの逆光、長い影、遠くの電車の音` |
| `雰囲気のある` | 雰囲気を作る要素を名指しする：`薄い霧、濡れた路面の反射、低い環境音` |
| `美しい` | 色・質感・構図・光の挙動で書く |
| `壮大な` | 物理的スケールで書く：群衆の人数、レンズの距離、建物の高さ |
| `高品質 / 高画質 / 8K` | 削除する。解像度は設定であり、文章ではない |
| `圧倒的な` | 圧倒する一つの対比か開示を書く |
| `幻想的な`（単独） | 幻想を作る要素を書く：`漂う塵、ボリューム光、ゆっくりした浮遊` |
| `神作画` | 動きで書く：`滑らかなフルアニメーションの一連の動き、そのあと静止` |
| `かっこいい` | 具体的なポーズ・動き・カメラで書く |
| `ダイナミック` | 動きの種類・速度・終点で書く |
