<div align="center">

# 🎧 Supertonic-AudioBook

**Convertí tus libros Markdown en audiolibros con voz sintética — 100% local.**

Lee archivos `.md`, los limpia, los segmenta y los convierte en audiolibros con el motor
[Supertonic 3](https://huggingface.co/spaces/Supertone/supertonic-3) (TTS on-device basado en ONNX Runtime),
con voces sintéticas en 31 idiomas + auto.
Sin nube. Sin API. Sin GPU. Sin ffmpeg.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=1f2937)
![Windows](https://img.shields.io/badge/Windows-ok-0078D6?style=for-the-badge&logo=windows&logoColor=white&labelColor=1f2937)
![TTS local](https://img.shields.io/badge/TTS-100%25%20local-22c55e?style=for-the-badge&logo=speakerdeck&logoColor=white&labelColor=1f2937)
![Licencia](https://img.shields.io/badge/Licencia-MIT-22c55e?style=for-the-badge&logo=github&logoColor=white&labelColor=1f2937)

**[Quick start](#quick-start) · [Características](#características) · [Uso](#uso) · [Estructura](#estructura-del-proyecto) · [Empaquetado](#empaquetado) · [Créditos](#créditos)**

---

</div>

## Quick start

```bash
pip install supertonic numpy soundfile
python app/main.py --cli
```

1. **Instalá** las dependencias (`Python 3.10+`).
2. **Poné tus archivos** en `archivos/` (Markdown, un archivo por sección).
3. **Ejecutá** la CLI: `python app/main.py --cli`.
4. **Escuchá** los resultados en `audio/` (por defecto `archivoN.wav`).

> 💡 **Offline**: la primera ejecución descarga el modelo (~1 vez, requiere red). Si copiás una carpeta `modelo/` con los assets junto a los scripts, funciona 100% sin conexión.

¿Preferís una ventana? La GUI también está lista: `python app/main.py`. Más abajo en [Uso](#uso).

---

## Características

| | | |
|---|---|---|
| 🎚️ **Multi-formato nativo** | 🔊 **Voz en 31 idiomas + auto** | 🧹 **Limpieza automática de Markdown** |
| `wav`, `flac`, `ogg` y `mp3` sin ffmpeg, varios a la vez. | 10 voces (`M1`–`M5`, `F1`–`F5`), 31 idiomas de voz + auto, pasos y velocidad ajustables. | Títulos, listas, links, citas y bloques de código, sin restos. |
| 🧠 **Segmentación optimizada para TTS** | 🛡️ **Protección de memoria** | 🔢 **Natural sorting** |
| Soporta abreviaturas del español (`Dr.`, `Sr.`, `etc.`) para no cortar oraciones. | Volcado incremental a disco desde ~500 MB: libros largos nunca se pierden. | `archivo10.md` va después de `archivo2.md`, no de `archivo9`. |
| 🖥️ **CLI + GUI** | 📦 **Empaquetable en `.exe`** | 💪 **Tolerante a fallos** |
| Terminal con argparse o ventana Tkinter sin congelarse. | Aplicación one-folder e instalador portable de un solo archivo. | Un fragmento que falla no aborta el archivo. |
| 🌙 **Tema + i18n ES/EN** | ⚙️ **Ventana de ajustes** | ▶️ **Escuchar muestra** |
| GUI clara/oscura en estilo Material, Neumorfismo o Skeuomorfismo, con interfaz en español o inglés. | Preferencias persistentes: tema, estilo, idioma, voz, idioma de la voz, formatos y carpetas. | Sintetiza y reproduce una muestra con la voz e idioma elegidos. |

---

## Uso

### CLI

```bash
# Todos los archivos, formato por defecto (wav)
python app/main.py --cli

# Un solo archivo, voz femenina, mejor calidad, dos formatos
python app/main.py --cli -c archivo3.md -v F1 --steps 12 -f wav,mp3

# Toda la novela en mp3, más rápido
python app/main.py --cli -f mp3 --speed 1.3

# Log detallado
python app/main.py --cli --verbose
```

| Opción | Descripción | Default |
|--------|-------------|---------|
| `-c, --archivo ARCHIVO` | Procesar solo un archivo (`archivo3.md`). | todos |
| `-v, --voz VOZ` | Voz: `M1`–`M5`, `F1`–`F5`. | `M1` |
| `--steps` | Pasos de inferencia (más = mejor calidad, más lento). | `5` |
| `--speed` | Velocidad de habla. | `1.1` |
| `-f, --formato FORMATOS` | Formato(s) de salida: `wav, flac, ogg, mp3`. | `wav` |
| `-V, --verbose` | Logging DEBUG. | — |
| `-q, --quiet` | Solo warnings y errores. | — |

### GUI

```bash
python app/main.py
```

Ventana Tkinter con selección de archivos (`Todo` / `Nada` / `Refrescar`, multiselección con `Ctrl+clic`),
carpetas de entrada/salida, formatos, voz, idioma de la voz (31 + auto), sliders de pasos (5–12) y velocidad
(0.7–2.0), y un botón `▶ Escuchar` que reproduce una muestra con la voz e idioma elegidos.
La ventana `⚙` de ajustes cambia el tema (claro/oscuro), el estilo (Material/Neumorfismo/Skeuomorfismo) y el idioma de la interfaz (ES/EN) al instante;
las preferencias (tema, estilo, idioma, voz, idioma de la voz, formatos y carpetas) se guardan entre sesiones.
Se procesa en un hilo aparte (la interfaz nunca se congela) y `Cancelar` exporta lo generado hasta el momento.

### Self-test

Verificá el motor y una síntesis real sin abrir la ventana (pensado para el ejecutable empaquetado):

```bash
python app/main.py --self-test
```

Escribe `audio/_self_test.wav` y termina con `SELF-TEST OK` (exit 0) o `SELF-TEST FAIL` (exit 1).

### Portable

Para el usuario final: instaladores de un solo `.exe` que extraen la app completa junto a sí mismos y la lanzan.
No requieren Python. Más detalle en [`packaging/README.md`](packaging/README.md).

| Instalador | Tamaño aprox. | Modelo TTS |
|---|---|---|
| `SupertonicAudioBook-Portable.exe` | ~417 MB | ✅ Incluido — funciona sin conexión |
| `SupertonicAudioBook-Portable-Lite.exe` | ~60 MB | ⬇️ Se descarga solo al primer uso (requiere internet) |

---

## Estructura del proyecto

| Carpeta | Qué contiene | Documentación |
|---------|--------------|---------------|
| `app/` | **Versión actual** — código en capas (`domain/`, `data/`, `presentation/`), `main.py` como punto de entrada y spec PyInstaller. | [`app/README.md`](app/README.md) |
| `docs/` | **Documentación completa** — arquitectura, dominio, datos, presentación y empaquetado. | [`docs/README.md`](docs/README.md) |
| `packaging/` | **Instalador portable** — un `.exe` que extrae la app completa junto a sí mismo y la lanza. | [`packaging/README.md`](packaging/README.md) |
| `legacy/` | **Versión original** — solo WAV, voz fija. Deprecada. | [`legacy/README.md`](legacy/README.md) |

## Convenciones de carpetas

| Carpeta | Rol |
|---------|-----|
| `archivos/` | Entrada (documentos `.md`). Se crea automáticamente. |
| `audio/` | Audios de salida, uno por archivo de entrada. Se crea automáticamente. |
| `modelo/` | Caché offline del modelo (assets ONNX + voces). Si existe, la app no necesita red. |

En la CLI las carpetas son relativas al directorio de trabajo; en la GUI se eligen desde la ventana.

---

## Empaquetado

La app se compila a un `.exe` (one-folder, sin consola) con PyInstaller:

```bash
pip install pyinstaller
pyinstaller app/SupertonicAudioBook.spec
```

Produce `app/dist/SupertonicAudioBook/SupertonicAudioBook.exe`. Para distribuir sin conexión,
copiá `modelo/` junto al `.exe` y verificá con `SupertonicAudioBook.exe --self-test`.

Los instaladores portables se construyen contra la app ya compilada con un solo comando:

```bash
python packaging/build_portables.py
```

Produce `packaging/dist/SupertonicAudioBook-Portable.exe` (completa, con modelo) y
`packaging/dist/SupertonicAudioBook-Portable-Lite.exe` (lite, sin modelo). Para la variante completa,
copiá `modelo/` en `app/dist/SupertonicAudioBook` antes de construir.

---

## Créditos

Supertonic-AudioBook es un proyecto independiente que usa el motor de síntesis
[Supertonic 3](https://huggingface.co/supertone-inc/supertonic-3) de [Supertone Inc.](https://www.supertone.ai/)
— TTS local, on-device, de 99M parámetros con soporte para 31 idiomas. El modelo se distribuye bajo la
licencia OpenRAIL-M; consultá los términos en el [repositorio del modelo](https://huggingface.co/Supertone/supertonic-3).

## Licencia

El código de este proyecto se distribuye bajo la **MIT License**.
