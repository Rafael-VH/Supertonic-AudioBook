"""
build_portables.py — Genera los dos instaladores portables de Supertonic-AudioBook.

Este script trabaja SOLO dentro de packaging/: prepara el staging sin modelo y
compila los instaladores. NO compila la app (eso vive en app/ y es
responsabilidad de app/SupertonicAudioBook.spec); solo la lee desde
app/dist/SupertonicAudioBook.

1. Verifica que la app ya esté compilada en app/dist/SupertonicAudioBook.
2. Prepara un staging del dist SIN la carpeta modelo/ (para la variante Lite).
3. Compila el instalador completo  (SupertonicAudioBook-Portable.exe, ~417 MB).
4. Compila el instalador Lite       (SupertonicAudioBook-Portable-Lite.exe, ~40 MB).

El instalador Lite no incluye el modelo TTS: la app lo descarga sola al primer
uso (TTS(auto_download=True) + SUPERTONIC_CACHE_DIR=modelo/ junto al exe).

Uso:
    python build_portables.py            # pasos 2-4
    python build_portables.py --solo-lite # solo el instalador Lite
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
APP_DIST = RAIZ / "app" / "dist" / "SupertonicAudioBook"
APP_EXE = APP_DIST / "SupertonicAudioBook.exe"
STAGING_LITE = RAIZ / "packaging" / "staging_lite" / "SupertonicAudioBook"

# Fuente de verdad del modelo TTS. El rebuild de la app (pyinstaller
# --noconfirm) borra app/dist; el modelo NO se guarda ahí, se copia desde
# resource/modelo al compilar el instalador completo.
RESOURCE_MODELO = RAIZ / "resource" / "modelo"
MODELO = APP_DIST / "modelo"


def _ejecutar(args, cwd):
    print(f"[build] >> {args}")
    subprocess.run(args, cwd=cwd, check=True)


def verificar_app() -> None:
    if not APP_EXE.exists():
        raise SystemExit(
            f"No está compilada la app: {APP_EXE}\n"
            "Compilala primero desde app/ (ver app/README.md):\n"
            "  pyinstaller app/SupertonicAudioBook.spec\n"
            "Este script solo genera los instaladores, no compila la app."
        )
    print(f"[build] App compilada: {APP_EXE}")


def preparar_staging_lite() -> None:
    if STAGING_LITE.exists():
        shutil.rmtree(STAGING_LITE)
    print("[build] Preparando staging sin modelo/ para la variante Lite...")

    def _excluir_modelo(directorio, nombres):
        if Path(directorio) == APP_DIST:
            return {"modelo"}
        return set()

    shutil.copytree(APP_DIST, STAGING_LITE, ignore=_excluir_modelo)
    print(f"[build] Staging listo: {STAGING_LITE}")


def sincronizar_modelo() -> None:
    """Copia el modelo desde resource/modelo hacia app/dist, si falta.

    La fuente de verdad es ``resource/modelo`` (raíz del proyecto). El rebuild
    de la app con ``pyinstaller --noconfirm`` borra ``app/dist`` y con él el
    modelo; por eso el instalador completo se compila SIEMPRE desde resource.
    """
    if MODELO.is_dir():
        return
    if not RESOURCE_MODELO.is_dir():
        raise SystemExit(
            f"Falta el modelo TTS en {RESOURCE_MODELO}.\n"
            "El instalador COMPLETO lo necesita. Corré la app una vez para que "
            "lo descargue a resource/modelo, o usá --solo-lite."
        )
    print(f"[build] Copiando modelo desde {RESOURCE_MODELO}...")
    shutil.copytree(RESOURCE_MODELO, MODELO)
    print(f"[build] Modelo listo: {MODELO}")


def compilar_instalador_completo() -> None:
    sincronizar_modelo()
    print("[build] Compilando instalador COMPLETO (con modelo)...")
    _ejecutar(
        [sys.executable, "-m", "PyInstaller", "SupertonicAudioBook-Portable.spec", "--noconfirm"],
        RAIZ / "packaging",
    )


def compilar_instalador_lite() -> None:
    print("[build] Compilando instalador LITE (sin modelo)...")
    env = dict(os.environ, SUPERTONIC_APP_DIST=str(STAGING_LITE))
    _ejecutar(
        [sys.executable, "-m", "PyInstaller", "SupertonicAudioBook-Portable-Lite.spec", "--noconfirm"],
        RAIZ / "packaging",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera los instaladores portables.")
    parser.add_argument(
        "--solo-lite",
        action="store_true",
        help="genera solo el instalador Lite (no exige el modelo)",
    )
    args = parser.parse_args()

    verificar_app()
    preparar_staging_lite()
    if args.solo_lite:
        compilar_instalador_lite()
    else:
        compilar_instalador_completo()
        compilar_instalador_lite()

    print("\n[build] Listo. Instaladores generados:")
    if args.solo_lite:
        print(f"  {RAIZ / 'packaging' / 'dist' / 'SupertonicAudioBook-Portable-Lite.exe'}")
    else:
        print(f"  {RAIZ / 'packaging' / 'dist' / 'SupertonicAudioBook-Portable.exe'}")
        print(f"  {RAIZ / 'packaging' / 'dist' / 'SupertonicAudioBook-Portable-Lite.exe'}")


if __name__ == "__main__":
    main()
