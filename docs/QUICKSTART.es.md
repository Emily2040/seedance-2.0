# Seedance 2.0 Skill OS — Guía rápida

> Versión 6.7.0 · De la instalación a tu primer prompt "con dirección" en unos 5 minutos.
> Documentación completa: [README](../README.md).

## En una frase

Seedance 2.0 Skill OS es un agent skill que dirige Seedance 2.0 como lo haría un cineasta, en lugar de amontonar adjetivos. Una sola regla: **dirige el modelo, no te pelees con cada fotograma.** Cuéntale qué está *haciendo* la escena y la skill convierte esa intención en un prompt listo para producción.

## 1. Instalación (unos 5 minutos)

Instala el repositorio como **una** skill raíz llamada `seedance-20`; sus sub-skills y references se cargan solas por ruta relativa.

**Primero, consigue los archivos.** Cada comando de abajo se ejecuta dentro de una copia local:

```bash
git clone https://github.com/Emily2040/seedance-2.0.git
cd seedance-2.0
```

¿Sin `git`? Usa **Code → Download ZIP** en la página del repositorio, descomprime y entra en la carpeta.

**Después, instálalo.** El instalador no es solo para Codex: `--dest` elige el directorio de skills que lee tu cliente:

```bash
# Codex (por defecto ~/.codex/skills)
python scripts/install_codex_skill.py

# Claude Code (instalación personal, en todos los proyectos)
python scripts/install_codex_skill.py --dest ~/.claude/skills

# Instalar en otro proyecto: ejecuta esto desde ese proyecto
python /ruta/a/seedance-2.0/scripts/install_codex_skill.py --dest .claude/skills
```

Imprime dónde quedó instalada. Reinicia tu cliente y llama a `seedance-20`. Añade `--force` solo para reemplazar una instalación completa existente; una instalación administrada incompleta se repara automáticamente. La nueva copia se prepara y valida antes del cambio. Durante la promoción, la copia completa anterior se conserva como respaldo vinculado a la transacción: si la promoción falla, se restaura; solo después de una promoción correcta se pone en cuarentena y se elimina de forma segura. Un destino dentro de este repositorio se rechaza: copiar el árbol de fuentes dentro de sí mismo recurre hasta que la longitud de la ruta falla.

**Instalar desde GitHub (si tu cliente lo permite por URL)**

```text
https://github.com/Emily2040/seedance-2.0
```

**Copia manual (otros clientes)**

Copia la carpeta en el directorio de skills de tu cliente, sin cambiarle el nombre `seedance-20`. Los destinos habituales están en la [tabla de instalación del README](../README.md#install) (no es una garantía: compruébalos en tu propio cliente). Por ejemplo: Claude Code `.claude/skills/`, Cursor `.cursor/skills/`, GitHub Copilot `.github/skills/`, Windsurf `.windsurf/skills/`.

> Lo primero, la seguridad: instálalo solo en clientes de agente en los que confíes. Antes de usar esta skill en un agente ajeno o desconocido, léete [SECURITY.md](../SECURITY.md).

## 2. Elige la skill según tu caso

| Lo que tienes… | Carga primero |
|---|---|
| una idea todavía difusa | `seedance-interview` |
| una escena clara | `seedance-prompt` |
| una historia de varios clips | `seedance-sequence` |
| un clip ya aprobado que continuar | `seedance-continuation` |
| un resultado flojo o bloqueado | `seedance-troubleshoot` |
| un personaje, marca, celebridad o persona real | `seedance-copyright` |

## 3. Dirige antes de escribir — cuatro preguntas

1. **¿Qué está haciendo la escena?** ¿Un giro, una revelación, una emoción, una demostración?
2. **¿Cómo lo cuenta la cámara?** El plano general para la soledad, el primer plano para el rostro, un acercamiento lento para la revelación.
3. **¿Para qué trabaja la luz?** La hora del día, dura o suave, cálida o fría — todo al servicio de la intención.
4. **¿Qué hace el sonido?** Casi silencio, un solo detalle de ambiente, o una línea de diálogo.

## 4. Un contraste

**Recargado (flojo)**

```
plano épico y cinematográfico de una mujer leyendo una carta, emotivo, iluminación preciosa, 4K
```

**Con dirección (fuerte)**

```
Una mujer con una chaqueta de lana está sentada a la mesa de la cocina y lee una sola hoja de papel. Sus ojos recorren la misma línea dos veces; después sus manos bajan la hoja a la mesa y se quedan completamente quietas. La cámara mantiene un plano medio corto a la altura de los ojos y se acerca despacio, deteniéndose cuando sus manos paran. Luz de ventana de día nublado desde la izquierda, sin relleno. Sonido: tono de sala, el roce de una silla, luego casi silencio.
```

Lee el **orden**, no solo las palabras. El sujeto y lo que está haciendo van **primero**, y la cámara, la luz y el sonido vienen después: el comienzo del prompt es donde el modelo fija de quién es el plano. Empezar por `Plano medio corto, a la altura de los ojos` gasta esa posición en datos de encuadre y deja que el modelo deduzca el sujeto más tarde. El mismo oficio, con peor jerarquía.

La longitud funciona igual: esto son 89 palabras. Para un solo clip, apunta a unas **40–110 palabras**. Mucho más corto y el modelo rellena los huecos por ti; mucho más largo y las frases finales dejan de llegar a la imagen.

## 5. Dos reglas que te ahorran tomas

- **Deja las etiquetas de referencia tal cual:** `@Image1`, `@Video1`, `@Audio1`, `@图片1`, `@视频1`. Ni las traduzcas ni las reformatees.
- **No pidas la historia entera en una sola generación.** Genera el Clip 01, mira cómo terminó *de verdad* y escribe el Clip 02 a partir de ese final real (`seedance-continuation`).

## 6. Seguridad

- **Seguridad del contenido:** si tu idea usa un personaje protegido, una celebridad, una marca, un logo, una canción o el rostro o la voz de una persona real, no lo escondas en otro idioma: reescríbelo con `seedance-copyright` en un equivalente original, con licencia o de posproducción.
- **Seguridad del agente:** el **contenido instalado** no hace llamadas de red ni envía telemetría; los scripts instalados se ejecutan localmente sin contactar servicios externos. La copia de trabajo del repositorio también contiene `scripts/eval_run.py`, una herramienta solo para desarrollo que puede contactar a un proveedor de modelos y que el instalador excluye. No pegues nunca claves de API, cookies de cuenta ni material privado en un agente en el que no confíes. Consulta [SECURITY.md](../SECURITY.md).

## 7. Para profundizar

- `references/directing-engine.md` — lee la escena y elige una única intención (33 ejemplos por género).
- `references/capability-map.md` — diseña aprovechando las fortalezas del modelo y esquivando sus límites conocidos.
- `references/api-workflow.md` — API, proveedores, precios e IDs de modelo (con fecha de la fuente).
- `references/examples-by-mode.md` — ejemplos de T2V, I2V, V2V, R2V, FLF2V, edición y extensión.

---

Otros idiomas: [English](QUICKSTART.md) · [中文](QUICKSTART.zh.md) · [日本語](QUICKSTART.ja.md) · [한국어](QUICKSTART.ko.md) · [Русский](QUICKSTART.ru.md)
