# Capa de datos (`app/data/`)

Implementaciones CONCRETAS de los contratos del dominio. Esta capa es el único lugar donde viven las dependencias externas: `supertonic`, `soundfile`, `pathlib` de escritura. Si se reemplaza una tecnología (otro motor TTS, otra lib de audio), se toca SOLO acá.

## Configuración técnica — `config.py`

Constantes del mundo del audio. La lógica de negocio vive en `domain/`; acá solo lo técnico.

| Constante | Valor | Uso |
|-----------|-------|-----|
| `SAMPLE_RATE` | `44100` | Frecuencia de muestreo (Hz) |
| `SILENCE_DURATION_SECS` | `0.6` | Silencio entre fragmentos (s) |
| `SILENCE_SAMPLES` | `int(SAMPLE_RATE * SILENCE_DURATION_SECS)` | = 26460 muestras de silencio; se inyecta al caso de uso |
| `SUBTIPOS_AUDIO` | `{"wav": "PCM_16", "flac": "PCM_16", "ogg": "VORBIS", "mp3": "MPEG_LAYER_III"}` | Subtipo soundfile por formato |
| `MEMORY_SAFE_MARGIN_BYTES` | `500 * 1024 * 1024` (~500 MB) | Umbral de volcado parcial por RAM |

### `configurar_entorno() -> Path`

Apunta la caché del modelo a la carpeta `modelo/` local y devuelve la carpeta base:

```python
os.environ.setdefault("SUPERTONIC_CACHE_DIR", str(base / "modelo"))
```

La carpeta base (`_carpeta_base()`) se resuelve así:

- **Empaquetado** (`sys.frozen`): junto al `.exe` (`sys.executable`).
- **En desarrollo**: `parents[1]` de `data/config.py` = `app/`.

Se llama en `main.py` (raíz) y de nuevo en `MotorSupertonic.__init__` (por seguridad, usando `setdefault` para no pisar).

## Implementaciones — `repositories/`

### `motor_tts.py` — `MotorSupertonic`

Wrapper alrededor de `supertonic.TTS` que satisface el contrato `MotorTTS`. Es la ÚNICA clase que importa `supertonic`.

| Aspecto | Detalle |
|---------|---------|
| Inicialización | **Lazy**: el engine `TTS(auto_download=True)` se crea recién en `_asegurar_inicializado()`, no en el constructor |
| Constructor | `MotorSupertonic(voz="M1")` — llama `configurar_entorno()`, guarda la voz, `_engine=None`, `_style=None` |
| Validación de voz | En el primer uso: `engine.get_voice_style(voice_name=voz)`; si falla, `ValueError` con mensaje que sugiere `engine.list_voices()` |
| Propiedades | `engine` y `style` exponen el estado lazy (aseguran inicialización y lanzan `assert`) |
| `sintetizar(texto, *, steps, speed, lang=DEFAULT_LANG)` | Llama `engine.synthesize(texto, voice_style=style, lang=lang, total_steps=steps, speed=speed)`. Devuelve `np.atleast_1d(wav.squeeze()).astype(np.float32)` |
| Tolerancia a fallos | Un error de síntesis → `log.error` y devuelve array vacío (no aborta el archivo) |
| Silencios | Fragmento de 0 muestras → warning y array vacío |

### `repositorio_archivos.py` — `RepositorioArchivosLocal`

Implementación con pathlib del contrato `RepositorioArchivos`.

| Método | Detalle |
|--------|---------|
| `crear_carpetas_si_no_existen(*carpetas)` | `Path(nombre).mkdir(exist_ok=True)` por carpeta |
| `listar_archivos_md(carpeta="archivos")` | Filtra `.md` (case-insensitive) y ordena con **natural sort**. Carpeta inexistente o sin archivos → warning + lista vacía |
| `leer_archivo(ruta)` | `ruta.read_text(encoding="utf-8")` |

**Natural sort** (`_natural_sort_key`): extrae TODOS los números del `stem` del archivo y los usa como clave de orden. `archivo2.md` → `(2,)`, `archivo10.md` → `(10,)` (va después). Si no hay números, usa el nombre como string. `archivo10` ordena después de `archivo2` en vez de después de `archivo9` como haría el sort lexicográfico.

### `exportador_audio.py` — `ExportadorAudioSoundfile`

Implementación con soundfile + numpy. ÚNICA clase que importa `soundfile`.

| Método | Implementación |
|--------|----------------|
| `escribir_audio` | `np.concatenate(fragmentos)` → `sf.write(ruta, audio, SAMPLE_RATE, subtype=SUBTIPOS_AUDIO[formato])`. Fragmentos vacíos → no-op |
| `wav_append` | Para volcado incremental. Concatena, `np.clip(audio, -1, 1) * 32767 → int16`. Si el archivo no existe o está vacío, `sf.write` normal; si existe, escribe los bytes crudos al final y **parchea el header RIFF** (tamaño de chunk en offset 4 y de datos en offset 40) |
| `convertir_desde_wav` | `sf.read` del WAV → `sf.write` en el formato destino con su subtipo |
| `duracion_audio` | `sf.info` (lee SOLO cabecera, no carga el archivo) → `frames / samplerate`. Error → warning + `0.0` |

> **Gotcha `wav_append`**: soundfile no tiene append nativo para WAV. Se escriben los samples int16 little-endian al final del archivo y se parchean los 2 campos de tamaño del header RIFF. Si el archivo destino existe pero tiene tamaño 0, se reescribe como WAV nuevo.

## Dependencias externas (resumen de la capa)

| Paquete | Dónde se usa |
|---------|--------------|
| `supertonic` | `data/repositories/motor_tts.py` |
| `soundfile` | `data/repositories/exportador_audio.py` |
| `numpy` | todas las implementaciones de data/ (y `domain/` solo para tipos) |
| `huggingface_hub` | solo en el spec (PyInstaller `collect_all`) para empaquetar datos del modelo |
