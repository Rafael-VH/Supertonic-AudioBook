# Arquitectura

Supertonic-AudioBook usa **arquitectura limpia en 3 capas**. La regla que lo gobierna todo es la **Regla de Dependencia**: las dependencias apuntan SIEMPRE hacia adentro (hacia el dominio). Nada del dominio conoce el mundo exterior.

## La decisión en una frase

Partimos de un monolito (`lector_fanfiction_mejorado.py` + `lector_gui.py`) y lo partimos en capas para que quede claro qué carpeta modificar: el dominio decide CÓMO convertir, los datos saben CÓMO hablar con el mundo (SDK, disco, audio) y la presentación solo muestra y recoge intenciones del usuario.

## Estructura

```
app/
├── main.py                  # Raíz de composición (composition root)
├── domain/                  # Capa más interna: reglas de negocio puras
│   ├── entities/            #   Archivo
│   ├── repositories/        #   Contratos (Protocols) + constantes de producto
│   └── use_cases/           #   Pipeline: limpiar, segmentar, procesar, formatos
├── data/                    # Implementaciones concretas del mundo exterior
│   ├── config.py            #   Constantes técnicas + configurar_entorno()
│   └── repositories/        #   MotorSupertonic, RepositorioArchivosLocal, ExportadorAudioSoundfile, PreferenciasJSONLocal
├── presentation/            # Interfaz de usuario (consume SOLO inyecciones)
│   ├── cli.py               #   argparse + tqdm (con fallback dummy)
│   ├── gui.py               #   Tkinter
│   └── self_test.py         #   Verificación del motor sin ventana
└── SupertonicAudioBook.spec # PyInstaller (one-folder, sin consola)
```

## Regla de dependencia (la ley del proyecto)

| Capa | Puede importar | NUNCA importa |
|------|----------------|---------------|
| `domain/` | stdlib, `numpy` (tipos de audio) | `data/`, `presentation/`, SDKs externos |
| `data/` | `domain/` (para satisfacer contratos) | `presentation/` |
| `presentation/` | `domain/` (use cases, entidades, constantes) | `data/` |

> **La regla de oro**: si un archivo fuera de `app/data/` contiene `from data...`, es un error. La presentación recibe sus dependencias YA inyectadas; no las construye.

## Raíz de composición: `app/main.py`

Es el ÚNICO lugar que conoce las implementaciones concretas. Se ejecuta según los args:

| Comando | Qué hace |
|---------|----------|
| `python main.py` | Abre la GUI (Tkinter) |
| `python main.py --cli [opciones]` | Ejecuta la CLI |
| `python main.py --self-test` | Verifica motor + síntesis y sale |

Funciones de composición expuestas:

- `CARPETA_BASE = configurar_entorno()` — resuelve la carpeta base (junto al exe si está empaquetada, si no `app/`) y apunta la caché del modelo a `modelo/`.
- `fabrica_motor(voz) -> MotorTTS` — crea `MotorSupertonic` con la voz pedida.
- `fabrica_muestra(voz) -> SintetizarMuestra` — compone el caso de uso de muestra de voz (motor + exportador) para el botón "Escuchar" de la GUI.
- `fabrica_use_case(voz) -> ProcesarArchivo` — compone el caso de uso completo con motor, repositorio y exportador concretos, inyectando `SILENCE_SAMPLES` y `MEMORY_SAFE_MARGIN_BYTES`.

Por eso `fabrica_use_case` acepta la voz como parámetro: la CLI/GUI la toman del usuario y la raíz recompone un caso de uso por cada voz.

## Flujo de datos de un procesamiento

```
GUI/CLI (usuario elige voz, formatos, steps, speed)
   │  inyecta dependencias desde main.py
   ▼
ProcesarArchivo (domain/use_cases)  ← orquesta, NO implementa
   ├── RepositorioArchivos.leer_archivo()      → texto .md
   ├── limpiar_markdown()                      → texto plano
   ├── segmentar_texto()                       → lista de segmentos
   ├── MotorTTS.sintetizar(segmento)           → np.ndarray (float32)
   ├── ExportadorAudio.*                       → .wav/.flac/.ogg/.mp3
   └── on_progreso / debe_detenerse            → callbacks hacia la UI
```

## Pipeline del caso de uso (ProcesarArchivo.procesar)

1. **Leer y limpiar**: `leer_archivo` → `limpiar_markdown`. Si falla o queda vacío, se omite el archivo.
2. **Segmentar**: `segmentar_texto` con reglas de fusión/límites (ver [domain.md](domain.md)).
3. **Sintetizar incrementalmente**: por cada segmento llama `motor.sintetizar` y acumula en RAM. Si el audio acumulado supera `memoria_safe_margin_bytes` (~500 MB), vuelca a disco con `wav_append` (protección de memoria para libros largos).
4. **Cancelación**: `debe_detenerse()` se consulta entre segmentos; si devuelve `True`, se exporta lo generado hasta ese momento.
5. **Exportar**: si hubo volcado parcial usa `wav_append` + `convertir_desde_wav` (y un WAV temporal si `wav` no está en los formatos); si no, `escribir_audio` directo.

## Notas técnicas clave

- **WAV de trabajo**: si `wav` está entre los formatos, el archivo final ES el WAV. Si no, se usa un `tempfile.mkstemp` como fuente intermedia y se borra en el `finally`.
- **Callbacks de progreso**: `on_progreso(procesados, total)` y `debe_detenerse()` los implementa la capa de presentación (tqdm en CLI, cola + eventos en GUI). El dominio no sabe de UI.
- **Logging**: un solo logger `"lector"` en todo el código. La GUI le agrega un handler que reenvía a su cola.
- **Imports absolutos**: `main.py` usa `from data...`, `from domain...`, por lo que se ejecuta con `cwd = app/`. El spec de PyInstaller fija `pathex=[SPECPATH]` para no depender del directorio.
