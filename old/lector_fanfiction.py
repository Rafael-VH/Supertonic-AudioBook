import os
import re
import numpy as np
import soundfile as sf
from supertonic import TTS

def crear_carpetas_si_no_existen():
    for carpeta in ["fanfic", "audio"]:
        if not os.path.exists(carpeta):
            os.makedirs(carpeta)
            print(f"[+] Carpeta creada: {carpeta}/")

def listar_archivos_md(carpeta="fanfic"):
    archivos = [f for f in os.listdir(carpeta) if f.lower().endswith(".md")]
    if not archivos:
        print("[!] No se encontraron archivos .md en la carpeta 'fanfic/'.")
        print("    Coloca tus capitulos alli (formato Markdown).")
        return []
    print(f"[*] Detectados {len(archivos)} capitulo(s): {', '.join(archivos)}")
    return sorted(archivos)

def limpiar_markdown(texto):
    texto = re.sub(r"^#{1,6}\s*", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", texto)
    texto = re.sub(r"_{1,3}(.*?)_{1,3}", r"\1", texto)
    texto = re.sub(r"`{1,3}(.*?)`{1,3}", r"\1", texto)
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)
    texto = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", texto)
    texto = re.sub(r">\s?", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"[-*+]\s", "", texto)
    texto = re.sub(r"---|\*\*\*", "", texto)
    texto = re.sub(r"~~~.*?~~~", "", texto, flags=re.DOTALL)
    texto = re.sub(r"```.*?```", "", texto, flags=re.DOTALL)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()

def limpiar_y_segmentar_texto(ruta_archivo):
    if not os.path.exists(ruta_archivo):
        raise FileNotFoundError(f"No se encontro el archivo: {ruta_archivo}")

    with open(ruta_archivo, "r", encoding="utf-8") as f:
        contenido = f.read()

    contenido = limpiar_markdown(contenido)

    lineas = [p.strip() for p in contenido.split("\n") if p.strip()]

    LIMITE = 1500
    UMBRAL_FUSION = 200

    fusionados = []
    buffer = ""
    for p in lineas:
        if not buffer:
            buffer = p
        elif len(buffer) + len(p) < LIMITE and len(p) < UMBRAL_FUSION:
            buffer += " " + p
        else:
            fusionados.append(buffer)
            buffer = p
    if buffer:
        fusionados.append(buffer)

    parrafos_finales = []
    for p in fusionados:
        if len(p) > LIMITE:
            subfrases = p.split(". ")
            buffer_frase = ""
            for frase in subfrases:
                if len(buffer_frase) + len(frase) <= LIMITE:
                    buffer_frase += frase + ". "
                else:
                    parrafos_finales.append(buffer_frase.strip())
                    buffer_frase = frase + ". "
            if buffer_frase:
                parrafos_finales.append(buffer_frase.strip())
        else:
            parrafos_finales.append(p)

    return parrafos_finales

_TTS_ENGINE = None

def cargar_tts(voz="M1"):
    global _TTS_ENGINE
    if _TTS_ENGINE is None:
        print("[1/4] Inicializando motor Supertonic...")
        _TTS_ENGINE = TTS(auto_download=True)
    style = _TTS_ENGINE.get_voice_style(voice_name=voz)
    return _TTS_ENGINE, style

def procesar_capitulo(nombre_archivo, voz="M1"):
    ruta_entrada = os.path.join("fanfic", nombre_archivo)
    nombre_base = os.path.splitext(nombre_archivo)[0]
    ruta_salida = os.path.join("audio", nombre_base + ".wav")

    print(f"\n{'='*50}")
    print(f"  Procesando: {nombre_archivo}")
    print(f"{'='*50}")

    tts, style = cargar_tts(voz)

    print("[2/4] Leyendo y fragmentando manuscrito...")
    parrafos = limpiar_y_segmentar_texto(ruta_entrada)
    total = len(parrafos)
    print(f"  -> {total} parrafo(s) para procesar.")

    print("[3/4] Generando voz sintetica...")
    todos_los_audios = []
    SILENCIO = int(44100 * 0.6)

    for i, parrafo in enumerate(parrafos, 1):
        print(f"  - Fragmento {i}/{total} [{len(parrafo)} caracteres]...")
        wav, _ = tts.synthesize(parrafo, voice_style=style, lang="es", total_steps=5, speed=1.1)
        if wav.size > 0:
            todos_los_audios.append(wav.squeeze())
            todos_los_audios.append(np.zeros(SILENCIO, dtype=np.float32))

    if not todos_los_audios:
        print("  [!] No se genero audio.")
        return

    print("[4/4] Exportando audio final...")
    audio_final = np.concatenate(todos_los_audios)
    sf.write(ruta_salida, audio_final, 44100)
    print(f"  + Guardado en: {os.path.abspath(ruta_salida)}")
    duracion = len(audio_final) / 44100
    print(f"  Duracion: {duracion:.1f}s")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    crear_carpetas_si_no_existen()
    archivos = listar_archivos_md()

    if not archivos:
        print("\nCrea un archivo .md dentro de la carpeta 'fanfic/' y ejecuta de nuevo.")
    else:
        for archivo in archivos:
            procesar_capitulo(archivo, voz="M1")
        print("Todos los capitulos procesados.")
