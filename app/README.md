<div align="center">

# 🎧 Supertonic-AudioBook

**La aplicación — código en capas, CLI + GUI.**

Este módulo contiene la versión actual de la app: `main.py` como punto de entrada,
el código separado en capas (`domain/`, `data/`, `presentation/`) y el spec de PyInstaller.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=1f2937)
![Windows](https://img.shields.io/badge/Windows-ok-0078D6?style=for-the-badge&logo=windows&logoColor=white&labelColor=1f2937)
![TTS local](https://img.shields.io/badge/TTS-100%25%20local-22c55e?style=for-the-badge&logo=speakerdeck&logoColor=white&labelColor=1f2937)
![Licencia](https://img.shields.io/badge/Licencia-MIT-22c55e?style=for-the-badge&logo=github&logoColor=white&labelColor=1f2937)

**[Instalación](#instalación) · [CLI](#uso--cli) · [GUI](#uso--gui) · [Síntesis](#detalles-de-síntesis) · [Empaquetado](#empaquetado-con-pyinstaller)**

---

</div>

Incluye **dos interfaces**:

- 🖥️ **CLI** — `python main.py --cli`: procesa capítulos desde la terminal.
- 🗔 **GUI** — `python main.py` (o `python main.py --gui`): ventana Tkinter con selección de capítulos, formatos, voz y parámetros del TTS, sin necesidad de la terminal.

## Características

- Exportación multi-formato **nativa**: `wav`, `flac`, `ogg` y `mp3` (sin ffmpeg).
- **Natural sorting** de capítulos: `capitulo10.md` va después de `capitulo2.md`.
- Limpieza automática de sintaxis Markdown (títulos, listas, links, imágenes, bloques de código, etc.).
- Segmentación de texto optimizada para TTS con soporte de abreviaturas del español (`Dr.`, `Sr.`, `etc.`).
- **Protección de memoria para libros largos**: volcado incremental a disco cuando los fragmentos acumulados superan ~500 MB.
- Manejo de errores en síntesis: un fragmento fallido no aborta el capítulo.
- Validación de la voz antes de usarla.
- Barra de progreso con `tqdm` (opcional).
- Logging granular (`--verbose` / `--quiet`).
- En la GUI: cancelación en cualquier momento (exporta lo generado hasta entonces) y `--self-test` para verificar el motor sin abrir la ventana.
- **Arquitectura en capas**: `domain/` (reglas puras e interfaces), `data/` (implementaciones del motor, archivos y audio) y `presentation/` (CLI, GUI y self-test). `main.py` es la raíz de composición que las conecta.

## Requisitos

- **Python 3.10+** (el código usa anotaciones de tipo modernas; probado con Python 3.14).
- **supertonic** — SDK TTS.
- **numpy** — procesamiento de audio.
- **soundfile** — escritura de audio en los 4 formatos.
- **tqdm** *(opcional)* — barra de progreso. Si no está instalado, se reemplaza por un dummy y todo funciona igual.
- **Tkinter** *(solo GUI)* — incluido en la instalación estándar de Python en Windows.
- **PyInstaller** *(solo empaquetado)*.

> 💡 **Red**: solo se necesita la primera vez, para descargar el modelo. Si existe una carpeta `modelo/` con los assets, la app funciona completamente offline.

## Instalación

```bash
pip install supertonic numpy soundfile
pip install tqdm            # opcional: barra de progreso
pip install pyinstaller     # opcional: para empaquetar el .exe
```

---

## Uso — CLI

Desde la carpeta del proyecto, con los capítulos `.md` dentro de `archivos/`:

```bash
python main.py --cli
python main.py --cli --capitulo capitulo3.md
python main.py --cli --voz F1 --steps 10
python main.py --cli --formato mp3
python main.py --cli --formato wav,mp3,flac
python main.py --cli --verbose
```

### Opciones

| Opción | Descripción | Default |
|--------|-------------|---------|
| `-c, --capitulo ARCHIVO` | Procesar solo un capítulo (ej: `capitulo3.md`). Debe existir dentro de `archivos/`. Sin esta opción se procesan todos los `.md` encontrados. | todos |
| `-v, --voz VOZ` | Voz a usar. Voces disponibles: `M1`–`M5`, `F1`–`F5`. | `M1` |
| `--steps` | Pasos de inferencia del TTS. Más pasos = mejor calidad, más lento. | `5` |
| `--speed` | Velocidad de habla (`1.0` = normal). | `1.1` |
| `-f, --formato FORMATOS` | Formato(s) de salida separados por coma. Válidos: `wav, flac, ogg, mp3`. | `wav` |
| `-V, --verbose` | Modo verbose (logging DEBUG). | — |
| `-q, --quiet` | Modo silencioso (solo warnings y errores). | — |

### Ejemplos

```bash
# Un solo capítulo, voz femenina, mejor calidad, dos formatos
python main.py --cli -c capitulo3.md -v F1 --steps 12 -f wav,mp3

# Toda la novela en mp3, más rápido
python main.py --cli -f mp3 --speed 1.3
```

## Uso — GUI

```bash
python main.py
```

La ventana permite:

- Elegir la **carpeta de entrada** (por defecto `archivos/`) y ver la lista de capítulos `.md`.
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
python main.py --self-test
SupertonicAudioBook.exe --self-test
```

Escribe `audio/_self_test.wav`, imprime `SELF-TEST OK` (exit code `0`) o `SELF-TEST FAIL` (exit code `1`).

---

## Formatos de salida

`wav`, `flac`, `ogg` y `mp3` se escriben directamente con `soundfile` (subtipos `PCM_16`, `PCM_16`, `VORBIS` y `MPEG_LAYER_III`), sin necesidad de ffmpeg. Se pueden pedir varios a la vez separados por coma.

## Convenciones de carpetas

| Carpeta | Rol |
|---------|-----|
| `archivos/` | Capítulos de entrada (`.md`). Se crea automáticamente si no existe. |
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

---

## Empaquetado con PyInstaller

El proyecto incluye `SupertonicAudioBook.spec`, que genera una build **one-folder** (ventana, sin consola) a partir de `main.py`:

```bash
pyinstaller SupertonicAudioBook.spec
```

El spec recolecta automáticamente los datos de `huggingface_hub` (`collect_all`) y produce:

```
dist/SupertonicAudioBook/SupertonicAudioBook.exe
```

Para distribuir sin conexión, copia la carpeta `modelo/` al lado del `SupertonicAudioBook.exe` (en la versión empaquetada, `SUPERTONIC_CACHE_DIR` apunta automáticamente a esa carpeta). Verifica la instalación con:

```bash
SupertonicAudioBook.exe --self-test
```
