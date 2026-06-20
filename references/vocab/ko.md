# Korean Vocabulary

Use this reference for Korean Seedance prompt wording, role binding, and compact prompt compression. Keep reference tags unchanged: `[Image1]`, `[Video1]`, and `[Audio1]` stay literal.

| Function | Korean | English meaning |
|---|---|---|
| Role | `[Image1]을 첫 프레임으로 사용` | use Image1 as the first frame |
| Role | `[Image2]를 마지막 프레임으로 사용` | use Image2 as the last frame |
| Role | `[Image1]로 인물 정체성을 고정` | Image1 locks character identity |
| Role | `[Video1]은 카메라 움직임만 참고` | Video1 controls camera movement only |
| Role | `[Video1]은 동작 리듬만 참고` | Video1 controls action rhythm only |
| Role | `[Audio1]은 템포와 분위기만 참고` | Audio1 controls tempo and mood only |
| FirstLastFrame | `첫 프레임은 변경하지 않는다` | keep first frame unchanged |
| FirstLastFrame | `마지막 프레임을 최종 목표로 삼는다` | final frame is the target endpoint |
| FirstLastFrame | `중간 동작은 끊기지 않고 이어진다` | continuous in-between motion |
| FirstLastFrame | `같은 인물, 의상, 공간 구조를 유지` | preserve same character, outfit, and layout |
| Camera | `느린 돌리 인` | slow push-in |
| Camera | `뒤로 빠지며 공간을 드러내는 샷` | pull back to reveal space |
| Camera | `안정적인 측면 트래킹` | stable lateral tracking |
| Camera | `고정된 중간 샷` | locked medium shot |
| Camera | `매크로 클로즈업` | macro close-up |
| Camera | `낮은 앵글` | low-angle shot |
| Camera | `어깨 너머 샷` | over-the-shoulder shot |
| Camera | `가벼운 핸드헬드 호흡감` | handheld shot with slight breathing sway |
| Shot | `중간 클로즈업` | medium close-up |
| Shot | `넓은 설정 샷` | wide establishing shot |
| Shot | `3/4 측면 얼굴` | three-quarter profile |
| Lens | `24mm 광각으로 공간감 강조` | 24mm wide spatial feel |
| Lens | `50mm 자연스러운 인물감` | 50mm natural portrait feel |
| Lens | `매크로 렌즈로 재질 디테일 강조` | macro lens for material detail |
| Lighting | `부드러운 역광` | soft backlight |
| Lighting | `왼쪽의 따뜻한 실용 조명` | warm practical light from left |
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

`[Image1]은 참조이며 [주체/제품/얼굴/로고]를 정확히 유지한다. 변화는 [동작/조명/카메라]만 적용한다. 카메라: [한 가지 움직임]. 사운드: [음향 지시].`

## Multimodal Template

`[Image1]은 오리지널 인물을 고정한다. [Video1]은 카메라 움직임만 참고하고 인물, 장소, 브랜드는 복사하지 않는다. [Audio1]은 템포와 분위기만 참고한다.`

## Sequence and Continuation Phrases

Use these when the Korean prompt is part of a v6 sequence project, continuation, or localized delivery workflow.

| Function | Korean | English meaning |
|---|---|---|
| Role | `승인된 영상을 프로젝트의 기준으로 삼는다` | accepted footage is the project truth |
| Role | `이전 실제 끝 상태에서 이어진다` | continue from the actual previous ending |
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

## Slop Traps

커뮤니티 공통 결론: 추상적인 품질 단어는 모델이 어떤 요소를 강조해야 할지 판단하지 못하게 만들어 출력을 불안정하게 한다. 느낌 단어는 그 느낌을 만드는 물리 요소(카메라 동사+속도+시점, 광원+방향+행동)로 분해한다.

| 상투어 | 바꿔 쓰기 |
|---|---|
| `영화같은 / 시네마틱한` | 샷 크기·카메라 움직임·광원·색보정으로 쓴다: `넓은 설정 샷, 느린 돌리 인, 낮은 노을빛, 틸앤오렌지` |
| `감성적인 / 감성` | 감성을 만드는 물리 요소로 쓴다: `해질녘 역광, 긴 그림자, 멀리서 들리는 기차 소리` |
| `분위기 있는` | 분위기를 만드는 요소를 지목한다: `얇은 안개, 젖은 노면 반사, 낮은 환경음` |
| `아름다운` | 색·질감·구도·빛의 움직임으로 쓴다 |
| `웅장한` | 물리적 규모로 쓴다: 군중 수, 렌즈 거리, 구조물 높이 |
| `고퀄리티 / 고화질 / 8K` | 삭제한다. 해상도는 설정이지 문장이 아니다 |
| `압도적인` | 압도하는 한 가지 대비나 드러남을 쓴다 |
| `몽환적인`(단독) | 몽환을 만드는 요소로 쓴다: `떠다니는 먼지, 볼류메트릭 라이트, 느린 부유` |
| `미친 퀄리티` | 삭제한다. 품질은 요청하는 것이 아니다 |
| `멋있는` | 구체적인 포즈·움직임·카메라로 쓴다 |
| `다이내믹한` | 움직임의 종류·속도·끝점으로 쓴다 |
