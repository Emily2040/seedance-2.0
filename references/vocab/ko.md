# Korean Vocabulary

Use this reference for Korean Seedance prompt wording, role binding, and compact prompt compression. Keep reference tags unchanged when translating surrounding prose. The tokens in these tables and templates are examples, not attached assets or universal syntax. Before adapting them, follow [Using Reference Examples](../surface-prompt-profiles.md#using-reference-examples) and preserve the actual binding token, whatever its script or format.

| Function | Korean | English meaning |
|---|---|---|
| Role | `@Image1을 첫 프레임으로 사용` | use Image1 as the first frame |
| Role | `@Image2를 마지막 프레임으로 사용` | use Image2 as the last frame |
| Role | `@Image1로 인물 정체성을 고정` | Image1 locks character identity |
| Role | `@Video1은 카메라 움직임만 참고` | Video1 controls camera movement only |
| Role | `@Video1은 동작 리듬만 참고` | Video1 controls action rhythm only |
| Role | `@Audio1은 템포와 분위기만 참고` | Audio1 controls tempo and mood only |
| FirstLastFrame | `첫 프레임은 변경하지 않는다` | keep first frame unchanged |
| FirstLastFrame | `마지막 프레임을 최종 목표로 삼는다` | final frame is the target endpoint |
| FirstLastFrame | `중간 동작은 끊기지 않고 이어진다` | continuous in-between motion |
| FirstLastFrame | `같은 인물, 의상, 공간 구조를 유지` | preserve same character, outfit, and layout |
| Camera | `느린 돌리 인` | slow push-in |
| Camera | `뒤로 빠지며 공간을 드러내는 샷` | pull back to reveal space |
| Camera | `안정적인 측면 트래킹` | stable lateral tracking |
| Camera | `고정된 미디엄 샷` | locked medium shot |
| Camera | `매크로 클로즈업` | macro close-up |
| Camera | `로우 앵글` | low-angle shot |
| Camera | `어깨 너머 샷` | over-the-shoulder shot |
| Camera | `가벼운 핸드헬드 호흡감` | handheld shot with slight breathing sway |
| Shot | `미디엄 클로즈업` | medium close-up |
| Shot | `넓은 설정 샷` | wide establishing shot |
| Shot | `3/4 측면 얼굴` | three-quarter profile |
| Shot | `삼분할 구도` | rule-of-thirds composition |
| Shot | `여백의 미, 고독감` | negative space, isolation |
| Shot | `전경을 흐리게 처리한 프레임` | frame seen past foreground blur |
| Shot | `시선을 끄는 유도선` | leading lines pulling the eye |
| Shot | `전경, 중경, 원경의 깊이` | layered foreground, midground, background depth |
| Camera | `원테이크 롱테이크` | one continuous long take |
| Camera | `드론 부감샷` | drone bird's-eye view |
| Lighting | `나뭇잎 사이로 비치는 빛` | sunlight dappled through leaves |
| Lens | `24mm 광각으로 공간감 강조` | 24mm wide spatial feel |
| Lens | `50mm 자연스러운 인물감` | 50mm natural portrait feel |
| Lens | `매크로 렌즈로 재질 디테일 강조` | macro lens for material detail |
| Lighting | `부드러운 역광` | soft backlight |
| Lighting | `왼쪽의 따뜻한 프랙티컬 조명` | warm practical light from left |
| Lighting | `차가운 달빛 림 라이트` | cool moon rim light |
| Lighting | `얇은 안개를 지나는 볼류메트릭 라이트` | volumetric light through mist |
| Lighting | `젖은 노면에 네온이 반사된다` | wet pavement reflects neon |
| Motion | `발밑의 안개가 천천히 퍼진다` | fog spreads around the feet |
| Motion | `물방울이 합쳐져 아래로 흐른다` | droplets merge and slide down |
| Motion | `천천히 고개를 돌리고 멈춘다` | slow head turn and stop |
| Motion | `천이 동작에 맞춰 자연스럽게 흔들린다` | fabric moves naturally with action |
| VFX | `금빛 입자가 올라가며 사라진다` | gold particles rise and dissipate |
| VFX | `푸른 전기 아크가 가장자리를 따라 흐른다` | blue arcs crawl along the edge |
| VFX | `빛줄기가 재질 표면을 지나간다` | light sweep crosses material surface |
| Audio | `짧고 명확한 한마디 대사` | one short clear spoken line |
| Audio | `대사는 해요체로` | dialogue in polite 해요체 |
| Audio | `대사는 합니다체로, 격식 있게` | dialogue in formal 합니다체 |
| Audio | `대사는 반말로, 편하게` | dialogue in plain 반말 |
| Audio | `두 인물 사이의 말투 관계를 유지` | keep the speech-level relationship between the two characters |
| Audio | `음악 없이 낮은 환경음만` | no music, low ambience only |
| Audio | `대사 중에는 카메라를 고정` | locked camera during dialogue |
| Audio | `발소리가 박자에 맞는다` | footsteps hit the beat |
| Text | `자막, 워터마크, 불필요한 글자 추가 금지` | no subtitles, watermark, or extra text |
| Editing | `샷을 이어서 진행` | continue the shot |
| Editing | `5초 연장` | extend by five seconds |
| Editing | `실패한 구간만 교체` | replace only the failed segment |
| Constraint | `로고, 라벨, 형태, 색상을 엄격히 유지` | preserve logo, label, shape, and color |
| Constraint | `움직임, 빛, 카메라만 변경` | change only motion, light, and camera |
| Constraint | `사람, 장소, 브랜드를 복사하지 않음` | do not copy people, place, or brands |
| Safety | `오리지널 캐릭터로 대체` | replace with an original character |
| Safety | `허가된 참조만 사용` | use only authorized references |
| Safety | `창작 기능은 유지하되 보호된 정체성은 제외` | preserve creative function, not protected identity |

## Compact Template

`@Image1은 참조이며 [피사체/제품/얼굴/로고]를 정확히 유지한다. 변화는 [동작/조명/카메라]만 적용한다. 카메라: [한 가지 움직임]. 사운드: [음향 지시].`

## Multimodal Template

`@Image1은 오리지널 인물을 고정한다. @Video1은 카메라 움직임만 참고하고 인물, 장소, 브랜드는 복사하지 않는다. @Audio1은 템포와 분위기만 참고한다.`

## Timeline Template

The bracket-timeline skeleton is the Chinese community's long-prompt pattern (`vocab/zh` Timeline Template, field-observed on 即梦/Dreamina). Below is the same structure in Korean: the *structure* is what is field-observed, a Korean-specific version is not independently reported, so treat it as a starting scaffold rather than a community guarantee.

```
[스타일] [매체·질감·색조를 한 문장으로]
[타임라인] 0-3s: [화면+카메라+사운드]; 3-6s: [화면+카메라+사운드]; 6-10s: [화면+카메라+사운드]
[사운드] [대사/환경음/효과음/음악 없음]
[참조] @Image1 로 인물 동일성 고정; @Video1 은 카메라 움직임만 참조; @Audio1 은 템포만 참조
```

## Sequence and Continuation Phrases

Use these when the Korean prompt is part of a v6 sequence project, continuation, or localized delivery workflow.

| Function | Korean | English meaning |
|---|---|---|
| Role | `승인된 영상을 프로젝트의 기준으로 삼는다` | accepted footage is the project truth |
| Role | `이전 클립의 실제 끝 상태에서 이어진다` | continue from the actual previous ending |
| Role | `이전 동작을 반복하지 않는다` | do not replay the previous action |
| Role | `이번 클립은 현재 작업만 보여준다` | this clip shows only the current task |
| Role | `뒤의 전개는 아직 보여주지 않는다` | future story beats do not appear yet |
| FirstLastFrame | `이전 클립의 마지막 프레임을 시작점으로 사용` | use previous final frame as starting point |
| FirstLastFrame | `새로운 마지막 자세로 멈춘다` | settle into the new final pose |
| Motion | `이전 열린 움직임 방향을 유지` | preserve previous open motion vector |
| Motion | `정지 상태에서 움직임을 시작` | action starts from a still state |
| Editing | `Clip 02 이어가기 프롬프트` | continuation prompt for Clip 02 |
| Editing | `끝부분 드리프트만 수정하고 앞부분은 유지` | repair only tail drift, not the first half |
| Constraint | `완료된 동작은 반복하지 않는다` | completed actions must not repeat |
| Constraint | `아직 일어나지 않은 내용은 먼저 보여주지 않는다` | unshown future events must not appear early |
| Text | `화면 안 글자는 넣지 않고 자막은 후반 작업에서 추가` | keep image textless; subtitles added in post |
| Text | `한국어 카피와 법적 문구는 편집에서 추가` | Korean copy and legal text added in edit |
| Safety | `창작 기능만 유지하고 오리지널 인물로 대체` | preserve creative function with original identity |

## Dialogue Notes

No validated language-wide line ceiling is established here. Preserve the user's exact dialogue and intended register. Time the spoken performance rather than treating written counts as seconds. A short speaker turn and stable framing are useful starting conditions; review pronunciation, performance, and visible sync separately. See [audio-guide](../audio-guide.md) for task-scoped benchmark evidence. Voice references and post dubbing are options, not mandatory remedies for this language. Reference tags such as `@Image1` stay unchanged.

## Speech Level (말투)

Preserve the user's wording and characterization. For newly drafted speech, choose 합니다체, 해요체, or an appropriate informal form from the relationship, situation, and intended tone. These examples are not an exhaustive account of Korean speech levels, and no register has a fixed syllable multiplier. A deliberate shift can express a change in relationship; do not automatically flatten it.

고마워, 고마워요, and 감사합니다 illustrate different wording and social use. Their lengths do not establish a universal cost ratio. Measure the actual delivery with pauses, and do not choose casual speech merely to save syllables. If the relationship is unclear and materially changes the line, ask one focused question or offer labeled alternatives. Naturalness remains pending a qualified Korean-language review.

## Aesthetic Registers (미학)

Korean aesthetic terms can carry useful creative intent. Preserve the user's chosen term; when the intended shot is unclear, ask what matters or propose a scene-specific visible or audible detail. The examples below are authored possibilities, not definitions of a culture or mandatory ingredients. This is editorial guidance for making direction reviewable, not evidence that these terms destabilize Seedance output. Independent language and production-language review remains pending.

| Term | One possible scene treatment |
|---|---|
| 한 (han — grief that stays) | stillness and weight, not tears: `움직임을 멈춘 인물, 긴 그림자, 식은 밥상, 빗소리만` |
| 정 (jeong — accumulated closeness) | small physical care between people: `말없이 반찬을 옮겨 주는 손, 어깨에 걸쳐 주는 외투` |
| 여백의 미 (beauty of empty space) | already physical — compose it: `대칭 구도, 화면 대부분이 빈 벽, 인물은 구석에 작게` |
| 신명 (exuberant collective spirit) | rhythm made visible: `북 장단에 맞춘 발 구름, 원을 그리며 도는 군무, 손에서 손으로 넘어가는 술잔` |
| 사극 (historical-drama register) | period material, not the label: `한복의 겹쳐진 옷감, 궁궐 처마 아래의 그림자, 촛불 조명` |

## Slop Traps

편집 지침: 의도가 불분명할 때 추상적인 형용사에 보이는 동작이나 들리는 소리를 덧붙인다. 의도를 전달하는 스타일 이름은 남겨도 된다. 이는 제작 의도를 확인하기 위한 방법이며, 모델이 형용사를 이해하지 못한다는 실증이나 영상 안정성·생성 비용 개선의 보장이 아니다. 아래 예시는 공통 처방이 아니다. 느린 돌리 인, 안개, 틸 앤 오렌지를 자동으로 추가하지 않는다. 사용자가 정한 스타일, 표현의 강도, 대사, 참조 태그, 설정을 유지한다. 해석에 따라 장면이 크게 달라질 때만 차이가 분명한 선택지를 소수 제시한다. 선택을 위임받았다면 그 범위에서 결정한다.

| 상투어 | 장면에 맞춰 덧붙일 지시 |
|---|---|
| `영화 같은 / 시네마틱한` | 시계 수리공이 째깍 소리를 듣고 미소 짓는 장면이라면: `눈높이에 카메라를 고정한다. 시계 소리가 난 뒤 그녀가 미소 짓는다. 마지막에는 그 표정을 유지한다`. 이 장면의 한 가지 선택이며, 모든 연기를 조용하고 절제되게 만드는 규칙이 아니다 |
| `감성적인 / 감성` | 어떤 반응을 보여 줄지 정하고 동작이나 소리로 쓴다. 기쁨이라면 웃음소리나 큰 몸짓도 선택할 수 있다. 노을이나 쓸쓸함을 자동으로 더하지 않는다 |
| `분위기 있는` | 필요한 분위기를 확인하고 그 장소의 소리나 빛을 고른다. 작업실이라면 `공구를 내려놓은 뒤에도 시계 소리가 들린다`. 안개나 젖은 노면은 필수가 아니다 |
| `아름다운` | 선택한 스타일에 맞춰 색·질감·구도·빛의 움직임을 구체화한다. 부드러운 빛만으로 제한하지 않는다 |
| `웅장한` | 규모가 목적이면 인물과 공간의 크기 관계를 쓴다. 다른 뜻이라면 확인하고 군중을 자동으로 늘리지 않는다 |
| `고퀄리티 / 고화질 / 8K` | 실제 납품 해상도와 확인 항목을 기록하고 지원되는 설정을 확인한다. 프롬프트의 숫자만으로 출력 해상도가 보장되지는 않는다 |
| `압도적인` | 인상을 만드는 대비·동작·드러나는 순간을 쓴다. 요청된 강한 표현을 약화하지 않는다 |
| `몽환적인`(단독) | 무엇이 평소와 다른지 정하고 그 움직임이나 소리를 쓴다. 입자나 안개를 자동으로 더하지 않는다 |
| `미친 퀄리티` | 이 장면에서 확인할 항목을 쓴다. 예를 들어 시계 눈금의 가독성이나 동작의 연결이다. 이는 요구 사항이며 이미 확인된 결과가 아니다 |
| `멋있는` | 그 인물에게 맞는 자세·동작·보여 주는 방식을 고른다 |
| `다이내믹한` | 움직임의 종류·속도·끝점을 쓴다. 피사체의 움직임과 카메라의 움직임을 구분한다 |
