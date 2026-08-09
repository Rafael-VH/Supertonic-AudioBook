# Capa de dominio (`app/domain/`)

Capa más interna: reglas de negocio PURAS. Solo importa stdlib y `numpy` (para los tipos de audio). No conoce Supertonic, soundfile ni Tkinter. Todo lo que vive acá se puede probar sin hardware, sin red y sin GUI.

## Entidades

### `entities/archivo.py` — `Archivo`

`@dataclass(frozen=True)` con un único atributo y dos propiedades derivadas:

| Miembro | Tipo | Descripción |
|---------|------|-------------|
| `ruta` | `Path` | Ruta al archivo `.md` de entrada |
| `nombre` (propiedad) | `str` | `ruta.name` (ej: `archivo3.md`) |
| `titulo` (propiedad) | `str` | `ruta.stem` (ej: `archivo3`); da nombre al audio de salida |

## Contratos (Protocols) — `repositories/`

Interfaces que el dominio necesita del mundo exterior. Las implementaciones viven en `data/`. El dominio usa `typing.Protocol` para no depender de clases concretas.

### `repositories/motor_tts.py` — `MotorTTS`

```python
def sintetizar(self, texto: str, *, steps: int, speed: float, lang: str = DEFAULT_LANG) -> np.ndarray
```

Convierte texto a audio. Devuelve un array numpy 1D `float32` con las muestras; **vacío** si no se generó audio (el caso de uso lo omite y sigue).

Constantes de producto (las que decide el negocio):

| Constante | Valor | Significado |
|-----------|-------|-------------|
| `DEFAULT_VOICE` | `"M1"` | Voz por defecto del producto |
| `DEFAULT_LANG` | `"es"` | Idioma de síntesis por defecto (código de `LANGUAGES_VOZ`) |
| `LANGUAGES_VOZ` | 32 códigos | Idiomas soportados por supertonic-3 (31 + `"na"` = texto sin idioma) |
| `DEFAULT_TTS_STEPS` | `5` | Pasos de inferencia (más = mejor calidad, más lento) |
| `DEFAULT_SPEED` | `1.1` | Velocidad de habla (`1.0` = normal) |

> Estas constantes las consumen CLI y GUI para los valores por defecto de sus controles. Si cambiás la voz/idioma/steps/speed por defecto, se hace ACÁ, no en presentación.

### `repositories/repositorio_archivos.py` — `RepositorioArchivos`

```python
crear_carpetas_si_no_existen(self, *carpetas: str) -> None
listar_archivos_md(self, carpeta: str = "archivos") -> List[Path]
leer_archivo(self, ruta: Path) -> str   # UTF-8
```

### `repositories/exportador_audio.py` — `ExportadorAudio`

| Método | Propósito |
|--------|-----------|
| `escribir_audio(fragmentos, ruta, formato)` | Concatena y escribe en un formato dado |
| `wav_append(fragmentos, ruta)` | Agrega al final de un WAV PCM_16 existente (volcado por memoria) |
| `convertir_desde_wav(ruta_wav, ruta_destino, formato)` | Re-encoda un WAV a otro formato |
| `duracion_audio(ruta) -> float` | Duración en segundos (0.0 si no se puede leer) |

## Casos de uso — `use_cases/`

### `formato.py` — regla de formatos soportados

| Constante/Función | Detalle |
|-------------------|---------|
| `FORMATOS_NATIVOS` | `("wav", "flac", "ogg", "mp3")` — los únicos soportados, sin ffmpeg |
| `normalizar_formatos(cadena)` | `"wav,MP3"` → `["wav", "mp3"]`. Minúsculas, sin espacios, sin duplicados, orden de aparición. Lanza `ValueError` si algún formato no existe. |

### `limpiar_markdown.py` — `limpiar_markdown(texto)`

Función pura que elimina sintaxis Markdown con `re.sub` en cadena: bloques de código (```` ``` ```` y `~~~`), títulos (`#`), negrita/cursiva (`*` `_`), inline code (`` ` ``), links `[texto](url)` → texto, imágenes `![alt](url)` → alt, blockquotes (`>`), listas (`- ` `* ` `+ ` y `1. `), líneas horizontales (3+ marcadores: `---`, `***`, `- - -`, ...) y saltos de línea. Normaliza 3+ saltos a 2.

Reglas de seguridad (evitan corromper prosa que el TTS va a leer en voz alta):

- El énfasis no se come operadores ni identificadores: `2 * 3 * 4 = 24`, `a*b*c`, `clave_privada_valor` sobreviven intactos; `**negrita**`, `*cursiva*`, `***ambas***` se limpian.
- Énfasis pegado a palabra (`**a**b`, `la **mejor**opcion`, `**Nota:***esto*`) se conserva literal en vez de quedar medio comido.
- Listas, blockquote y líneas horizontales están ancladas al inicio de línea completa: `5 > 3`, `a---b`, `a * b` o `2024. Cifra` no se pierden en medio de la prosa.
- Los bloques de código se quitan ANTES que los inline para no corromper su contenido.

### `segmentar_texto.py` — reglas de segmentación

| Constante | Valor | Regla |
|-----------|-------|-------|
| `MAX_CHARS_PER_SEGMENT` | `1500` | Máximo de caracteres por fragmento de audio |
| `MERGE_THRESHOLD` | `200` | Párrafos con menos caracteres se fusionan con el siguiente |
| `_ABREVIATURAS` | `Dr, Dra, Sr, Sra, etc, i.e, e.g, vs, ...` | Cuyo punto NO es fin de oración |

`segmentar_texto(texto_plano) -> List[str]`:

1. Divide por saltos de línea (párrafos).
2. Fusiona párrafos cortos (< 200) con el siguiente, si no exceden 1500.
3. Si un párrafo excede 1500, lo parte por oraciones.

**Gotcha técnico** (`_dividir_en_oraciones`): Python `re` no soporta lookbehind de ancho variable, así que un patrón con alternancia de largos distintos crashea con `re.error`. La solución es reemplazar temporalmente el punto de cada abreviatura por un carácter neutro (`\x00`), partir por `re.split(r"(?<=\.)\s+", ...)` y restaurar los puntos.

### `procesar_archivo.py` — `ProcesarArchivo` (el orquestador)

```python
ProcesarArchivo(motor, archivos, exportador, *,
                 silencio_muestras: int, memoria_safe_margin_bytes: int)

procesar(archivo: Archivo, ruta_base: Path, *,
         steps: int, speed: float, formatos: List[str],
         lang: str = DEFAULT_LANG,
         on_progreso: Callable[[int, int], None] | None = None,
         debe_detenerse: Callable[[], bool] | None = None) -> None
```

### `sintetizar_muestra.py` — `SintetizarMuestra` (prueba de voz)

```python
SintetizarMuestra(motor: MotorTTS, exportador: ExportadorAudio)

generar(texto: str, *, lang: str = DEFAULT_LANG, ruta: Path) -> Path
```

Genera un WAV PCM corto con el motor y el exportador inyectados, sin pasar
por el pipeline de archivos. Lo usa la GUI para probar una voz con el idioma
seleccionado antes de procesar. Se compone en `main.py` con
`fabrica_muestra(voz)`.

- **Inyección de valores técnicos**: `silencio_muestras` y `memoria_safe_margin_bytes` NO se importan de `data/`; se inyectan desde la raíz de composición. El dominio no conoce `config.py`.
- `ruta_base` es la ruta de salida sin extensión (ej: `audio/archivo`); el método agrega `.formato`.
- Flujo completo: leer → limpiar → segmentar → sintetizar (con volcado por RAM) → exportar. Detalle en [architecture.md](architecture.md), sección "Pipeline".
- Comportamientos clave:
  - Un segmento vacío (0 muestras) se omite sin abortar.
  - Un archivo que no se pudo leer o quedó vacío se omite con log.
  - Cancelación entre segmentos exporta lo generado hasta ahora.
  - Si no se generó NINGÚN fragmento: `log.error` y return sin archivos.
  - Al final loguea la duración real de cada archivo (`duracion_audio`).
- **Publicación atómica por archivo**: el WAV de trabajo es SIEMPRE un temporal; cada salida se publica con `os.replace` (atómico) recién cuando está completa. Si la corrida se cancela o falla durante la síntesis, el output previo de cada formato queda intacto. Los formatos se deduplican (`dict.fromkeys`) y cada corrida regenera SOLO los pedidos; salidas viejas de formatos no pedidos permanecen en disco.
- **Orden de publicación**: en la fase 2 el WAV se publica ÚLTIMO (`_orden_publicacion`). Si falla un formato no-WAV (ej: archivo abierto en otra app → `PermissionError` logueado y propagado), el WAV previo no se reemplaza, aunque los formatos ya publicados sí quedaron actualizados.
