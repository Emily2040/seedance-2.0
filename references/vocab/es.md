# Spanish Vocabulary

Use this reference for Spanish Seedance prompt wording, role binding, and compact prompt compression. Keep reference tags unchanged when translating surrounding prose. The tokens in these tables and templates are examples, not attached assets or universal syntax. Before adapting them, follow [Using Reference Examples](../surface-prompt-profiles.md#using-reference-examples) and preserve the actual binding token, whatever its script or format.

| Function | Spanish | English meaning |
|---|---|---|
| Role | `@Image1 como primer fotograma` | Image1 is the first frame |
| Role | `@Image2 como fotograma final` | Image2 is the last frame |
| Role | `@Image1 fija la identidad del personaje` | Image1 locks character identity |
| Role | `@Video1 solo controla el movimiento de cámara` | Video1 controls camera movement only |
| Role | `@Video1 solo marca el ritmo de la acción` | Video1 controls action rhythm only |
| Role | `@Audio1 solo marca tempo y ambiente` | Audio1 controls tempo and mood only |
| FirstLastFrame | `mantener el primer fotograma sin cambios` | keep first frame unchanged |
| FirstLastFrame | `usar el fotograma final como objetivo visual` | final frame is the target endpoint |
| FirstLastFrame | `movimiento continuo sin salto de montaje` | continuous motion, no jump cut |
| FirstLastFrame | `mantener el mismo personaje, vestuario y espacio` | preserve same character, wardrobe, and layout |
| Camera | `travelling de acercamiento lento` | slow push-in |
| Camera | `travelling de retroceso para revelar el espacio` | pull back to reveal space |
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
| Lighting | `luz de contorno fría de luna` | cool moon rim light |
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
| Audio | `los pasos siguen el pulso` | footsteps hit the beat |
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

`@Image1 es la referencia; mantener [identidad/producto/rostro/logotipo] sin cambios. Solo cambia [acción/luz/cámara]. Cámara: [movimiento único]. Sonido: [señal].`

## Multimodal Template

`@Image1 fija el personaje original. @Video1 solo controla el movimiento de cámara; no copiar persona, lugar ni marca. @Audio1 solo marca tempo y ambiente.`

## Dialogue Notes

La variante regional, la relación entre hablantes y el registro se eligen según el encargo. Conserva literalmente las frases indicadas por el usuario; no las traduzcas, acortes ni vuelvas más formales sin acuerdo. Si la frase está en otro idioma y debe ser exacta, la lengua de las instrucciones no cambia la lengua del diálogo.

Cronometra la interpretación real y escucha el resultado con una persona competente en la variante elegida. Una frase breve y un turno de habla pueden servir como condiciones de prueba; no son límites universales ni garantías de sincronización. El texto de esta guía no justifica clasificar todos los idiomas por fiabilidad.

Ofrece voz generada, una referencia de voz autorizada si la operación la admite, o doblaje posterior según las prioridades del usuario. Una referencia no garantiza reproducción exacta. Consulta [audio-guide](../audio-guide.md) y el [protocolo de calibración](../sync-budget-protocol.md) para separar duración, pronunciación y sincronización.

## Slop Traps

Criterio editorial: sustituye un adjetivo vago cuando no indique qué debe verse u oírse. Nombra la acción, el encuadre, la fuente de luz o el sonido que sirve a esa escena. Esta revisión facilita evaluar el encargo; no demuestra cómo procesa el modelo los adjetivos ni garantiza una mejora del vídeo.

| Muletilla | Escribe en su lugar |
|---|---|
| `cinematográfico` | decisiones ligadas al encargo: `cámara fija a la altura de sus ojos; el tictac precede a la sonrisa; mantener la expresión al final` |
| `épico` | escala física: tamaño de la multitud, distancia a la cámara, altura de la estructura |
| `impresionante / asombroso` | el único contraste o revelación visible que lo justifica |
| `hermoso / precioso` | color, textura, material, comportamiento de la luz |
| `obra maestra / alta calidad / 8K` | eliminar; la calidad no se pide y la resolución es un ajuste |
| `espectacular` | el momento concreto: qué se mueve, qué se revela |
| `dramático` | puesta en escena, sombra, silencio o presión de cámara |
| `mágico` | comportamiento de partículas, fuente del brillo, trayectoria |
| `de ensueño` (solo) | qué lo hace onírico: `bruma fina, luz volumétrica, flotación lenta` |
| `dinámico` | el movimiento concreto, su velocidad y su punto final |
| `con mucha atmósfera` | los elementos físicos: `niebla fina, reflejos en el suelo mojado, ambiente bajo` |
| `profesional` | iluminación controlada del producto, fondo limpio, cámara estable |
