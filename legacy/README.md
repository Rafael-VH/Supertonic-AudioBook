<div align="center">

# 🗂️ legacy/ — Versión original (deprecada)

**Lector de Fanfiction — primera versión del conversor Markdown → audio.**

> [!WARNING]
> **DEPRECADO**: esta carpeta contiene la versión ORIGINAL del conversor de Markdown a audio con el SDK Supertonic TTS. Fue reemplazada por la versión actual en [`../app/`](../app/README.md). **No empieces aquí**: usa `python ../app/main.py --cli` (CLI) o `python ../app/main.py` (interfaz gráfica).

</div>

## Qué es

`lector_fanfiction.py` convierte capítulos en formato Markdown (`.md`) a archivos de audio **WAV** usando síntesis de voz en español con el SDK `supertonic` TTS.

Flujo de trabajo:

1. Lee los archivos `.md` de la carpeta `archivos/`.
2. Limpia el Markdown (encabezados, negritas, cursivas, enlaces, citas, listas, bloques de código, etc.).
3. Segmenta el texto en fragmentos de hasta ~1500 caracteres para sintetizar.
4. Sintetiza cada fragmento en español (voz `M1`, `total_steps=5`, `speed=1.1`), insertando 0.6 s de silencio entre fragmentos.
5. Concatena todo y exporta un único WAV por capítulo en `audio/`.

**Salida**: únicamente WAV a 44 100 Hz (no soporta otros formatos).

## Contenido de la carpeta

| Archivo | Descripción |
|---|---|
| `lector_fanfiction.py` | Script principal: conversor Markdown → WAV (voz `M1`, español). |
| `iniciar_lector_fanfiction.bat` | Launcher de Windows: se posiciona en la carpeta del script, ejecuta `py lector_fanfiction.py` y mantiene la consola abierta (`pause`). |

## Convención de carpetas

El script crea automáticamente las carpetas si no existen:

- `archivos/` — entrada: coloca aquí los capítulos en Markdown (`.md`).
- `audio/` — salida: un archivo WAV por capítulo (`audio/<nombre_del_capitulo>.wav`).

Si `archivos/` está vacía o no tiene archivos `.md`, el script avisa y termina.

## Requisitos

- Python 3 (se invoca con `py` desde el `.bat`).
- Dependencias: `supertonic`, `numpy`, `soundfile`.
- En el primer uso, `TTS(auto_download=True)` descarga el modelo automáticamente (requiere conexión a internet).

## Uso básico

1. Instala las dependencias:

   ```
   pip install supertonic numpy soundfile
   ```

2. Crea `archivos/` y coloca tus capítulos en Markdown (por ejemplo, `capitulo_01.md`).

3. Ejecuta:

   ```
   py lector_fanfiction.py
   ```

   O simplemente haz doble clic en `iniciar_lector_fanfiction.bat`.

4. Encuentra el audio resultante en `audio/capitulo_01.wav`.

## Limitaciones (razones para migrar a `../app/`)

- Solo exporta WAV.
- Voz fija `M1`, sin selección por capítulo.
- Sin interfaz gráfica, sin barra de progreso visual ni opciones de configuración.
- Mensajes de progreso solo por consola.
