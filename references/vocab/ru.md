# Russian Vocabulary

Use this reference for Russian Seedance prompt wording, role binding, and compact translation. Keep reference tags unchanged: `@Image1`, `@Video1`, and `@Audio1` stay literal.

| Function | Russian | English meaning |
|---|---|---|
| Role | `@Image1 как первый кадр` | Image 1 is the first frame |
| Role | `@Image2 как последний кадр` | Image 2 is the final frame |
| Role | `@Image1 задает персонажа` | Image 1 defines the character |
| Role | `@Image2 задает атмосферу сцены` | Image 2 defines scene mood |
| Role | `@Video1 только движение камеры` | Video 1 provides camera movement only |
| Role | `@Video1 задает ритм действия` | Video 1 provides action rhythm |
| Role | `@Audio1 задает темп и настроение` | Audio 1 provides tempo and mood |
| FirstLastFrame | `сохранить первый кадр без изменений` | keep first frame unchanged |
| FirstLastFrame | `естественный переход к последнему кадру` | natural transition to final frame |
| FirstLastFrame | `непрерывное движение без монтажного скачка` | continuous motion, no jump cut |
| FirstLastFrame | `последний кадр является целевым финалом` | final frame is the target endpoint |
| Camera | `фиксированный средний план` | locked medium shot |
| Camera | `медленный наезд камеры` | slow push-in |
| Camera | `отъезд с раскрытием пространства` | pull back to reveal the space |
| Camera | `плавное боковое сопровождение` | stable lateral tracking |
| Camera | `макросъемка крупным планом` | macro close-up |
| Camera | `кадр через плечо` | over-the-shoulder shot |
| Camera | `нижний ракурс` | low-angle shot |
| Camera | `верхний ракурс` | high-angle shot |
| Camera | `круговой облет объекта` | orbit around the subject |
| Camera | `ручная камера с легким дыханием` | handheld camera with slight breathing sway |
| Shot | `среднекрупный план` | medium close-up |
| Shot | `широкий общий план` | wide establishing shot |
| Shot | `профиль в три четверти` | three-quarter profile |
| Lens | `сжатая перспектива телеобъектива` | telephoto compression |
| Lens | `широкоугольное ощущение пространства` | wide-angle spatial feel |
| Lens | `фокус переходит от размытия к резкости` | focus resolves from blur to sharpness |
| Lighting | `мягкий контровой свет` | soft backlight |
| Lighting | `теплый практический источник` | warm practical light |
| Lighting | `теплый практический свет слева` | warm practical light from left |
| Lighting | `холодная лунная контурная подсветка` | cool moon rim light |
| Lighting | `объемный свет через легкий туман` | volumetric light through mist |
| Lighting | `мокрый асфальт отражает неон` | wet asphalt reflects neon |
| Motion | `туман расходится вокруг шагов` | fog spreads around the feet |
| Motion | `капли соединяются и стекают вниз` | droplets merge and slide down |
| Motion | `медленно поворачивает голову и замирает` | slow head turn and stop |
| Motion | `ткань естественно движется от жеста` | fabric moves naturally with action |
| VFX | `золотые частицы поднимаются и рассеиваются` | gold particles rise and dissipate |
| VFX | `синие электрические дуги ползут по краю` | blue arcs crawl along the edge |
| VFX | `световой блик проходит по поверхности материала` | light sweep travels across material |
| Audio | `одна короткая четкая реплика` | one short clear spoken line |
| Audio | `без музыки, только тихий фон` | no music, ambience only |
| Audio | `во время реплики камера неподвижна` | locked camera during dialogue |
| Audio | `шаги попадают в ритм` | footsteps hit the beat |
| Text | `без лишних субтитров, текста и водяных знаков` | no extra subtitles, text, or watermarks |
| Editing | `продолжить кадр` | continue the shot |
| Editing | `продлить на 5 секунд` | extend by five seconds |
| Editing | `заменить только неудачный фрагмент` | replace only the failed segment |
| Constraint | `сохранить логотип, этикетку, форму и цвет без изменений` | preserve logo, label, shape, and color |
| Constraint | `меняются только движение, свет и камера` | change only movement, light, and camera |
| Constraint | `не копировать людей, место или бренды` | do not copy people, place, or brands |
| Safety | `заменить на оригинального персонажа` | change to an original character |
| Safety | `использовать только авторизованный референс` | use only authorized reference |
| Safety | `сохранить творческую функцию без защищенной личности` | preserve creative function, not protected identity |

## Compact Template

`@Image1 — референс; сохранить [персонажа/продукт/логотип] без изменений. Меняются только [движение/свет/камера]. Камера: [одно движение]. Звук: [аудиосигнал].`

## Russian Dialogue Notes

Russian is not included in the model card's Table 20; that absence establishes neither poor performance nor a word limit. Preserve the user's Cyrillic dialogue and intended register. Do not transliterate or shorten it without agreement. Time the actual spoken line and review the returned speech with a Russian speaker; mark naturalness unreviewed if that review is unavailable.

Stable framing and one speaker turn are useful test conditions. Offer native generation, a supported rights-cleared voice-reference workflow, or post dubbing according to the brief. Do not promise reference playback or declare an entire Russian production impossible. See [audio-guide](../audio-guide.md) and [calibration protocol](../sync-budget-protocol.md).

## Slop Traps

Редакторский приём: заменяйте расплывчатое прилагательное, если из него непонятно, что должно быть видно или слышно. Назовите действие, кадрирование, источник света или звук, нужные именно этой сцене. Это помогает проверить замысел, но не доказывает, как модель обрабатывает прилагательные, и не гарантирует улучшения видео.

| Штамп | Пишите вместо него |
|---|---|
| `кинематографичный` | решения для конкретной сцены: `камера неподвижна на уровне её глаз; тиканье предшествует улыбке; в финале выражение лица сохраняется` |
| `эпичный` | физический масштаб: размер толпы, расстояние до объекта, высота сооружения |
| `потрясающий / захватывающий` | тот единственный контраст или момент раскрытия, который это оправдывает |
| `красивый` | цвет, фактура, материал, поведение света |
| `шедевр / высокое качество / 8K` | удалить; качество не запрашивается, разрешение — это настройка |
| `атмосферный` | физические элементы атмосферы: `тонкий туман, отражения на мокром асфальте, тихий фон` |
| `драматичный` | мизансцена, тень, тишина или давление камеры |
| `волшебный` | поведение частиц, источник свечения, траектория |
| `невероятно детализированный` | две детали, которые действительно важны, названные прямо |
| `динамичный` | конкретное движение, его скорость и конечная точка |
| `профессиональный` | контролируемый свет на продукте, чистый фон, стабильная камера |
