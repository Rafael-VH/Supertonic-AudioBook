# Empaquetado (`app/SupertonicAudioBook.spec` + `packaging/`)

Cómo se distribuye la app: un `.exe` one-folder para el desarrollo y dos instaladores portables para el usuario final. Todo el empaquetado usa PyInstaller.

## Resumen de artefactos

| Artefacto | Qué es | Tamaño aprox. | Modelo TTS |
|-----------|--------|---------------|------------|
| `app/dist/SupertonicAudioBook/SupertonicAudioBook.exe` | Build one-folder (ventana, sin consola) | — | no incluido (se descarga o se copia `modelo/`) |
| `packaging/dist/SupertonicAudioBook-Portable.exe` | Instalador portable completo | ~417 MB | **incluido** (offline) |
| `packaging/dist/SupertonicAudioBook-Portable-Lite.exe` | Instalador portable Lite | ~60 MB | no incluido; se descarga al primer uso |

## App one-folder — `app/SupertonicAudioBook.spec`

Build de la app en `dist/SupertonicAudioBook/SupertonicAudioBook.exe`:

```bash
pyinstaller app/SupertonicAudioBook.spec
```

El spec:

- `Analysis([os.path.join(SPECPATH, 'main.py')], pathex=[SPECPATH], ...)` — usa `SPECPATH` para no depender del CWD desde donde corras PyInstaller. `main.py` importa `from data...`, `from domain...`, así que `app/` debe estar en el path de búsqueda.
- `collect_all('huggingface_hub')` — empaqueta los datos/binarios del hub (el modelo se descarga en runtime).
- `console=False`, nombre `SupertonicAudioBook`, one-folder (`COLLECT`).

Para distribuir offline: copiá la carpeta `modelo/` junto al `.exe` (la app fija `SUPERTONIC_CACHE_DIR=modelo/`). Verificá con `SupertonicAudioBook.exe --self-test`.

## Instaladores portables — `packaging/`

### Cómo funciona un instalador

`instalador_portable.py` es el script que se compila como **one-file**. Al ejecutarse:

1. PyInstaller extrae el payload a `sys._MEIPASS`.
2. Toma la carpeta `SupertonicAudioBook` de ahí (`_carpeta_origen`).
3. La copia a `carpeta_del_instalador/SupertonicAudioBook` (`_carpeta_destino`) con ventana + barra de progreso.
4. Recrea `archivos/` y `audio/` (PyInstaller descarta carpetas vacías).
5. Lanza `SupertonicAudioBook.exe` y termina.

Si ya está instalada y el exe coincide (mismo tamaño), se omite la copia y se lanza directo.

### Construcción — `build_portables.py`

```bash
python packaging/build_portables.py              # los dos instaladores (exige modelo)
python packaging/build_portables.py --solo-lite  # solo el Lite (no exige modelo)
```

El script NO compila la app: lee la ya compilada en `app/dist/SupertonicAudioBook`. Rutas que define:

| Variable | Ruta |
|----------|------|
| `APP_DIST` | `<raiz>/app/dist/SupertonicAudioBook` |
| `APP_EXE` | `APP_DIST/SupertonicAudioBook.exe` |
| `STAGING_LITE` | `<raiz>/packaging/staging_lite/SupertonicAudioBook` |
| `MODELO` | `APP_DIST/modelo` |

Pasos: verifica la app → copia `APP_DIST` a `STAGING_LITE` **sin** `modelo/` (variante Lite) → compila el instalador completo → compila el Lite.

### Specs portables

- `packaging/SupertonicAudioBook-Portable.spec` — payload completo: `datas=[('C:\Users\rafae\Music\Supertonic\app\dist\SupertonicAudioBook', 'SupertonicAudioBook')]`. Ruta hardcodeada; si cambiás de ruta, ajustá `datas`.
- `packaging/SupertonicAudioBook-Portable-Lite.spec` — payload desde `SUPERTONIC_APP_DIST` (variable que define `build_portables.py` apuntando a `STAGING_LITE`). Si no está definida, fallback a la ruta del staging_lite.

### Variante Lite (sin modelo)

- Al primer uso la app necesita internet: `TTS(auto_download=True)` + `SUPERTONIC_CACHE_DIR=modelo/` junto al exe descargan el modelo automáticamente.
- La descarga ocurre UNA vez; después funciona offline igual que la completa.
- El modelo descargado y el empaquetado son el mismo; no se duplica si ya existe.

## Flujo de build completo (para release)

```
1. pyinstaller app/SupertonicAudioBook.spec        → app/dist/SupertonicAudioBook/
2. python app/main.py --self-test  (opcional, verifica el motor)
3. copiar modelo/ a app/dist/SupertonicAudioBook/  (si se quiere offline)
4. python packaging/build_portables.py             → packaging/dist/*.exe
```

## Gotchas de empaquetado

- `app/dist/`, `packaging/dist/` y `packaging/staging_lite/` están en `.gitignore`.
- El instalador compara SOLO el tamaño del exe para decidir si hay que reinstalar.
- `console=False` en los 3 specs: no aparece ventana de terminal al ejecutar.
