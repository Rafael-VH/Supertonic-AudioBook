# Documentación de Supertonic-AudioBook

Conversor de capítulos en Markdown a audios con voz sintética (TTS local, on-device, motor Supertonic 3). Este directorio documenta la arquitectura y el comportamiento de TODO el proyecto: capas, contratos, implementaciones, interfaces y empaquetado.

**Para agentes y desarrolladores**: si vas a modificar código, buscar información o revisar una función, empezá por el [mapa de arquitectura](architecture.md) y usá este índice para ir directo al módulo que necesitás.

## Índice de documentos

| Documento | Contenido | Cuándo consultarlo |
|-----------|-----------|--------------------|
| [architecture.md](architecture.md) | Estructura en 3 capas (domain/data/presentation), regla de dependencia, raíz de composición. | Antes de cualquier cambio: para saber DÓNDE vive cada cosa. |
| [domain.md](domain.md) | Contratos (Protocols), entidades y casos de uso puros. Reglas de negocio. | Para cambiar reglas de negocio, formatos, segmentación o el pipeline. |
| [data.md](data.md) | Implementaciones concretas: motor TTS, repositorio de archivos, exportador de audio y constantes técnicas. | Para tocar el SDK de Supertonic, soundfile, rutas o configuración. |
| [presentation.md](presentation.md) | CLI (argparse + tqdm), GUI (Tkinter) y self-test. | Para tocar la experiencia de usuario o los argumentos de la CLI. |
| [packaging.md](packaging.md) | Builds con PyInstaller (one-folder) e instaladores portables (completo y Lite). | Para empaquetar, distribuir o entender `app/dist` y `packaging/`. |

## Mapa rápido: qué carpeta tocar según el cambio

| Querés... | Vas a | Capa |
|-----------|-------|------|
| Cambiar cómo se segmenta el texto o las reglas de formato | `app/domain/use_cases/` | domain |
| Cambiar formatos soportados (`wav, flac, ogg, mp3`) | `app/domain/use_cases/formato.py` | domain |
| Cambiar la entidad `Capitulo` | `app/domain/entities/capitulo.py` | domain |
| Cambiar la voz por defecto, steps o speed | `app/domain/repositories/motor_tts.py` | domain |
| Cambiar el SDK de síntesis (llamadas a `TTS`) | `app/data/repositories/motor_tts.py` | data |
| Cambiar cómo se escribe el audio o los subtipos soundfile | `app/data/repositories/exportador_audio.py` + `app/data/config.py` | data |
| Cambiar carpetas de trabajo, caché del modelo, sample rate | `app/data/config.py` | data |
| Cambiar argumentos de la CLI o la barra de progreso | `app/presentation/cli.py` | presentation |
| Cambiar la ventana Tkinter | `app/presentation/gui.py` | presentation |
| Cablear nuevas implementaciones | `app/main.py` | raíz de composición |
| Cambiar el `.exe` o los instaladores | `app/SupertonicAudioBook.spec`, `packaging/*` | empaquetado |

## Regla de oro

`app/main.py` es el ÚNICO archivo que importa `data/`. La presentación y el dominio consumen solo contratos (interfaces) y casos de uso. Si un archivo fuera de `data/` importa `from data...`, es un error de arquitectura. Detalles en [architecture.md](architecture.md).

## Convenciones del proyecto

- **Idioma**: código, docstrings y docs en español (el proyecto es 100% en español, incluida la interfaz).
- **Código**: Python 3.10+, anotaciones de tipos en todas las firmas, logging con el logger `"lector"`.
- **Commits**: conventional commits (ej: `feat:`, `refactor:`, `docs:`), sin atribución de IA.
- **Carpetas de datos**: `archivos/` (entrada .md), `audio/` (salida), `modelo/` (caché del modelo offline). Se crean automáticamente.
