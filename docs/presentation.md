# Capa de presentación (`app/presentation/`)

Interfaces de usuario. Consume SOLO el dominio (use cases, entidades, constantes) y recibe las dependencias YA inyectadas desde `main.py`. **Nunca importa `data/`.**

## `cli.py` — Interfaz de línea de comandos

Entrada: `main(fabrica_use_case: Callable[[str], ProcesarCapitulo], repositorio: RepositorioArchivos)`.

Argumentos de argparse:

| Opción | Default | Descripción |
|--------|---------|-------------|
| `-c, --capitulo ARCHIVO` | todos | Procesar solo un capítulo (dentro de `archivos/`) |
| `-v, --voz VOZ` | `M1` | Voz (`M1`–`M5`, `F1`–`F5`) |
| `--steps` | `5` | Pasos de inferencia |
| `--speed` | `1.1` | Velocidad de habla |
| `-f, --formato FORMATOS` | `wav` | Formatos separados por coma (`wav, flac, ogg, mp3`) |
| `-V, --verbose` | — | Logging DEBUG |
| `-q, --quiet` | — | Solo warnings y errores |

Comportamiento:

1. Normaliza formatos con `normalizar_formatos` (un formato inválido → `parser.error`).
2. Asegura `archivos/` y `audio/` (`crear_carpetas_si_no_existen`).
3. Si `--capitulo`: verifica que exista en `archivos/` (si no, exit 1). Si no: lista todos los `.md` (si no hay, avisa y termina).
4. Crea el use case con `fabrica_use_case(args.voz)`.
5. Procesa cada capítulo con `ruta_base = audio/<stem>` y `on_progreso=_barra_progreso(...)`.

**tqdm es opcional**: si no está instalado, `_DummyTqdm` (iterable + `set_description`/`update`/`close`/`write` no-op) reemplaza la barra y todo funciona igual. Es UI, por eso vive acá y no en el dominio.

`_barra_progreso(nombre)` devuelve un callback `on_progreso(actual, total)` que ajusta `barra.total` la primera vez (el total se conoce recién tras segmentar) y actualiza `barra.n`.

## `gui.py` — Interfaz gráfica (Tkinter)

Entrada: `AppLector(*, fabrica_use_case, repositorio, carpeta_base, repositorio_preferencias)`. Es un `tk.Tk` con la ventana completa.

| Elemento | Detalle |
|----------|---------|
| `VOCES` | `("M1".."M5", "F1".."F5")` — 10 voces del modelo |
| Tema | Claro/oscuro con paleta Material Design 3 (`PALETA_CLARA`/`PALETA_OSCURA`) |
| Idioma | Español/Inglés (`IDIOMAS`/`TRADUCCIONES`); `self.t(clave)` traduce todos los textos. Se cambia desde Ajustes y se persiste |
| Cabecera | Título + botón de ajustes (`⚙`) que abre la ventana flotante de configuración (`_abrir_ajustes`) |
| Ventana de ajustes | `tk.Toplevel` transiente centrada sobre la principal; muestra la configuración del programa. Secciones: **Tema** (Claro/Oscuro, aplica y guarda al instante) e **Idioma** (combobox Español/Inglés, reconstruye la UI al cambiar). Estructurada para sumar más secciones (voz, formatos, etc.) |
| Pestañas | `ttk.Notebook`: "Entrada y salida" (carpetas + lista) y "Síntesis y registro" (opciones + log) |
| Layout responsive | Bajo `UMBRAL_ANCHO` (900 px) usa pestañas; a partir de ahí muestra ambos paneles lado a lado en columnas (`_modo_columnas`/`_modo_pestanas`) |
| Carpeta de origen | Entry + "Examinar…", en tarjeta propia separada de la lista |
| Archivos Encontrados | Lista multiselección (Ctrl+clic), botones `Todo` / `Nada` / `Refrescar` y contador; vacío = todos |
| Salida de audio | Entry + "Examinar…" (arriba, en el tab "Entrada y salida") |
| Formatos | Checkboxes `WAV`/`FLAC`/`OGG`/`MP3`; `wav` y `mp3` marcados por defecto. Obliga a elegir al menos uno |
| Voz | Combobox readonly |
| Pasos | Slider 5–12 |
| Velocidad | Slider 0.7–2.0 |
| Acciones | `▶ Procesar` y `■ Cancelar` (deshabilitado mientras no procesa) |
| Progreso | `ttk.Progressbar` + porcentaje + etiqueta de estado |
| Feedback | Snackbar flotante estilo Material (`_mostrar_snackbar`) en lugar de diálogos modales |
| Log | `ScrolledText` con niveles coloreados; `logging` raíz en `INFO`. Registra: config al iniciar (voz/pasos/velocidad/formatos/salida), cada capítulo (`▶ N/M`), progreso de segmentos (máx. ~20 líneas por capítulo), fin por capítulo (`✔`), cancelación (`■`), errores con traceback y tiempo total |

Preferencias persistentes (contrato `RepositorioPreferencias` de `domain/repositories`, implementado como JSON en `data/repositories/repositorio_preferencias.py`):

- Se guardan al alternar tema, al cambiar idioma, al iniciar un procesamiento y al cerrar la ventana.
- Persisten: tema, idioma, voz, pasos, velocidad, formatos y carpetas de entrada/salida.
- Se inyectan desde `main.py` (`PreferenciasJSONLocal(CARPETA_BASE / "preferencias.json")`).
- Cambiar idioma reconstruye la UI (`_reconstruir_ui`) preservando valores, log, tema y modo responsive.

Arquitectura interna de la GUI (no se congela):

- El procesamiento corre en un `threading.Thread` daemon (`_trabajo`), leyendo los valores de las variables Tk en el momento de arrancar.
- `_LogHaciaCola(logging.Handler)` reenvía cada log a una `queue.Queue` con `("log", nivel, texto)`. Se agrega al logger raíz en el constructor.
- `_drenar_cola()` (scheduleado con `after(100, ...)`) consume la cola en el hilo de la UI y actualiza widgets.
- Mensajes de cola: `("log", nivel, texto)`, `("capitulo", i, n, nombre)`, `("progreso", actual, total)`, `("fin", exito, n)`, `("error", texto)`.
- **Cancelación**: `_cancelar = threading.Event()`; `debe_detenerse` del use case consulta `self._cancelar.is_set()` entre segmentos; al cancelar se exporta lo generado hasta ahora.

## `self_test.py` — Self-test

Verifica motor + síntesis real sin abrir ventana. Pensado para probar el ejecutable empaquetado.

```python
self_test(fabrica_motor, exportador, carpeta_base) -> int
main(fabrica_motor, exportador, carpeta_base)     # sys.exit(self_test(...))
```

Qué hace:

1. Crea el motor con `fabrica_motor(DEFAULT_VOICE)`.
2. Sintetiza `"Prueba de síntesis del motor Supertonic."` con `DEFAULT_TTS_STEPS`/`DEFAULT_SPEED`.
3. Si el audio salió vacío → `SELF-TEST FAIL`, retorna 1.
4. Escribe `audio/_self_test.wav` y reporta `SELF-TEST OK` con muestras y duración. Retorna 0.

Cualquier excepción → `SELF-TEST FAIL: <exc>` y retorna 1.
