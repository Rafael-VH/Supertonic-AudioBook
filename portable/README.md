# Supertonic-AudioBook — Instalador portable

Un único `.exe` que, al ejecutarse en cualquier PC con Windows, extrae la aplicación completa (ejecutable + dependencias + modelo TTS) en una carpeta junto a sí mismo y la lanza. No requiere instalar Python ni nada más: todo viaja empaquetado dentro del instalador.

## Qué es

`instalador_portable.py` es un instalador de un solo archivo. Se compila con PyInstaller en modo one-file y, al ejecutarlo, deja una instalación portable de **Supertonic-AudioBook** en la carpeta del propio instalador, lista para usarse desde ahí.

El resultado es `SupertonicReader-Portable.exe`, un instalador sin consola (`console=False`) pensado para el usuario final.

## Cómo funciona

1. La aplicación compilada se embebe en el build con `--add-data` de PyInstaller (en el `.spec` se declara en `datas`).
2. Al ejecutar el instalador, PyInstaller extrae el payload a un directorio temporal accesible como `sys._MEIPASS`.
3. El script toma la carpeta `SupertonicReader` de ese directorio de extracción (`_carpeta_origen`).
4. La copia a `carpeta_del_instalador\SupertonicReader` (`_carpeta_destino`), mostrando una ventana con barra de progreso y contador de MB.
5. Recrea explícitamente las carpetas `archivos` y `audio`, porque PyInstaller descarta las carpetas vacías del payload y la app espera que existan.
6. Lanza `SupertonicReader.exe` desde su carpeta de destino y termina.

Si se ejecuta el script como Python normal (`python instalador_portable.py`), no existe `_MEIPASS` y se toma como origen la carpeta `SupertonicReader` junto al propio script.

## Requisitos

### Para construir el instalador

- Windows y Python 3 con PyInstaller instalado (`pip install pyinstaller`).
- La aplicación **Supertonic-AudioBook ya compilada** en la ruta declarada en el `.spec`: `C:\Users\rafae\Music\Supertonic\new\dist\SupertonicReader`. Esa carpeta debe contener `SupertonicReader.exe`, sus dependencias y el modelo TTS. Si la app se compila en otra ruta, ajustá `datas` en `SupertonicReader-Portable.spec`.

### Para el usuario final

- Cualquier PC con Windows. No necesita Python ni ninguna dependencia adicional.

## Cómo construir el instalador

1. Verificá que la carpeta de la app compilada exista en la ruta que apunta el `.spec`.
2. Ejecutá PyInstaller con el `.spec`:

```bash
pyinstaller SupertonicReader-Portable.spec
```

3. El instalador queda en `dist\SupertonicReader-Portable.exe`.

## Uso (usuario final)

1. Copiá `SupertonicReader-Portable.exe` a la carpeta donde querés dejar la instalación portable.
2. Ejecutalo con doble clic.
    - **Primera ejecución**: se abre la ventana "Supertonic-AudioBook — Instalador" con una barra de progreso. Copia la aplicación completa a la subcarpeta `SupertonicReader` (junto al instalador) y al terminar lanza la app.
   - **Ejecuciones siguientes**: si la instalación ya existe y está actualizada, lanza la app directamente, sin mostrar ventana.
3. La app queda instalada de forma permanente en esa carpeta: se puede ejecutar desde ahí sin volver a correr el instalador.

## Notas de comportamiento

- **Comprobación de actualización**: el instalador compara únicamente el tamaño de `SupertonicReader.exe` entre el payload empaquetado y el archivo ya instalado. Si el tamaño coincide, se asume que la instalación está al día y se omite la copia.
- **Lanzamiento**: la app se inicia con `cwd` apuntando a su propia carpeta de destino, y el instalador termina sin esperarla.
- **Errores**: si la copia falla, se muestra un cuadro "Error al instalar" y el proceso sale con código 1.
- **Carpetas de datos**: `archivos` y `audio` se recrean vacías si no vienen en el payload (PyInstaller descarta directorios vacíos). No se borran instalaciones previas antes de copiar.
