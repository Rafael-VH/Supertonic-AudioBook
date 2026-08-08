# Supertonic Reader

Conversor de capítulos en Markdown a audios con voz sintética, basado en el motor [Supertonic 3](https://huggingface.co/spaces/Supertone/supertonic-3) (TTS local, on-device, sin llamadas a la nube).

Incluye dos interfaces:

- **CLI** — `lector_fanfiction_mejorado.py`: procesa capítulos desde la terminal.
- **GUI** — `lector_gui.py`: ventana Tkinter con selección de capítulos, formatos, voz y parámetros del TTS, sin necesidad de la terminal.

## Características

- Exportación multi-formato **nativa**: `wav`, `flac`, `ogg` y `mp3` (sin ffmpeg).
- **Natural sorting** de capítulos: `capitulo10.md` va después de `capitulo2.md`.
- Limpieza automática de sintaxis Markdown (títulos, listas, links, imágenes, bloques de código, etc.).
- Segmentación de texto optimizada para TTS con soporte de abreviaturas del español (`Dr.`, `Sr.`, `etc.`, ...).
- **Protección de memoria para libros largos**: volcado incremental a disco cuando los fragmentos acumulados superan ~500 MB.
- Manejo de errores en síntesis: un fragmento fallido no aborta el capítulo.
- Validación de la voz antes de usarla.
- Barra de progreso con `tqdm` (opcional).
- Logging granular (`--verbose` / `--quiet`).
- En la GUI: cancelación en cualquier momento (exporta lo generado hasta entonces) y `--self-test` para verificar el motor sin abrir la ventana.

## Requisitos

- **Python 3.10+** (el código usa anotaciones de tipo modernas; probado con Python 3.14).
- **supertonic** — SDK TTS.
- **numpy** — procesamiento de audio.
- **soundfile** — escritura de audio en los 4 formatos.
- **tqdm** *(opcional)* — barra de progreso. Si no está instalado, se reemplaza por un dummy y todo funciona igual.
- **Tkinter** *(solo GUI)* — incluido en la instalación estándar de Python en Windows.
- **PyInstaller** *(solo empaquetado)*.

> **Red**: solo se necesita la primera vez, para descargar el modelo. Si existe una carpeta `modelo/` con los assets, la app funciona completamente offline.

## Instalación

```bash
pip install supertonic numpy soundfile
pip install tqdm            # opcional: barra de progreso
pip install pyinstaller     # opcional: para empaquetar el .exe
```

## Uso — CLI

Desde la carpeta del proyecto, con los capítulos `.md` dentro de `fanfic/`:

```bash
python lector_fanfiction_mejorado.py
python lector_fanfiction_mejorado.py --capitulo capitulo3.md
python lector_fanfiction_mejorado.py --voz F1 --steps 10
python lector_fanfiction_mejorado.py --formato mp3
python lector_fanfiction_mejorado.py --formato wav,mp3,flac
python lector_fanfiction_mejorado.py --verbose
```

### Opciones

| Opción | Descripción | Default |
|--------|-------------|---------|
| `--capitulo, -c ARCHIVO` | Procesar solo un capítulo (ej: `capitulo3.md`). Debe existir dentro de `fanfic/`. Sin esta opción se procesan todos los `.md` encontrados. | todos |
| `--voz, -v` | Voz a usar. Voces disponibles: `M1`–`M5`, `F1`–`F5`. | `M1` |
| `--steps` | Pasos de inferencia del TTS. Más pasos = mejor calidad, más lento. | `5` |
| `--speed` | Velocidad de habla (`1.0` = normal). | `1.1` |
| `--formato, -f FORMATOS` | Formato(s) de salida separados por coma. Válidos: `wav, flac, ogg, mp3`. | `wav` |
| `--verbose, -V` | Modo verbose (logging DEBUG). | — |
| `--quiet, -q` | Modo silencioso (solo warnings y errores). | — |

### Ejemplos

```bash
# Un solo capítulo, voz femenina, mejor calidad, dos formatos
python lector_fanfiction_mejorado.py -c capitulo3.md -v F1 --steps 12 -f wav,mp3

# Toda la novela en mp3, más rápido
python lector_fanfiction_mejorado.py -f mp3 --speed 1.3
```

## Uso — GUI

```bash
python lector_gui.py
```

La ventana permite:

- Elegir la **carpeta de entrada** (por defecto `fanfic/`) y ver la lista de capítulos `.md`.
  - Botones `Todo`, `Nada` y `Refrescar`.
  - `Ctrl+clic` para elegir varios; sin selección se procesan todos.
- Elegir la **carpeta de salida** (por defecto `audio/`).
- Marcar los **formatos de salida** (`WAV`, `FLAC`, `OGG`, `MP3`; `WAV` y `MP3` marcados por defecto).
- Elegir **voz** (`M1`–`M5`, `F1`–`F5`), **pasos** (slider 5–12) y **velocidad** (slider 0.7–2.0).
- `Procesar` para lanzar la conversión en un hilo aparte (la interfaz no se congela) y `Cancelar` para detenerla — se exporta lo generado hasta el momento.
- Seguir el avance con la barra de progreso y el panel de registro (log) con niveles coloreados.

### Self-test

Verifica el motor y una síntesis real sin abrir la ventana. Pensado para probar el ejecutable empaquetado:

```bash
python lector_gui.py --self-test
SupertonicReader.exe --self-test
```

Escribe `audio/_self_test.wav`, imprime `SELF-TEST OK` (exit code `0`) o `SELF-TEST FAIL` (exit code `1`).

## Formatos de salida

`wav`, `flac`, `ogg` y `mp3` se escriben directamente con `soundfile` (subtipos `PCM_16`, `PCM_16`, `VORBIS` y `MPEG_LAYER_III`), sin necesidad de ffmpeg. Se pueden pedir varios a la vez separados por coma.

## Convenciones de carpetas

| Carpeta | Rol |
|---------|-----|
| `fanfic/` | Capítulos de entrada (`.md`). Se crea automáticamente si no existe. |
| `audio/` | Audio de salida. Se crea automáticamente; cada archivo usa el nombre del capítulo (ej: `capitulo3.wav`). |
| `modelo/` | Caché offline del modelo (assets ONNX + voces). En el ejecutable empaquetado, si esta carpeta existe junto al `.exe` la app funciona sin red; si no existe, el modelo se descarga al primer uso. |

En la CLI las carpetas son relativas al directorio de trabajo. En la GUI se pueden cambiar ambas carpetas desde la ventana.

## Detalles de síntesis

- **Voces**: `M1`–`M5` y `F1`–`F5` (10 voces del modelo supertonic-3).
- **Idioma**: español (`lang="es"`).
- **Pasos de inferencia**: default `5`; en la GUI el slider va de `5` a `12` (más = mejor calidad, más lento).
- **Velocidad**: default `1.1`; en la GUI el slider va de `0.7` a `2.0`.
- **Máximo de caracteres por segmento**: 1500. Los párrafos de menos de 200 caracteres se fusionan con el siguiente.
- **Silencio entre segmentos**: 0.6 s.
- **Frecuencia de muestreo**: 44100 Hz.
- **Memoria**: si los fragmentos acumulados superan ~500 MB (libros muy largos), se vuelcan a disco de forma incremental — el capítulo nunca se pierde por falta de RAM.

## Empaquetado con PyInstaller

El proyecto incluye `SupertonicReader.spec`, que genera una build **one-folder** (ventana, sin consola) a partir de `lector_gui.py`:

```bash
pyinstaller SupertonicReader.spec
```

El spec recolecta automáticamente los datos de `huggingface_hub` (`collect_all`) y produce:

```
dist/SupertonicReader/SupertonicReader.exe
```

Para distribuir sin conexión, copia la carpeta `modelo/` al lado del `SupertonicReader.exe` (en la versión empaquetada, `SUPERTONIC_CACHE_DIR` apunta automáticamente a esa carpeta). Verifica la instalación con:

```bash
SupertonicReader.exe --self-test
```
