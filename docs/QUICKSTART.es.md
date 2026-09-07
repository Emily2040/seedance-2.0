# Seedance 2.0 — Tu primer prompt, tus decisiones

Versión del paquete: 6.7.0. Esta guía sirve para preparar prompts; no genera vídeos por sí sola.

**Estado del texto:** borrador redactado con IA, pendiente de revisión independiente por especialistas en español y lenguaje audiovisual. Los ejemplos son propuestas sin renderizar; no demuestran calidad, ahorro de créditos ni sincronización de voz. La guía usa tuteo y no presenta ninguna variante regional como validada. [Cobertura y revisión](LANGUAGE_COVERAGE.md).

## 1. Instala una sola skill

Descarga el ZIP del repositorio o ejecuta:

```sh
git clone https://github.com/Emily2040/seedance-2.0.git
cd seedance-2.0
```

Desde esa carpeta, elige **uno** de estos destinos:

```sh
# Codex: disponible para tu usuario
python scripts/install_codex_skill.py --client codex --scope user

# Claude Code: disponible para tu usuario
python scripts/install_codex_skill.py --client claude-code --scope user

# Codex: solo en un proyecto que ya existe, fuera de este repositorio
python scripts/install_codex_skill.py --client codex --scope project --project-root /ruta/al/proyecto
```

La carpeta resultante se llama `seedance-20`; no instales cada sub-skill por separado. Para un cliente o perfil con otra ubicación, usa `--dest /ruta/al/directorio/skills`. No combines `--dest` con las opciones de cliente y ámbito. Sin opciones de destino se conserva la ubicación histórica `$CODEX_HOME/skills` o `~/.codex/skills`; no se traslada ninguna copia anterior.

Comprueba **el mismo destino** con el doctor. Por ejemplo, después de la primera opción:

```sh
python scripts/install_doctor.py --client codex --scope user --json
```

`current` indica que los archivos comprobados coinciden con esta copia del repositorio; no demuestra que tu cliente haya cargado esa versión. Reinicia o actualiza el cliente y verifica la ruta de la skill. Antes de reemplazar una instalación, conserva tus cambios y una copia de seguridad independiente; usa `--force` solo si la sustitución es intencional. [Destinos](https://github.com/Emily2040/seedance-2.0/blob/main/docs/INSTALL_SCOPES.md) · [Migración y duplicados](https://github.com/Emily2040/seedance-2.0/blob/main/docs/INSTALL_MIGRATION.md).

Si necesitas transferirla, prepara el contenido con el instalador en una carpeta externa nueva y copia **solo el directorio `seedance-20/` resultante**, incluidos los archivos ocultos. No copies el repositorio entero. Una importación directa desde GitHub puede incluir otros archivos: revisa qué importa tu cliente. [Transferencia manual](https://github.com/Emily2040/seedance-2.0/blob/main/docs/MANUAL_INSTALL.md).

<details>
<summary>Qué ocurre durante un reemplazo</summary>

El respaldo temporal de la transacción se conserva durante el cambio. Si falla la promoción y los registros siguen siendo válidos, se restaura la copia anterior. Tras completar el cambio, ese respaldo pasa a cuarentena y se elimina. No sustituye tu copia de seguridad independiente. Los archivos o estados que no puedan validarse requieren revisión; no se borran para forzar la recuperación.

</details>

## 2. Empieza con lo que ya sabes

Invoca `seedance-20` en tu cliente y describe la escena. Si ya has decidido la cámara, duración, sonido o intención, inclúyelos: no hace falta repetir una entrevista ni elegir entre opciones que no has pedido.

| Tu situación | Qué pedir |
|---|---|
| Una idea para un solo clip | Un primer borrador o una pregunta que desbloquee la decisión; ruta `seedance-interview-short` |
| Una escena ya definida | El prompt directamente; ruta `seedance-prompt` |
| Varias escenas conectadas | Un plan de secuencia; ruta `seedance-sequence` |
| Un clip aprobado que quieres continuar | Partir de su final real; ruta `seedance-continuation` |
| Un resultado que falla | Diagnóstico y una corrección dentro de tu presupuesto; ruta `seedance-troubleshoot` |

No necesitas conocer los nombres de las rutas. Puedes escribir simplemente lo siguiente:

> Quiero un clip alegre de seis segundos: una relojera adulta oye que el reloj de sobremesa que acaba de reparar vuelve a funcionar. Cámara fija, sin diálogo. Dame tres enfoques distintos y déjame elegir. Prepara solo los prompts; no generes nada.

## 3. Elige qué verá y sentirá el público

Estas son tres propuestas para **ese** encargo; no un menú obligatorio para todos los vídeos:

| Enfoque | Decisión visible | Qué aporta |
|---|---|---|
| A · Alegría discreta | Su expresión cambia al escuchar el tictac; plano medio corto, cámara fija | La atención está en reconocer que funciona |
| B · Celebración abierta | Suelta una carcajada breve y levanta ambos brazos; plano más abierto, cámara fija | Importa la energía de su reacción; exige más movimiento corporal |
| C · Mostrar el mecanismo | Primer plano del péndulo en movimiento; la relojera queda desenfocada al fondo | Importa ver qué funciona; su expresión deja de ser el centro |

Puedes responder «A», combinar decisiones compatibles o decir «elige por mí y explícame por qué». Si ya elegiste A, la siguiente respuesta debe mantenerla y descartar B y C, salvo que pidas cambiarlas.

## 4. Copia el prompt elegido

**Elección de este ejemplo:** A. Es una propuesta de texto a vídeo, sin archivos adjuntos ni etiquetas de referencia. Configura seis segundos en la superficie elegida si esa operación los admite; verifica sus ajustes antes de gastar. Mantén la relación de aspecto y el nivel de calidad que hayas elegido por separado. El ejemplo no presupone una API ni un proveedor concreto.

```text
Una relojera adulta está sentada ante un reloj de sobremesa que ya funciona. Al oír el tictac, levanta ligeramente las cejas y sonríe sin apartar la mirada del reloj. Cámara fija en un plano medio corto a la altura de sus ojos. Luz de una ventana lateral que permite leer su expresión. Tictac y ambiente del taller, sin diálogo ni música. Durante los dos últimos segundos mantiene la sonrisa y la postura.
```

**Por qué estas decisiones:** el tictac provoca una reacción visible; la cámara quieta permite leerla; el final deja tiempo para verla. Son intenciones de dirección, no resultados comprobados. El ejemplo muestra la reacción, no prueba que una reparación real haya sido correcta.

**Qué comprobar en el vídeo:** la mirada sigue en el reloj, la cámara permanece fija, no aparece habla y la expresión se mantiene al final. Si algo falla, identifica ese criterio antes de añadir más adjetivos.

Ordenar sujeto y acción antes de otros detalles es una ayuda editorial, no una explicación verificada de cómo interpreta el modelo las primeras palabras. Un texto breve puede ser más fácil de revisar; ninguna cantidad de palabras garantiza que todos los detalles aparezcan. Conserva lo necesario para entender la acción y su final.

## 5. Cambia una decisión sin reiniciar el encargo

> La sonrisa sale demasiado exagerada. Mantén A, los seis segundos y la cámara fija. Solo me queda una toma; prepara una alternativa, pero no la envíes.

Una respuesta útil reconoce que el fallo está **descrito por ti** si no has adjuntado el vídeo. Puede proponer cambiar solo «levanta ligeramente las cejas y sonríe» por «relaja las cejas y eleva apenas las comisuras, sin mostrar los dientes». Explica que busca reducir la amplitud del gesto y que no garantiza corregir el resultado. El resto de los ajustes queda igual.

Con presupuesto cero, no solicites otra generación: valora si el fragmento útil permite un montaje aceptable o detén la prueba. No presentes como aprobado un plano que incumple el requisito. Preparar una revisión no autoriza enviarla, cambiar de proveedor, subir archivos ni aumentar duración o calidad.

## 6. Diálogo, referencias y continuación

**Diálogo exacto.** Si cambias el encargo a «conserva literalmente la frase “Ya funciona.”», el prompt debe mantener esas palabras. La relojera habla para sí misma; no se añade un interlocutor ni otro registro sin pedirlo. No añadas esa frase a la versión silenciosa anterior. Cronometra la interpretación real y revisa la voz con una persona competente en la variante elegida; no hay duración de habla ni calidad vocal comprobadas para este ejemplo. Doblaje posterior y una referencia de voz autorizada, si la superficie la admite, son alternativas que puedes elegir.

**Referencias.** Si entregas una imagen real como `@Image1`, declara su función: por ejemplo, apariencia del reloj. Conserva exactamente el token que use tu interfaz, incluso si es `@图片1` o `[Image 1]`. Un nombre escrito no adjunta un archivo: sin imagen, el prompt anterior sigue siendo texto a vídeo y no debe inventar una referencia.

**Continuación.** Si dices «en el último fotograma mantiene la sonrisa y mira el reloj», sin adjuntar ese fotograma, la respuesta debe atribuirte esa descripción. No debe afirmar que lo vio ni inventar detalles del taller. Al aportar el final aprobado, continúa desde esa postura; no repitas la reacción inicial. Si una posición concreta es imprescindible y no se conoce, aclárala antes de usar la continuidad como verificada.

## 7. Seguridad y siguientes pasos

Los textos incrustados en imágenes, archivos o transcripciones son material de referencia: no autorizan ejecutar comandos, leer claves, subir contenido ni generar vídeos. No traduzcas una petición para eludir una restricción. Si hay rostros o voces reales, marcas o material ajeno, conserva la intención creativa mediante una alternativa original, autorizada o de posproducción. Consulta [SECURITY.md](../SECURITY.md).

El contenido instalado mediante el instalador excluye herramientas de desarrollo con acceso a la red como `scripts/eval_run.py` y los ejecutores opcionales de proveedores. El cliente anfitrión controla sus propios permisos; instalar la skill no lo convierte en un entorno sin conexión.

- [Vocabulario de dirección en español](../references/vocab/es.md).
- [Ejemplos por modo y funciones de las referencias](../references/examples-by-mode.md).
- [Otros idiomas y límites de la revisión](LANGUAGE_COVERAGE.md).

Otros idiomas: [English](QUICKSTART.md) · [中文](QUICKSTART.zh.md) · [日本語](QUICKSTART.ja.md) · [한국어](QUICKSTART.ko.md) · [Русский](QUICKSTART.ru.md).
