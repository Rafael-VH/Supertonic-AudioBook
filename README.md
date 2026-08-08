# Supertonic Reader

Conversor de fanfiction a audios con voz sintética, totalmente local. Lee capítulos en Markdown, los limpia y sintetiza en español con el motor [Supertonic 3](https://huggingface.co/spaces/Supertone/supertonic-3) (TTS on-device basado en ONNX Runtime): sin nube, sin API, sin GPU.

```bash
pip install supertonic numpy soundfile
python new/lector_fanfiction_mejorado.py
```

Colocá tus capítulos `.md` en `fanfic/` y los audios aparecerán en `audio/`.

## Quick path

1. **Instalá** las dependencias: `pip install supertonic numpy soundfile` (Python 3.10+).
2. **Poné tus capítulos** en `fanfic/` (Markdown, un archivo por capítulo).
3. **Ejecutá** la CLI desde la raíz: `python new/lector_fanfiction_mejorado.py`.
4. **Escuchá** los resultados en `audio/` (por defecto `capituloN.wav`).

> La primera ejecución descarga el modelo (~1 vez, requiere red). Si copiás una carpeta `modelo/` con los assets junto a los scripts, funciona 100% offline.

## Características

- **Exportación multi-formato nativa**: `wav`, `flac`, `ogg` y `mp3` sin ffmpeg (varios a la vez separados por coma).
- **Natural sorting** de capítulos: `capitulo10.md` va después de `capitulo2.md`.
- **Limpieza automática de Markdown**: títulos, listas, links, imágenes, citas, bloques de código.
- **Segmentación optimizada para TTS** con soporte de abreviaturas del español (`Dr.`, `Sr.`, `etc.`).
- **Protección de memoria para libros largos**: volcado incremental a disco desde ~500 MB acumulados.
- **Tolerante a fallos**: un fragmento que falla no aborta el capítulo.
- **Dos interfaces**: CLI con argparse y GUI (Tkinter) con selección de capítulos, formatos, voz y parámetros.
- **Empaquetable en `.exe`**: tanto la app como un instalador portable de un solo archivo.

## Estructura del proyecto

| Carpeta | Qué contiene | Documentación |
|---------|--------------|---------------|
| `new/` | **Versión actual**: CLI (`lector_fanfiction_mejorado.py`), GUI (`lector_gui.py`) y spec PyInstaller. | [new/README.md](new/README.md) |
| `portable/` | **Instalador portable**: un `.exe` que extrae la app completa junto a sí mismo y la lanza. | [portable/README.md](portable/README.md) |
| `old/` | **Versión original (legacy)**: solo WAV, voz fija. Deprecada. | [old/README.md](old/README.md) |

## Uso

### CLI

```bash
# Todos los capítulos, formato por defecto (wav)
python new/lector_fanfiction_mejorado.py

# Un solo capítulo, voz femenina, mejor calidad, dos formatos
python new/lector_fanfiction_mejorado.py -c capitulo3.md -v F1 --steps 12 -f wav,mp3

# Toda la novela en mp3, más rápido
python new/lector_fanfiction_mejorado.py -f mp3 --speed 1.3

# Log detallado
python new/lector_fanfiction_mejorado.py --verbose
```

| Opción | Descripción | Default |
|--------|-------------|---------|
| `--capitulo, -c` | Procesar solo un capítulo (`capitulo3.md`). | todos |
| `--voz, -v` | Voz: `M1`–`M5`, `F1`–`F5`. | `M1` |
| `--steps` | Pasos de inferencia (más = mejor calidad, más lento). | `5` |
| `--speed` | Velocidad de habla. | `1.1` |
| `--formato, -f` | Formato(s) de salida: `wav, flac, ogg, mp3`. | `wav` |
| `--verbose, -V` | Logging DEBUG. | — |
| `--quiet, -q` | Solo warnings y errores. | — |

### GUI

```bash
python new/lector_gui.py
```

Ventana Tkinter con lista de capítulos (`Todo` / `Nada` / `Refrescar`, multiselección con `Ctrl+clic`), carpetas de entrada/salida, formatos, voz, sliders de pasos (5–12) y velocidad (0.7–2.0), barra de progreso y panel de log. Se procesa en un hilo aparte (la interfaz no se congela) y `Cancelar` exporta lo generado hasta el momento.

Self-test del motor sin abrir la ventana:

```bash
python new/lector_gui.py --self-test
```

Escribe `audio/_self_test.wav` y termina con `SELF-TEST OK` (exit 0) o `SELF-TEST FAIL` (exit 1).

### Portable

Para distribuir al usuario final: `portable/SupertonicReader-Portable.exe` (compilado desde `portable/`). Al ejecutarse en cualquier PC con Windows extrae la app (ejecutable + dependencias + modelo) a la carpeta del propio instalador y la lanza. No requiere Python. Más detalle en [portable/README.md](portable/README.md).

## Convenciones de carpetas

| Carpeta | Rol |
|---------|-----|
| `fanfic/` | Capítulos de entrada (`.md`). Se crea automáticamente. |
| `audio/` | Audios de salida, un archivo por capítulo. Se crea automáticamente. |
| `modelo/` | Caché offline del modelo (assets ONNX + voces). Si existe, la app no necesita red. |

En la CLI las carpetas son relativas al directorio de trabajo; en la GUI se eligen desde la ventana.

## Empaquetado

La app se compila a un `.exe` (one-folder, sin consola) con PyInstaller desde `new/`:

```bash
pip install pyinstaller
pyinstaller new/SupertonicReader.spec
```

Produce `new/dist/SupertonicReader/SupertonicReader.exe`. Para distribuir sin conexión, copiá `modelo/` junto al `.exe` y verificá con `SupertonicReader.exe --self-test`.

El instalador portable se construye desde `portable/` contra la app ya compilada:

```bash
pyinstaller portable/SupertonicReader-Portable.spec
```

Produce `portable/dist/SupertonicReader-Portable.exe`. La ruta de la app compilada está fijada en el `.spec` (ajustá `datas` si compilás en otro lugar).

## Créditos

Supertonic Reader es un proyecto independiente que usa el motor de síntesis [Supertonic 3](https://huggingface.co/supertone-inc/supertonic-3) de [Supertone Inc.](https://www.supertone.ai/) — TTS local, on-device, de 99M parámetros con soporte para 31 idiomas. El modelo se distribuye bajo la licencia OpenRAIL-M; consultá los términos en el [repositorio del modelo](https://huggingface.co/Supertone/supertonic-3).

## Licencia

El código de este proyecto se distribuye bajo la MIT License.
