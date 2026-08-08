"""
instalador_portable.py — Instalador portable de Supertonic-AudioBook.

Un único .exe que, al ejecutarse en cualquier PC con Windows, extrae la
aplicación completa (ejecutable + dependencias + modelo TTS) en una
carpeta junto a sí mismo y la lanza. No requiere instalar Python ni
nada más: todo viaja empaquetado dentro del instalador.

La aplicación se embebe en el build con --add-data (PyInstaller), así
que este script solo copia la carpeta ``SupertonicAudioBook`` desde el
directorio de extracción (_MEIPASS) hacia el lado del instalador.
"""

import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk


def _carpeta_origen() -> Path:
    """Carpeta de la app extraída por PyInstaller en memoria/temp."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "SupertonicAudioBook"


def _carpeta_destino() -> Path:
    """Coloca la app junto al instalador (portable: todo queda junto)."""
    return Path(sys.executable).resolve().parent / "SupertonicAudioBook"


def _instalado_actualizado(origen: Path, destino: Path) -> bool:
    """True si ya existe la app y el ejecutable coincide con el empaquetado."""
    src = origen / "SupertonicAudioBook.exe"
    dst = destino / "SupertonicAudioBook.exe"
    return src.exists() and dst.exists() and src.stat().st_size == dst.stat().st_size


def _copiar_con_progreso(
    origen: Path, destino: Path, root: tk.Tk, barra: ttk.Progressbar, lbl: ttk.Label
) -> None:
    """Copia la carpeta completa mostrando progreso en la ventana."""
    total = 0
    for carpeta, _, archivos in os.walk(origen):
        for nombre in archivos:
            total += (Path(carpeta) / nombre).stat().st_size

    copiado = 0
    for carpeta, _, archivos in os.walk(origen):
        destino_dir = destino / Path(carpeta).relative_to(origen)
        destino_dir.mkdir(parents=True, exist_ok=True)
        for nombre in archivos:
            origen_archivo = Path(carpeta) / nombre
            shutil.copy2(origen_archivo, destino_dir / nombre)
            copiado += origen_archivo.stat().st_size
            barra["value"] = copiado / total * 100
            lbl.config(
                text=f"{copiado // (1024 * 1024)} MB de {total // (1024 * 1024)} MB"
            )
            root.update()


def _lanzar(exe: Path) -> None:
    subprocess.Popen([str(exe)], cwd=str(exe.parent))


def main() -> None:
    origen = _carpeta_origen()
    destino = _carpeta_destino()
    app_exe = destino / "SupertonicAudioBook.exe"

    if _instalado_actualizado(origen, destino):
        _lanzar(app_exe)
        return

    root = tk.Tk()
    root.title("Supertonic-AudioBook — Instalador")
    root.geometry("440x120")
    root.resizable(False, False)
    ttk.Label(root, text="Instalando Supertonic-AudioBook...").pack(pady=(14, 4))
    barra = ttk.Progressbar(root, maximum=100)
    barra.pack(fill="x", padx=20, pady=6)
    lbl = ttk.Label(root, text="Preparando...")
    lbl.pack()
    root.update()

    try:
        _copiar_con_progreso(origen, destino, root, barra, lbl)
        # PyInstaller descarta las carpetas vacías del payload: se recrean
        # explícitamente las que la app espera tener.
        for nombre in ("archivos", "audio"):
            (destino / nombre).mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        root.destroy()
        from tkinter import messagebox

        messagebox.showerror("Error al instalar", f"No se pudo instalar:\n{exc}")
        sys.exit(1)

    root.destroy()
    _lanzar(app_exe)


if __name__ == "__main__":
    main()
