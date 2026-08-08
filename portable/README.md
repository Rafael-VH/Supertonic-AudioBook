# Supertonic-AudioBook — Instalador portable

Un único `.exe` que, al ejecutarse en cualquier PC con Windows, extrae la aplicación completa (ejecutable + dependencias + modelo TTS) en una carpeta junto a sí mismo y la lanza. No requiere instalar Python ni nada más: todo viaja empaquetado dentro del instalador.

Hay **dos variantes** del instalador:

| Instalador | Tamaño aprox. | Modelo TTS |
|---|---|---|
| `SupertonicAudioBook-Portable.exe` | ~417 MB | **Incluido** (funciona sin conexión) |
| `SupertonicAudioBook-Portable-Lite.exe` | ~60 MB | No incluido; se **descarga solo al primer uso** (requiere conexión a internet) |

Ambas se generan con un solo comando. Los detalles de la variante Lite están en la sección [Instalador Lite (sin modelo)](#instalador-lite-sin-modelo).

## Qué es

`instalador_portable.py` es un instalador de un solo archivo. Se compila con PyInstaller en modo one-file y, al ejecutarlo, deja una instalación portable de **Supertonic-AudioBook** en la carpeta del propio instalador, lista para usarse desde ahí.

El resultado es `SupertonicAudioBook-Portable.exe`, un instalador sin consola (`console=False`) pensado para el usuario final.

## Cómo funciona

1. La aplicación compilada se embebe en el build con `--add-data` de PyInstaller (en el `.spec` se declara en `datas`).
2. Al ejecutar el instalador, PyInstaller extrae el payload a un directorio temporal accesible como `sys._MEIPASS`.
3. El script toma la carpeta `SupertonicAudioBook` de ese directorio de extracción (`_carpeta_origen`).
4. La copia a `carpeta_del_instalador\SupertonicAudioBook` (`_carpeta_destino`), mostrando una ventana con barra de progreso y contador de MB.
5. Recrea explícitamente las carpetas `archivos` y `audio`, porque PyInstaller descarta las carpetas vacías del payload y la app espera que existan.
6. Lanza `SupertonicAudioBook.exe` desde su carpeta de destino y termina.

Si se ejecuta el script como Python normal (`python instalador_portable.py`), no existe `_MEIPASS` y se toma como origen la carpeta `SupertonicAudioBook` junto al propio script.

## Requisitos

### Para construir el instalador

- Windows y Python 3 con PyInstaller instalado (`pip install pyinstaller`).
- La aplicación **Supertonic-AudioBook ya compilada** en la ruta declarada en el `.spec`: `C:\Users\rafae\Music\Supertonic\new\dist\SupertonicAudioBook`. Esa carpeta debe contener `SupertonicAudioBook.exe`, sus dependencias y el modelo TTS. Si la app se compila en otra ruta, ajustá `datas` en `SupertonicAudioBook-Portable.spec`.

### Para el usuario final

- Cualquier PC con Windows. No necesita Python ni ninguna dependencia adicional.

## Cómo construir el instalador

El script `build_portables.py` prepara el staging sin modelo y genera **ambos** instaladores. No compila la aplicación: esa es responsabilidad de `new/` (ver `new/README.md`); este script solo lee la app ya compilada.

```bash
python build_portables.py
```

Requisitos previos:

- Windows y Python 3 con PyInstaller instalado (`pip install pyinstaller`).
- La aplicación compilada en `new/dist/SupertonicAudioBook` (desde `new/` con `new\SupertonicAudioBook.spec`).
- Para la variante completa, el modelo TTS en `new/dist/SupertonicAudioBook\modelo`. Podés descargarlo corriendo la app una vez (`SupertonicAudioBook.exe --self-test`) o copiándolo al dist. Para la variante Lite no hace falta.

Qué hace cada paso:

1. **Verifica** que la app esté compilada en `new/dist/SupertonicAudioBook`. Si no, te avisa y te manda a `new/`; no compila nada por su cuenta.
2. **Prepara el staging Lite**: copia `new/dist/SupertonicAudioBook` a `portable/staging_lite/SupertonicAudioBook` **sin** la carpeta `modelo`.
3. **Compila el instalador completo** (`SupertonicAudioBook-Portable.spec`): empaqueta el dist completo, modelo incluido.
4. **Compila el instalador Lite** (`SupertonicAudioBook-Portable-Lite.spec`): empaqueta el staging sin modelo. El `.spec` lee la ruta desde la variable `SUPERTONIC_APP_DIST`, que el script define automáticamente.

Los dos instaladores quedan en `dist\`:

```text
dist\SupertonicAudioBook-Portable.exe
dist\SupertonicAudioBook-Portable-Lite.exe
```

### Variantes de construcción

| Comando | Qué hace |
|---|---|
| `python build_portables.py` | Genera los dos instaladores (exige el modelo) |
| `python build_portables.py --solo-lite` | Solo el instalador Lite (no exige el modelo) |
| `pyinstaller SupertonicAudioBook-Portable.spec` | Solo el instalador completo (el dist debe existir) |
| `pyinstaller SupertonicAudioBook-Portable-Lite.spec` | Solo el instalador Lite (el staging debe existir) |

## Instalador Lite (sin modelo)

`SupertonicAudioBook-Portable-Lite.exe` trae la misma aplicación pero **sin el modelo TTS**. El modelo pesa ~385 MB, por eso este instalador es mucho más chico (~60 MB).

### Primer uso

- Al abrir la app por primera vez, **necesita conexión a internet**.
- La app descarga el modelo automáticamente a la carpeta `SupertonicAudioBook\modelo` (junto al exe). Lo hace gracias a `TTS(auto_download=True)` y a que la app fija `SUPERTONIC_CACHE_DIR` en esa carpeta.
- La descarga ocurre una sola vez: después, el modelo queda guardado y la app funciona sin conexión, igual que en la variante completa.

### Consideraciones

- Si la PC del usuario no tiene internet, conviene usar la variante completa.
- El modelo descargado y el incluido en el instalador completo son el mismo; no se descarga dos veces si ya existe en `modelo`.

## Uso (usuario final)

1. Copiá `SupertonicAudioBook-Portable.exe` a la carpeta donde querés dejar la instalación portable.
2. Ejecutalo con doble clic.
    - **Primera ejecución**: se abre la ventana "Supertonic-AudioBook — Instalador" con una barra de progreso. Copia la aplicación completa a la subcarpeta `SupertonicAudioBook` (junto al instalador) y al terminar lanza la app.
   - **Ejecuciones siguientes**: si la instalación ya existe y está actualizada, lanza la app directamente, sin mostrar ventana.
3. La app queda instalada de forma permanente en esa carpeta: se puede ejecutar desde ahí sin volver a correr el instalador.

## Notas de comportamiento

- **Comprobación de actualización**: el instalador compara únicamente el tamaño de `SupertonicAudioBook.exe` entre el payload empaquetado y el archivo ya instalado. Si el tamaño coincide, se asume que la instalación está al día y se omite la copia.
- **Lanzamiento**: la app se inicia con `cwd` apuntando a su propia carpeta de destino, y el instalador termina sin esperarla.
- **Errores**: si la copia falla, se muestra un cuadro "Error al instalar" y el proceso sale con código 1.
- **Carpetas de datos**: `archivos` y `audio` se recrean vacías si no vienen en el payload (PyInstaller descarta directorios vacíos). No se borran instalaciones previas antes de copiar.
