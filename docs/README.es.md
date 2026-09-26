<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/hero-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="../assets/hero-light.svg">
  <img alt="Cabecera de Seedance 2.0 Skill OS: dirige al modelo, no microgestiones el cuadro." src="../assets/hero-dark.svg" width="100%">
</picture>

# Seedance 2.0 Skill OS · Español

Convierte una idea en un prompt dirigido, listo para enviar. Esta es la página en español de la versión v6.8.0. No es una traducción de la página en inglés: el orden, los ejemplos y las preguntas están pensados para creadores y agencias de habla hispana. El video lo genera y lo cobra el servicio que tú elijas; esta skill solo se ocupa de escribir bien el prompt.

**Idiomas:** [English](../README.md) · [中文](README.zh.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · Español (esta página) · [Русский](README.ru.md)

Inicio rápido de cinco minutos: [inicio rápido en español](QUICKSTART.es.md)

## Empieza aquí

Después de instalar, dile al agente qué pasa y qué debe quedarse fijo:

> Usa seedance-20. En una sobremesa, una mujer mayor parte una naranja con las manos y le da la mitad al niño de al lado. Cámara fija, sin música. Dame solo el prompt.

Un borrador posible (sin renderizar, solo como ejemplo):

```text
Sobremesa, plano medio fijo desde la cabecera de la mesa.
Una mujer mayor parte una naranja con las manos
y le da la mitad al niño de al lado.
El niño la huele antes de morderla.
Luz de tarde por la ventana izquierda; migas y una taza vacía en primer plano.
Sonido: cubiertos lejanos, una silla que cruje. Sin música ni diálogo.
Los dos últimos segundos se quedan en la cáscara sobre el mantel.
```

**Por qué estas decisiones:** una acción visible, un final claro, una cámara fija y una decisión de sonido explícita. La ternura no se escribe con adjetivos; la lleva la mitad de la naranja que cambia de manos. Esto es intención de dirección, no un resultado comprobado. La duración y la relación de aspecto van en los controles del servicio, no dentro del prompt.

## Instalación

Descarga una copia y ejecuta el instalador desde esa carpeta. Basta con instalar la skill raíz una vez; las sub-skills vienen incluidas.

```bash
git clone https://github.com/Emily2040/seedance-2.0.git
cd seedance-2.0
python scripts/install_codex_skill.py --client codex --scope user
```

Para Claude Code, cambia a `--client claude-code`. Si no tienes git, usa el botón **Code → Download ZIP** de la página del repositorio, descomprime y ejecuta el mismo comando dentro de la carpeta. Reinicia tu cliente y elige `seedance-20`.

El instalador solo copia archivos: no se conecta a la red, no sube nada y no lee claves. Escribir un prompt tampoco autoriza ninguna generación de pago. Los detalles de ubicación y reemplazo están en el [inicio rápido](QUICKSTART.es.md#1-instala-una-sola-skill) y en la [política de seguridad](../SECURITY.md).

## Elige tu camino

| Lo que tienes | Abre primero | Lo que recibes |
|---|---|---|
| Una idea vaga | [`seedance-interview-short`](../skills/seedance-interview-short/SKILL.md) | Un brief corto y un primer borrador, o una sola pregunta que de verdad bloquea |
| Una escena ya clara | [`seedance-prompt`](../skills/seedance-prompt/SKILL.md) | Un prompt listo para enviar |
| Necesitas algo muy corto | [`seedance-prompt-short`](../skills/seedance-prompt-short/SKILL.md) | Una versión comprimida de 30 a 100 palabras |
| Una historia en varios clips | [`seedance-sequence`](../skills/seedance-sequence/SKILL.md) | La columna vertebral de la historia, la biblia de continuidad, el mapa de clips y el contrato y prompt del clip 01 |
| Continuar un clip aceptado | [`seedance-continuation`](../skills/seedance-continuation/SKILL.md) | Un prompt que arranca del final real |
| Referencias de imagen, video o audio | [flujo de referencias](../references/reference-workflow.md) | Un papel por recurso y lo que no debe transferirse |
| Primer y último fotograma | [guía de primer y último fotograma](../references/first-last-frame-guide.md) | Una transición continua con los extremos fijados |
| Un resultado que falló | [`seedance-troubleshoot`](../skills/seedance-troubleshoot/SKILL.md) | Un diagnóstico de causa y una corrección de una sola variable |
| Personas reales, personajes, marcas o canciones | [`seedance-copyright`](../skills/seedance-copyright/SKILL.md) | Una reescritura segura que conserva la función creativa |
| Vocabulario en español | [vocabulario de dirección en español](../references/vocab/es.md) | Encuadres, movimientos de cámara, luz y sonido en español |

## Primero la tabla de planos, después el prompt

Cuando un prompt tiene más de un plano o más de una persona, la skill escribe primero la [tabla de planos](../references/shot-table.md) y genera el prompt a partir de ella. Primero el lugar en unas frases (dónde está la puerta, hacia dónde mira la cabecera de la mesa, de dónde viene la luz); después una fila por plano: de qué lado está la cámara, quién aparece, dónde está y hacia dónde mira, qué mira, la única acción del plano, qué siguen haciendo los demás, la luz y el último fotograma.

La tabla se entrega debajo del prompt para que compruebes la geografía sobre el papel antes de pagar una generación. Una celda vacía o "por defecto" significa que el prompt todavía no se puede enviar.

La escritura sigue [dirigir para el modelo](../references/direct-for-the-model.md): la emoción es una palabra llana más un gesto del cuerpo ("se queda quieto, alarmado, traga saliva"), sin modismos ni listas de músculos; una acción por plano y los demás siguen con lo suyo, nunca "nadie se mueve".

Al final de cada plano se repiten luz, personajes, posición, orientación y lado de la cámara; los objetos se escriben como movimientos de la mano. Antes de entregar, el prompt pasa el [filtro previo de moderación](../references/moderation-prescreen.md).

## Reglas para prompts en español

1. **Las etiquetas de referencia no se tocan.** `@Image1`, `@Video1` y `@Audio1` se escriben tal cual, sin traducir ni cambiar espacios.
2. **Primero el papel de cada referencia, después la acción, la cámara, la luz y el sonido.** Cada recurso hace una sola cosa: `@Image1` fija la identidad, `@Video1` aporta solo el movimiento de cámara, `@Audio1` solo el ritmo.
3. **Nada de "cinematográfico", "épico" o "emotivo".** Se descomponen en encuadre, movimiento, fuente de luz, material, color y aire.
4. **Un clip, una acción, un final.** Dos acciones son dos clips.
5. **El diálogo exacto se conserva palabra por palabra.** Si el personaje tutea, vosea o trata de usted, eso lo decide la escena, no la guía. Mide el tiempo hablado antes de encajarlo en el clip.
6. **Subtítulos, rótulos y textos legales van en posproducción.** El texto generado por el modelo no es fiable.

## Continuación

No pidas toda la historia en una sola generación. Genera el clip 01, mira cómo terminó de verdad y escribe el clip 02 desde ese final. El modelo no siempre se detiene donde el plan esperaba.

```text
Objetivo de la historia: [el estado final que debe alcanzarse]
Lo que ya pasó: [hechos del clip aceptado]
Solo en este clip: [una acción visible]
Todavía no mostrar: [lo que se reserva para después]
Referencias: @Image1 fija al personaje; @Video1 solo cámara; @Audio1 solo ritmo
Prompt: [una acción + una cámara + luz concreta + sonido]
```

## Seguridad

Si la idea usa la cara o la voz de una persona real, un personaje protegido, una marca o una canción, cambiar de idioma no lo arregla.
Conserva la función creativa y sustitúyela por un personaje original, un mundo original, una referencia con licencia o una solución de posproducción.
De eso se encarga [`seedance-copyright`](../skills/seedance-copyright/SKILL.md).
Cuando un contenido legítimo queda bloqueado por error, [`seedance-filter`](../skills/seedance-filter/SKILL.md) lo repara aclarando el contexto de producción, nunca ocultando la intención.

## Preguntas frecuentes

**¿Sirve para Seedance 2.5?** Esta skill es para Seedance 2.0. La página oficial de ByteDance confirma que 2.5 es una línea de modelo distinta y Dreamina la ofrece; pero cada duración, límite de referencias, resolución e identificador de modelo que hay aquí es de 2.0 y no se puede trasladar a 2.5. El método de dirección, los papeles de las referencias y las reglas de continuidad sí se aplican. Consulta el [estado de la plataforma](../references/api-status.md).

**¿Cuántos planos caben en un clip?** No hemos encontrado un límite oficial. Cuantos más planos, menos segundos tiene cada uno. Empieza por una acción bien resuelta y consulta la [gramática multiplano](../references/multishot-grammar.md).

**Instalé la skill y no aparece.** Reinicia el cliente. Después ejecuta `python scripts/install_doctor.py --client codex --scope user --json` con la misma ubicación de instalación para comprobar que los archivos coinciden. El doctor confirma que los archivos existen; no confirma qué copia carga tu cliente.

## Estado de revisión

Esta página es un borrador redactado con ayuda de IA y aún no tiene revisión independiente de especialistas en español ni en lenguaje audiovisual. Los ejemplos no se han renderizado. Variante declarada: español neutro de América, con tuteo, "video" sin tilde y comillas rectas; ninguna variante regional se presenta como validada. [Cobertura y revisión](LANGUAGE_COVERAGE.md).
