# Capa de presentación (`app/presentation/`)

Interfaces de usuario. Consume SOLO el dominio (use cases, entidades, constantes) y recibe las dependencias YA inyectadas desde `main.py`. **Nunca importa `data/`.**

## `cli.py` — Interfaz de línea de comandos

Entrada: `main(fabrica_use_case: Callable[[str], ProcesarArchivo], repositorio: RepositorioArchivos)`.

Argumentos de argparse:

| Opción | Default | Descripción |
|--------|---------|-------------|
| `-a, --archivo ARCHIVO` | todos | Procesar solo un archivo (dentro de `archivos/`) |
| `-v, --voz VOZ` | `M1` | Voz (`M1`–`M5`, `F1`–`F5`) |
| `--steps` | `5` | Pasos de inferencia |
| `--speed` | `1.1` | Velocidad de habla |
| `-f, --formato FORMATOS` | `wav` | Formatos separados por coma (`wav, flac, ogg, mp3`) |
| `-V, --verbose` | — | Logging DEBUG |
| `-q, --quiet` | — | Solo warnings y errores |

Comportamiento:

1. Normaliza formatos con `normalizar_formatos` (un formato inválido → `parser.error`).
2. Asegura `archivos/` y `audio/` (`crear_carpetas_si_no_existen`).
3. Si `--archivo`: verifica que exista en `archivos/` y que la ruta resuelta quede DENTRO de `archivos/` (guard anti path-traversal: `Path.resolve().is_relative_to(carpeta_archivos)`; si no, exit 1). Si no: lista todos los `.md` (si no hay, avisa y termina).
4. Crea el use case con `fabrica_use_case(args.voz)`.
5. Procesa cada archivo con `ruta_base = audio/<stem>` y `on_progreso=_barra_progreso(...)`.

**`--cli` está oculto**: se registra con `argparse.SUPPRESS` para que `--help` muestre solo la GUI por defecto; los scripts y documentación interna lo usan para forzar el modo texto.

**tqdm es opcional**: si no está instalado, `_DummyTqdm` (iterable + `set_description`/`update`/`close`/`write` no-op) reemplaza la barra y todo funciona igual. Es UI, por eso vive acá y no en el dominio.

`_barra_progreso(nombre)` devuelve un callback `on_progreso(actual, total)` que ajusta `barra.total` la primera vez (el total se conoce recién tras segmentar) y actualiza `barra.n`.

## `gui.py` — Interfaz gráfica (Tkinter)

Entrada: `AppLector(*, fabrica_use_case, repositorio, carpeta_base, repositorio_preferencias)`. Es un `tk.Tk` con la ventana completa.

| Elemento | Detalle |
|----------|---------|
| `VOCES` | `("M1".."M5", "F1".."F5")` — 10 voces del modelo |
| Tema | Claro/oscuro con paleta Material Design 3 (`PALETA_CLARA`/`PALETA_OSCURA`) |
| Estilo | Material (actual), Neumorfismo o Skeuomorfismo (`_estilo`, valores en `ESTILOS`). El neumorfismo simula los biseles luz/sombra del soft UI con `relief` + `lightcolor`/`darkcolor` de clam (`_configurar_estilo_neumo`, superficie = fondo); el skeuomorfismo imita botones 3D con biseles y bordes marcados, entradas hundidas y acento azul acero (`_configurar_estilo_skeuo`, superficie distinta del fondo). Ambos se combinan con claro/oscuro (`NEUMO_*`/`SKEUO_*` sobre las paletas base) y se persisten en la clave `estilo` |
| Idioma | Español/Inglés (`IDIOMAS`/`TRADUCCIONES`); `self.t(clave)` traduce todos los textos. Se cambia desde Ajustes y se persiste |
| Cabecera | Título + botón de ajustes (`⚙`) que abre la ventana flotante de configuración (`_abrir_ajustes`) |
| Ventana de ajustes | `tk.Toplevel` transiente centrada sobre la principal; muestra la configuración del programa. Secciones: **Tema** (Claro/Oscuro, aplica y guarda al instante), **Estilo** (Material/Neumorfismo/Skeuomorfismo, aplica y guarda al instante), **Idioma** (combobox Español/Inglés, reconstruye la UI al cambiar) y **Acerca de** (nombre, versión `APP_VERSION`, descripción, licencia y enlace `Enlace.TButton` que abre `REPOSITORIO_URL` en el navegador vía `webbrowser`). Estructurada para sumar más secciones (voz, formatos, etc.) |
| Pestañas | `ttk.Notebook`: "Entrada y salida" (carpetas + lista) y "Síntesis y registro" (opciones + log) |
| Layout responsive | Bajo `UMBRAL_ANCHO` (900 px) usa pestañas; a partir de ahí muestra ambos paneles lado a lado en columnas (`_modo_columnas`/`_modo_pestanas`) |
| Carpeta de origen | Entry + "Examinar…", en tarjeta propia separada de la lista |
| Archivos Encontrados | Lista multiselección (Ctrl+clic), botones `Todo` / `Nada` / `Refrescar` y contador; vacío = todos |
| Salida de audio | Entry + "Examinar…" (arriba, en el tab "Entrada y salida") |
| Formatos | Checkboxes `WAV`/`FLAC`/`OGG`/`MP3`; `wav` y `mp3` marcados por defecto. Obliga a elegir al menos uno |
| Voz | Combobox readonly |
| Escuchar | Botón `▶` que sintetiza y reproduce una muestra corta con la voz e idioma seleccionados (hilo aparte; se deshabilita mientras genera). Texto de ejemplo por idioma (`TEXTO_MUESTRA_IDIOMAS`); los idiomas sin entrada usan el texto traducido de la interfaz. Reproduce con `winsound` (WAV PCM, sin dependencias). Requiere `fabrica_muestra` inyectada desde `main.py` |
| Pasos | Slider 5–12 |
| Velocidad | Slider 0.7–2.0 |
| Idioma de la voz | Combobox readonly con los 32 idiomas de `LANGUAGES_VOZ` (`IDIOMAS_VOZ_NATIVOS` muestra el nombre nativo; `na` aparece como "Auto (sin idioma)"). Se persiste en la clave `lang_voz` |
| Acciones | `▶ Procesar` y `■ Cancelar` (deshabilitado mientras no procesa) |
| Progreso | `ttk.Progressbar` + porcentaje + etiqueta de estado |
| Feedback | Snackbar flotante estilo Material (`_mostrar_snackbar`) en lugar de diálogos modales |
| Log | `ScrolledText` con niveles coloreados; `logging` raíz en `INFO`. Registra: config al iniciar (voz/pasos/velocidad/idioma de la voz/formatos/salida), cada archivo (`▶ N/M`), progreso de segmentos (máx. ~20 líneas por archivo), fin por archivo (`✔`), cancelación (`■`), errores con traceback y tiempo total |
| Rueda del mouse | Scroll direccional (horizontal en la lista de archivos, vertical en el log) mediante `<MouseWheel>`/`<Shift-MouseWheel>` en los toplevel; con `try/except TclError` para que una plataforma sin `wm_attributes` no rompa la reconstrucción de la UI |
| Cambio de idioma | `_reconstruir_ui` resetea también los checks de formatos a los valores actuales (`_vars_check`/`_checks`) y conserva log, tema y modo responsive; el cambio es seguro aun con la ventana de ajustes abierta |

Preferencias persistentes (contrato `RepositorioPreferencias` de `domain/repositories`, implementado como JSON en `data/repositories/repositorio_preferencias.py`):

- Se guardan al alternar tema o estilo, al cambiar idioma, al iniciar un procesamiento y al cerrar la ventana.
- Persisten: tema, estilo, idioma, voz, pasos, velocidad, idioma de la voz, formatos y carpetas de entrada/salida.
- Se inyectan desde `main.py` (`PreferenciasJSONLocal(CARPETA_BASE / "preferencias.json")`).
- Cambiar idioma reconstruye la UI (`_reconstruir_ui`) preservando valores, log, tema y modo responsive.

Arquitectura interna de la GUI (no se congela):

- El procesamiento corre en un `threading.Thread` daemon (`_trabajo`), leyendo los valores de las variables Tk en el momento de arrancar.
- `_LogHaciaCola(logging.Handler)` reenvía cada log a una `queue.Queue` con `("log", nivel, texto)`. Se agrega al logger raíz en el constructor.
- `_drenar_cola()` (scheduleado con `after(100, ...)`) consume la cola en el hilo de la UI y actualiza widgets.
- Mensajes de cola: `("log", nivel, texto)`, `("archivo", i, n, nombre)`, `("progreso", actual, total)`, `("fin", exito, n)`, `("error", texto)`.
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
