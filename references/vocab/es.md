# Spanish Vocabulary

Use this reference for Spanish Seedance prompt wording, role binding, and compact prompt compression. Keep reference tags unchanged: `[Image1]`, `[Video1]`, and `[Audio1]` stay literal.

| Function | Spanish | English meaning |
|---|---|---|
| Role | `[Image1] como primer fotograma` | Image1 is the first frame |
| Role | `[Image2] como fotograma final` | Image2 is the last frame |
| Role | `[Image1] fija la identidad del personaje` | Image1 locks character identity |
| Role | `[Video1] solo controla el movimiento de cámara` | Video1 controls camera movement only |
| Role | `[Video1] solo marca el ritmo de la acción` | Video1 controls action rhythm only |
| Role | `[Audio1] solo marca tempo y ambiente` | Audio1 controls tempo and mood only |
| FirstLastFrame | `mantener el primer fotograma sin cambios` | keep first frame unchanged |
| FirstLastFrame | `usar el fotograma final como objetivo visual` | final frame is the target endpoint |
| FirstLastFrame | `movimiento continuo sin salto de montaje` | continuous motion, no jump cut |
| FirstLastFrame | `mantener el mismo personaje, vestuario y espacio` | preserve same character, wardrobe, and layout |
| Camera | `travelling de acercamiento lento` | slow push-in |
| Camera | `retroceso para revelar el espacio` | pull back to reveal space |
| Camera | `seguimiento lateral estable` | stable lateral tracking |
| Camera | `plano medio fijo` | locked medium shot |
| Camera | `primer plano macro` | macro close-up |
| Camera | `plano en contrapicado` | low-angle shot |
| Camera | `plano sobre el hombro` | over-the-shoulder shot |
| Camera | `cámara en mano con leve respiración` | handheld camera with slight breathing sway |
| Shot | `plano medio corto` | medium close-up |
| Shot | `plano general amplio` | wide establishing shot |
| Shot | `perfil de tres cuartos` | three-quarter profile |
| Lens | `24 mm angular con sensación de espacio` | 24mm wide spatial feel |
| Lens | `50 mm con perspectiva natural de retrato` | 50mm natural portrait feel |
| Lens | `lente macro para detalle de material` | macro lens for material detail |
| Lighting | `contraluz suave` | soft backlight |
| Lighting | `luz cálida práctica desde la izquierda` | warm practical light from left |
| Lighting | `halo frío de luna` | cool moon rim light |
| Lighting | `luz volumétrica atravesando niebla fina` | volumetric light through mist |
| Lighting | `asfalto mojado reflejando neón` | wet pavement reflects neon |
| Motion | `la niebla se dispersa alrededor de los pasos` | fog spreads around footsteps |
| Motion | `las gotas se unen y descienden` | droplets merge and slide down |
| Motion | `gira lentamente la cabeza y se detiene` | slow head turn and stop |
| Motion | `la tela se mueve de forma natural con el gesto` | fabric moves naturally with action |
| VFX | `partículas doradas se elevan y se disipan` | gold particles rise and dissipate |
| VFX | `arcos eléctricos azules recorren el borde` | blue arcs crawl along the edge |
| VFX | `un barrido de luz cruza la superficie del material` | light sweep crosses material surface |
| Audio | `una frase corta y clara` | one short clear spoken line |
| Audio | `sin música, solo ambiente bajo` | no music, low ambience only |
| Audio | `cámara fija durante el diálogo` | locked camera during dialogue |
| Audio | `los pasos caen en el pulso` | footsteps hit the beat |
| Text | `sin subtítulos, marcas de agua ni texto adicional` | no subtitles, watermarks, or extra text |
| Editing | `continuar el plano` | continue the shot |
| Editing | `extender cinco segundos` | extend by five seconds |
| Editing | `reemplazar solo el fragmento fallido` | replace only the failed segment |
| Constraint | `mantener logotipo, etiqueta, forma y color sin cambios` | preserve logo, label, shape, and color |
| Constraint | `solo cambian movimiento, luz y cámara` | change only motion, light, and camera |
| Constraint | `no copiar personas, lugar ni marcas` | do not copy people, place, or brands |
| Safety | `sustituir por un personaje original` | replace with an original character |
| Safety | `usar solo referencias autorizadas` | use only authorized references |
| Safety | `mantener la función creativa, no la identidad protegida` | preserve creative function, not protected identity |

## Compact Template

`[Image1] es la referencia; mantener [identidad/producto/rostro/logotipo] sin cambios. Solo cambia [acción/luz/cámara]. Cámara: [movimiento único]. Sonido: [señal].`

## Multimodal Template

`[Image1] fija el personaje original. [Video1] solo controla el movimiento de cámara; no copiar persona, lugar ni marca. [Audio1] solo marca tempo y ambiente.`

## Slop Traps

Consenso de la comunidad: los adjetivos de calidad abstractos desestabilizan la generación porque el modelo no sabe qué elemento enfatizar. Convierte cada palabra-sensación en los elementos físicos que la producen (verbo de cámara + velocidad + punto de vista, fuente de luz + dirección + comportamiento).

| Muletilla | Escribe en su lugar |
|---|---|
| `cinematográfico` | escala de plano, movimiento de cámara, fuente de luz y etalonaje: `plano general amplio, travelling lento, sol bajo, tonos teal y naranja` |
| `épico` | escala física: tamaño de la multitud, distancia del objetivo, altura de la estructura |
| `impresionante / asombroso` | el único contraste o revelación visible que lo justifica |
| `hermoso / precioso` | color, textura, material, comportamiento de la luz |
| `obra maestra / alta calidad / 8K` | eliminar; la calidad no se pide y la resolución es un ajuste |
| `espectacular` | el momento concreto: qué se mueve, qué se revela |
| `dramático` | bloqueo, sombra, silencio o presión de cámara |
| `mágico` | comportamiento de partículas, fuente del brillo, trayectoria |
| `de ensueño` (solo) | qué lo hace onírico: `bruma fina, luz volumétrica, flotación lenta` |
| `dinámico` | el movimiento concreto, su velocidad y su punto final |
| `con mucha atmósfera` | los elementos físicos: `niebla fina, reflejos en el suelo mojado, ambiente bajo` |
| `profesional` | iluminación controlada del producto, fondo limpio, cámara estable |
