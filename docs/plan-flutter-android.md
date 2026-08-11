# Plan de Handoff — Portar Supertonic-AudioBook a Flutter multiplataforma

> **Documento de HANDOFF AUTOCONTENIDO.** Está diseñado para construir la app
> **Flutter multiplataforma (Android, iOS, Windows, Linux)** **sin acceso al
> proyecto Python original**. Toda la
> especificación de comportamiento, constantes y reglas vive acá, verificada
> contra el código real el **2026-08-10**. No infieras valores ni reglas que no
> estén en este documento; si algo falta, preguntá en lugar de inventar.
>
> **Flujo de uso**: 1) creá el proyecto Flutter nuevo (Fase 0/1), 2) pegá este
> documento en la raíz (ej: `HANDOFF.md`), 3) iniciá una conversación nueva de
> Opencode en el proyecto nuevo y pedile que siga este plan de punta a punta.

---

## Índice

0. Cómo usar este documento (meta-instrucciones)
1. Quick path — primeros 30 minutos
2. Alcance y descartes (paridad)
3. Arquitectura objetivo (Clean Architecture)
4. Especificación de dominio (reglas de negocio puras)
5. Especificación de datos (audio, archivos, modelo)
6. Especificación de presentación (UI, ajustes, i18n, Acerca de)
7. Tests a portar (lista literal)
8. Fases paso a paso (0–6)
9. Riesgos y mitigaciones
10. Fuentes (verificadas 2026-08-10)

---

## 0. Cómo usar este documento

**Lee este documento COMPLETO antes de escribir una sola línea de código.**

- Paridad **1:1 con el desktop** salvo motivo técnico documentado. No "mejores"
  constantes ni regex por tu cuenta: si algo del código original es así, se porta
  así (los bugs conocidos se listan en §4 como *comportamiento verificado*).
- **Regla de dependencia** (no negociable, ver §3): `lib/domain/` es Dart puro
  (sin Flutter ni plugins); `lib/data/` es el ÚNICO lugar con paquetes externos;
  `lib/presentation/` solo depende de `domain/`; `main.dart` es el único
  composition root que importa `data/`.
- **Idioma**: código, docstrings y docs en español. UI bilingüe ES/EN vía `.arb`.
- **Commits**: conventional commits, sin atribución de IA ("Co-Authored-By").
- **Gate de calidad** previo a buildar para cualquier plataforma (Fase 6):
  `flutter
  analyze` sin errores + `flutter test` + judgment-day (2 jueces ciegos →
  arreglar solo hallazgos confirmados → re-juzgar). No se compila sin ese gate.
- No comprometas secretos ni API keys.

### Contrato del agente (reglas de ejecución)

Este documento es una **especificación, no una sugerencia**. El agente que lo
ejecute acepta estas reglas:

1. **Leer TODO antes de escribir**: el doc completo, en orden (Índice → §0 → §10).
   No saltear secciones por "parecer familiar": las constantes y los bugs portados
   están donde están por una razón.
2. **No inventar**: si un valor, regla, texto i18n o mensaje no está acá, NO se
   crea de memoria. Se pregunta al usuario. Una respuesta "aproximada" es un defecto.
3. **Fuente única de verdad**: las constantes de §4.1/§4.5/§5.1 y las paletas de
   §6.2 son NORMATIVAS y se portan **exactas** (mismo nombre, mismo valor, mismo
   caso). Cualquier desvío es una decisión que exige justificación en el commit.
4. **Orden de fases innegociable** (§1): no arrancar dominio antes del smoke (Fase 2).
5. **Gate por fase**: cada fase termina con su checklist "Hecho cuando" (§8) y con
   `flutter analyze` + `flutter test` verdes. No avanzar con deuda roja.
6. **No ampliar alcance** (§2): features fuera de la tabla "Se porta" se descartan.
7. **Work units**: commits conventional commits por unidad revisable (§0); nunca
   un commit gigante que mezcle fases.
8. **Al pedir ayuda**: ante ambigüedad real, detenerse y preguntar UNA pregunta
   concreta (no listas de opciones).

### Skills a cargar (por fase)

| Fase | Skill |
|------|-------|
| 1 | `flutter-apply-architecture-best-practices` |
| 3 | `flutter-setup-localization` |
| 5 | `flutter-add-widget-test`, `flutter-build-responsive-layout`, `flutter-add-widget-preview`, `flutter-setup-declarative-routing` |
| 6 | `judgment-day` |

> La skill `flutter-use-http-package` NO aplica: la descarga del modelo es con
> **`dio`** (resumible con Range), decisión ya tomada.

### AGENTS.md mínimo a escribir en el proyecto nuevo

1. Regla de dependencia (§3): `lib/domain/` Dart puro, `lib/data/` único lugar con
   plugins, `lib/presentation/` solo depende de `domain/`, `main.dart` composition root.
2. Idioma: español en código/docstrings/docs; UI ES/EN vía `.arb`.
3. Commits: conventional commits, sin atribución de IA.
4. Gate de calidad previo al build: `flutter analyze` + `flutter test` + judgment-day.
5. No comprometer secretos ni API keys.

---

## 1. Quick path — primeros 30 minutos

```bash
# 1. Crear el proyecto (desde la carpeta que será su padre)
flutter create supertonic_audiobook --platforms=android,ios,windows,linux --org com.supertone

# 2. Entrar y arrancar Opencode
cd supertonic_audiobook
opencode

# 3. En la conversación: cargar la skill de arquitectura y escribir AGENTS.md
#    (contenido mínimo en §0)
```

**Plataformas objetivo**: Android, iOS, Windows (x86_64) y Linux (x86_64). Ver
§3 para el soporte real de cada plugin. (Si más adelante se quiere macOS: el
soporte existe, pero ONNX exige macOS 14+ y `Input/Output info` no está en la
API Swift — fuera de alcance por ahora.)

Orden innegociable: **Fase 1 (scaffold) → Fase 2 (smoke del modelo en cada
target, riesgo #1, PRIMERO) → Fase 3 (dominio con tests) → Fase 4 (audio) →
Fase 5 (UI) → Fase 6 (QA/release)**. No empieces el dominio antes de validar que
`flutter_onnxruntime` corre en el device/target real.

---

## 2. Alcance y descartes (paridad)

### Se porta 1:1

- Convertir `.md` → audiolibro en **4 formatos**: WAV/FLAC/OGG/MP3.
- Pipeline completo: leer → limpiar markdown → segmentar → sintetizar → exportar.
- Síntesis local con **supertonic-3** (ONNX, 99M params, 31 idiomas + `na`, salida
  44.1 kHz 16-bit), 10 voces, 5–12 pasos, 0.7–2.0× velocidad.
- Selección múltiple de archivos, progreso, **cancelación con exportación parcial**.
- Ajustes completos: tema claro/oscuro, estilo (material/neumo/skeuo), idioma
  ES/EN, voz, pasos, velocidad, idioma de voz, formatos, carpetas.
- Botón **Escuchar** (muestra de voz con el idioma seleccionado).
- Sección **Acerca de** con créditos y enlaces.
- i18n ES/EN (83 claves por idioma, ver §6).
- Natural sort de archivos.

### Se descarta / se reemplaza en Flutter

| Desktop (Python) | Flutter multiplataforma |
|---------|---------|
| CLI (`cli.py`: argparse, `--cli`, tqdm, guard anti path-traversal) | NO aplica (descartada en móvil y desktop) |
| `configurar_entorno()` / `SUPERTONIC_CACHE_DIR` / `sys.frozen` | `getApplicationDocumentsDirectory()` + descarga resumible con `dio` |
| `winsound` (reproducir muestra) | `just_audio` (+ `just_audio_media_kit` en Windows/Linux) |
| `soundfile` (sf.write / sf.SoundFile) | `wav_io` propio (§5) + `ffmpeg_kit_flutter_new` |
| Tkinter GUI | Flutter Material 3 |
| Packaging desktop (`docs/packaging.md`: PyInstaller, `.exe`, instaladores) | Builds nativos de Flutter por plataforma (Fase 6): `appbundle`/APK (Android), IPA (iOS), bundle de Windows, AppImage/deb (Linux) |

> **Solo se porta lo que la app necesita.** La GUI (Tkinter), la CLI
> (`cli.py`) y el packaging del desktop Python (PyInstaller) **NO se implementan
> en Flutter**: la GUI se reemplaza por Flutter Material 3, la CLI no aplica y el
> empaquetado es el build nativo de Flutter por plataforma (Android/iOS/Windows/
> Linux). El `self_test.py` se expone como opción de debug en la app (ver §6.6).
> La app Flutter **reemplaza también al desktop Python** (Windows/Linux) con una
> única base de código: mismo pipeline, misma paridad de comportamiento.

---

## 3. Arquitectura objetivo (Clean Architecture)

Misma Regla de Dependencia del desktop Python, adaptada:

| Capa | Contenido | Regla |
|------|-----------|-------|
| `lib/domain/` | Entidades, contratos (abstract), casos de uso, constantes de producto | Dart PURO, sin importar Flutter ni onnxruntime |
| `lib/data/` | `MotorTts` (flutter_onnxruntime + helper), `ExportadorAudio`, `RepositorioArchivos`, `RepositorioPreferencias`, `ModeloManager` | ÚNICO lugar que importa paquetes externos |
| `lib/presentation/` | Screens, widgets, controllers (Riverpod), tema, i18n | Solo Flutter |
| raíz (composición) | `main.dart`, inyección de dependencias | Arma el grafo |

**Estado**: Riverpod 3.4.2 (único framework; API moderna `Notifier`/`AsyncNotifier`,
no `StateProvider` legacy). No mezclar con Bloc.

### 3.1 Decisiones ya tomadas (NO re-litigar)

Todo esto está decidido y verificado. El agente lo implementa; no lo cuestiona.

| Decisión | Elección | Por qué (breve) |
|----------|----------|-----------------|
| Plataformas objetivo | Android, iOS, Windows (x86_64), Linux (x86_64) | Requisito del usuario; todos los plugins lo soportan (§3) |
| Motor TTS | `flutter_onnxruntime` ^1.8.3 | ORT 1.23.0; CPU ✅ en las 4 plataformas; MIT |
| Encode FLAC/OGG/MP3 | `ffmpeg_kit_flutter_new` ^4.6.2 | Fork mantenido del FFmpegKit retirado; streaming; GPL al publicar |
| Reproducción | `just_audio` + `just_audio_media_kit` (desktop) | Misma API `AudioPlayer` en todas las plataformas |
| Estado | `flutter_riverpod` ^3.4.2 | Único framework; sin mezclar con Bloc |
| Entidades | `equatable` (sin codegen) | `domain/` Dart puro; evita `build_runner` |
| HTTP | `dio` ^5.x (no `http`) | Descarga resumible con `Range` |
| Modelo | Descarga en runtime, NUNCA bundle | ~400 MB; resumible con aviso al usuario |
| Paridad de bugs | Portar tal cual (§4) | El "doble punto" y el segmento vacío son comportamiento verificado |
| CLI del desktop | Descartada (§2) | No aplica en ninguna plataforma del port |
| i18n | 83 claves ES/EN vía `.arb` | Verificado contra `TRADUCCIONES` (§6.5) |

### Dependencias (paquetes) — verificadas en pub.dev 2026-08-10

Runtime:

| Paquete | Versión | Propósito | Capa |
|---------|---------|-----------|------|
| `flutter` + `flutter_localizations` | SDK (3.44.9) | UI, Material, l10n base | presentación |
| `flutter_riverpod` | ^3.4.2 | Estado (requiere Dart ^3.12 — OK con Flutter 3.44.9 / Dart 3.12.2) | presentación |
| `intl` | ^0.20.x | Formato de fechas/números (l10n) | presentación |
| `path_provider` | ^2.1.x | Rutas `getApplicationDocumentsDirectory()` para modelo y salidas | data |
| `flutter_onnxruntime` | ^1.8.3 | Inferencia ONNX (ORT 1.23.0) — motor TTS. CPU ✅ en Android/iOS/Windows/Linux | data |
| `dio` | ^5.x | Descarga resumible del modelo (~400 MB) con Range/continuación | data |
| `ffmpeg_kit_flutter_new` | ^4.6.2 | Encode FLAC/OGG/MP3 + ffprobe para duración; SAF en Android. Windows/Linux x86_64 | data |
| `just_audio` | ^0.10.x | Reproducción del audiolibro generado y de la muestra | presentación |
| `just_audio_media_kit` | ^0.0.x | Implementación de `just_audio` para **Windows y Linux** (obligatoria en desktop) | presentación |
| `share_plus` | ^10.x | Compartir/exportar el audiolibro terminado | presentación |
| `file_picker` | ^8.x | Selección de archivos `.md` | data |
| `shared_preferences` | ^2.x | Ajustes persistidos (equivalente a `preferencias.json`) | data |
| `equatable` | ^2.x | Entidades inmutables con `==`/`hashCode` por campos (sin codegen) | domain |
| `logger` | ^2.x | Logs (igual que el ejemplo oficial del vendor) | todas |

Dev/test:

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| `flutter_test` | SDK | Tests de dominio, casos de uso, natural sort |
| `mocktail` | ^1.x | Mocks de contratos (sin codegen) |
| `flutter_lints` | ^5.x | Lints por defecto |
| `integration_test` | SDK | Smoke E2E en device (síntesis real) |

**Por qué `ffmpeg_kit_flutter_new` y no el original**: el paquete `ffmpeg_kit_flutter`
fue retirado/discontinuado en 2025. `ffmpeg_kit_flutter_new` es el fork comunitario
mantenido (FFmpeg 8.1.2, V2 embedding de Android, SAF nativo, API casi idéntica:
`FFmpegKit.execute`). Plataformas: Android, iOS, macOS, Windows (x86_64) y Linux
(x86_64). NOTA: al publicar, este paquete es GPL → revisar implicancias de licencia
si se distribuye (el desktop Python usaba ffmpeg del sistema). Requisitos desktop:
Windows descarga las libs prebuilt (x86_64) al build; **Linux requiere
`libjson-glib-dev`** además de los prerrequisitos de Flutter (`clang`, `cmake`,
`ninja-build`, `pkg-config`, `libgtk-3-dev`).

**`just_audio` en Windows/Linux**: el paquete base no incluye implementación para
desktop; hay que sumar `just_audio_media_kit` (y `media_kit_libs_windows_audio` /
`media_kit_libs_linux`). En Android/iOS se usa la implementación nativa. Todo
detrás de la misma API `AudioPlayer` → la capa `presentation/` no cambia.

**Por qué `equatable` y no `freezed`**: evita el codegen (`build_runner`) en el
dominio, manteniéndolo Dart puro sin dependencias de compilación.

**Config de `flutter_onnxruntime` por plataforma**:
- Android: agregar a `android/app/proguard-rules.pro`:
  ```
  -keep class ai.onnxruntime.** { *; }
  ```
  El plugin exige la línea (lo documenta el propio paquete).
- iOS: mínimo **iOS 16** y enlace estático (`use_frameworks! :linkage => :static`
  en `ios/Podfile`). OJO: en iOS `Input/Output info` y `Model Metadata` NO están
  disponibles (API Swift) → el helper no debe depender de inspeccionar tensores.
- Windows/Linux: sin config extra para ORT (las libs se bajan al build).

### Estructura de carpetas

```
lib/
├── main.dart                 # Composición: ProviderScope + runApp (único import de data/)
├── app.dart                  # MaterialApp: tema, localizaciones, rutas
│
├── domain/                   # Dart PURO — sin Flutter ni onnxruntime (paridad con el desktop)
│   ├── constants/
│   │   └── producto.dart     # DEFAULT_VOICE, DEFAULT_LANG, LANGUAGES_VOZ, VOCES,
│   │                         #   TTS_STEPS, SPEED, límites (§4)
│   ├── entities/
│   │   └── archivo.dart      # Archivo(ruta, nombre, titulo) — immutable + equatable
│   ├── repositories/         # CONTRATOS (abstract class) — nada concreto acá
│   │   ├── motor_tts.dart
│   │   ├── repositorio_archivos.dart
│   │   ├── exportador_audio.dart
│   │   └── repositorio_preferencias.dart
│   └── use_cases/            # lógica de negocio pura (§4)
│       ├── normalizar_formatos.dart
│       ├── limpiar_markdown.dart
│       ├── segmentar_texto.dart
│       ├── procesar_archivo.dart
│       └── sintetizar_muestra.dart
│
├── data/                     # ÚNICA capa que importa plugins/paquetes externos
│   ├── helpers/
│   │   └── supertonic_helper.dart  # port de helper.dart del vendor (tokenizador/vocoder ONNX)
│   ├── modelo/
│   │   └── modelo_manager.dart     # descarga resumible (dio), rutas (path_provider), verificación
│   └── repositories/              # implementaciones concretas de los contratos
│       ├── motor_tts_onnx.dart
│       ├── repositorio_archivos_local.dart
│       ├── exportador_audio_ffmpeg.dart
│       └── repositorio_preferencias_local.dart
│
├── presentation/             # Solo Flutter — depende de domain/, no de data/
│   ├── controllers/          # Riverpod providers (Notifier/AsyncNotifier)
│   │   ├── home_controller.dart      # lista, procesamiento (Isolate), progreso
│   │   └── settings_controller.dart  # ajustes + persistencia
│   ├── screens/
│   │   ├── home_screen.dart
│   │   └── settings_screen.dart
│   ├── widgets/              # componentes reutilizables
│   │   ├── archivo_tile.dart
│   │   ├── barra_progreso.dart
│   │   └── acerca_de_section.dart
│   ├── theme/
│   │   └── app_theme.dart    # claro/oscuro + estilos (§6)
│   └── l10n/                 # .arb ES/EN (83 claves × 2, §6)
│       ├── app_es.arb
│       └── app_en.arb
│
└── core/                     # utilidades transversales SIN negocio
    ├── utils/
    │   └── natural_sort.dart # orden natural de archivos (§5)
    └── audio/
        └── wav_io.dart       # header RIFF + append + parche de tamaño (§5)
```

Notas:

- `domain/` NO importa `flutter/material` ni `dart:io` donde interfiera con el
  testeo puro; los `use_cases` reciben datos vía contratos para ser 100% testeables.
- `core/` es transversal y no conoce negocio.
- Los providers de Riverpod se construyen en `main.dart` inyectando las
  implementaciones concretas de `data/` → los widgets solo ven los contratos de `domain/`.
- `test/` refleja la estructura: `test/domain/` (puro), `test/data/` (repositorios con
  mocks de plugins), `test/presentation/` (widget tests), `integration_test/` (smoke E2E).
- **Procesamiento pesado en un `Isolate`** (`Isolate.run`) con progreso vía Stream
  para no bloquear la UI.

---

## 4. Especificación de dominio (reglas de negocio puras)

### 4.1 Constantes de producto — valores EXACTOS

```dart
const defaultVoice = 'M1';
const defaultLang = 'es';   // código ISO del modelo supertonic-3
const defaultTtsSteps = 5;  // pasos de inferencia (más = mejor, más lento)
const defaultSpeed = 1.1;   // velocidad de habla (1.0 = normal)

// Idiomas soportados por supertonic-3: 31 + "na" (texto sin idioma)
const languagesVoz = [
  'es','en','ar','bg','cs','da','de','el','et','fi','fr','hi','hr','hu','id',
  'it','ja','ko','lt','lv','nl','pl','pt','ro','ru','sk','sl','sv','tr','uk','vi','na',
];

// Voces integradas del modelo (M1-M5, F1-F5)
const voces = ['M1','M2','M3','M4','M5','F1','F2','F3','F4','F5'];
```

Rangos de la UI (ver §6): pasos **5–12** (default 5), velocidad **0.7–2.0**
(default 1.1), formatos por defecto marcados: **wav y mp3**.

### 4.2 Entidad `Archivo`

```dart
class Archivo {          // immutable, equatable
  final String ruta;      // ruta completa al .md
  String get nombre;      // nombre con extensión (ej: 'archivo3.md')
  String get titulo;      // nombre sin extensión (se usa para nombrar el audio)
}
```

### 4.3 Contratos (interfaces de dominio)

```dart
// MotorTTS
Float32List sintetizar(String texto, {required int steps, required double speed,
  String lang = defaultLang});   // vacío si no se generó audio

// RepositorioArchivos
void crearCarpetasSiNoExisten(List<String> carpetas);
List<Archivo> listarArchivosMd(String carpeta); // .md + natural sort
String leerArchivo(String ruta);                // UTF-8

// ExportadorAudio
void escribirAudio(List<Float32List> fragmentos, String ruta, String formato);
void wavAppend(List<Float32List> fragmentos, String ruta); // WAV PCM16 append
void convertirDesdeWav(String rutaWav, String rutaDestino, String formato);
double duracionAudio(String ruta);               // 0.0 si no se puede leer

// RepositorioPreferencias
Map<String, Object> cargar();                    // {} si no hay ninguna
void guardar(Map<String, Object> preferencias);  // valores serializables
```

### 4.4 Caso de uso `normalizar_formatos`

```dart
const formatosNativos = ['wav', 'flac', 'ogg', 'mp3'];

List<String> normalizarFormatos(String cadena); // ej: "wav,MP3"
```
- Convierte a minúsculas, elimina espacios, **ignora duplicados**, conserva el orden
  de aparición.
- Lanza `ValueError` (en Dart: `FormatException` o excepción propia) si hay un formato
  desconocido, con mensaje: `Formato no soportado: '<f>'. Válidos: wav, flac, ogg, mp3.`

### 4.5 Caso de uso `limpiar_markdown` — regex EXACTAS

Aplica las reglas **en este orden** (importante: bloques de código ANTES que
títulos/negrita/inline, imágenes ANTES que links, HR antes que listas). Es el
comportamiento verificado del desktop:

```dart
// 1. Bloques de código (DOTALL): ```...``` y ~~~...~~~
//    NOTA Dart: RegExp soporta DOTALL; lookbehind de ancho variable SÍ existe en Dart
//    (JS-style), así que NO se necesita el truco \x00 del Python para estas reglas.
// 2. Títulos: ^#{1,6}\s*  (por línea, MULTILINE)
// 3. Énfasis asteriscos, en pasadas separadas por conteo EXACTO:
//    (?<![\\w*])\*{3}(?![\s*])(.*?)(?<![\s*])\*{3}(?![\\w*])   → \1
//    (?<![\\w*])\*{2}(?![\s*])(.*?)(?<![\s*])\*{2}(?![\\w*])   → \1
//    (?<![\\w*])\*{1}(?![\s*])(.*?)(?<![\s*])\*{1}(?![\\w*])   → \1
// 4. Énfasis subrayado, mismas reglas (no intraword, no adyacente a espacio/_):
//    (?<!\w)_{3}(?![\s_])(.*?)(?<![\s_])_{3}(?!\w)  → \1
//    (?<!\w)_{2}(?![\s_])(.*?)(?<![\s_])_{2}(?!\w)  → \1
//    (?<!\w)_{1}(?![\s_])(.*?)(?<![\s_])_{1}(?!\w)  → \1
// 5. Inline code: `{1,3}(.*?)`{1,3}                    → \1
// 6. Imágenes ANTES que links: !\[([^\]]*)\]\([^)]+\)  → \1  (alt text)
// 7. Links: \[([^\]]+)\]\([^)]+\)                      → \1
// 8. Blockquotes anclados a inicio de línea: ^\s*>\s?    (MULTILINE) → ''
// 9. HR (línea completa, MULTILINE, va ANTES de listas):
//    ^\s*(?:-{3,}|\*{3,}|(?:\*[ \t]*){3,}|(?:-[ \t]*){3,})\s*$  → ''
//10. Listas (ancladas): ^\s*[-*+]\s+                  (MULTILINE) → ''
//11. Listas ordenadas (hasta 3 dígitos): ^\s*\d{1,3}[.)]\s+ (MULTILINE) → ''
//12. Normaliza saltos: \n{3,} → \n\n
//13. strip() final
```

**Reglas de seguridad verificadas (casos que NO deben alterarse)**:
- `2 * 3 * 4` y `a*b*c` → no son énfasis (asterisco adyacente a espacio o intraword).
- `clave_privada_valor` → no es énfasis con `_` (intraword).
- `2024. Cifra...` → no es lista ordenada (anclaje + `\s+`).
- `5 > 3` → no es blockquote (sin ancla al inicio de línea).
- `a---b` / `x***y` en prosa → no son HR (anclado a línea completa).
- `**a**b` (negrita pegada a palabra) → se conserva literal.
- Bloque ``` dentro de ``` → no se toca (bloques antes que inline).

### 4.6 Caso de uso `segmentar_texto`

```dart
const maxCharsPerSegment = 1500;  // máximo de caracteres por fragmento
const mergeThreshold = 200;       // párrafos más cortos que esto se fusionan con el siguiente
const _abreviaturas = ['Dr','Dra','Sr','Sra','Sta','Sto','etc','i.e','e.g','vs',
                       'Lic','Ing','Mtro','Mtra','Prof','Gral'];
```

Algoritmo (verificado contra `segmentar_texto.py`):

1. Divide por saltos de línea → párrafos (`.strip()`, descarta vacíos).
2. **Fusión**: acumula en `buffer`; fusiona `p` con el buffer **solo si**
   `len(buffer)+len(p) < maxCharsPerSegment` (estricto `<`) **y** `len(p) < mergeThreshold`.
   Si no, cierra el buffer y arranca uno nuevo con `p`.
3. **División de párrafos largos** (`len(p) > maxCharsPerSegment`):
   - Divide por oraciones con el split `(?<=\.)\s+` (el punto queda en la frase).
   - Reconstruye: si `len(buffer_frase)+len(frase)+2 <= maxCharsPerSegment`, agrega
     `frase + ". "`; si no, cierra el segmento actual y arranca uno nuevo.
   - Cada segmento final se publica con `.strip()`.

**Protección de abreviaturas**: antes del split se reemplaza `abr + "."` por
`abr + "\x00"`, se divide, y se restaura `\x00` → `"."`. En Dart esto es directo
(`replaceAll`), porque Dart no tiene la limitación de lookbehind de Python.

**Comportamientos verificados (paridad, incluye bugs conocidos del desktop)**:
- El split conserva el punto de cierre de cada oración, y la reconstrucción agrega
  `". "` de nuevo → **un párrafo largo dividido produce ".. " en la unión**
  (doble punto, comportamiento real del desktop). Portar tal cual (paridad) a menos
  que se decida corregir; si se corrige, documentarlo explícitamente en el commit.
- Un párrafo con UNA sola oración > 1500 chars produce un segmento vacío al inicio y
  uno que excede el límite. Comportamiento real verificado.

### 4.7 Caso de uso `procesar_archivo` — pipeline completo

Firma:

```dart
void procesar(
  Archivo archivo,
  String rutaBase,              // salida sin extensión (ej: audio/archivo)
  {required int steps,
   required double speed,
   required List<String> formatos,
   String lang = defaultLang,
   void Function(int procesados, int total)? onProgreso,
   bool Function()? debeDetenerse})
```

Constructor inyecta: `motor`, `archivos`, `exportador`, `silencioMuestras`,
`memoriaSafeMarginBytes`.

Orden EXACTO (verificado):

1. Leer archivo (UTF-8) → `limpiar_markdown`. Error de lectura → loguear y **return**
   (no aborta los demás archivos).
2. Si el texto queda vacío tras limpiar → loguear "se omite" y return.
3. `segmentar_texto` → `total` = cantidad de segmentos.
4. **Dedupe de formatos**: `List<String> formatos = {...}` (dict.fromkeys: conserva
   orden, elimina duplicados — evita doble `os.replace` del mismo temporal).
5. Crear **WAV temporal** (`mkstemp` en la carpeta de salida). Nada se escribe sobre
   la ruta final hasta el final (garantiza que cancelar/fallar no dañe el output previo).
6. Bucle por segmento:
   - `if debeDetenerse() → cancelado = true; break` (cancelación ENTRE segmentos).
   - `wav = motor.sintetizar(texto, steps, speed, lang)`.
   - `onProgreso(procesados, total)` **después de cada síntesis** (el total se conoce
     recién tras segmentar; la barra ajusta `total` en el primer callback).
   - Si `wav.size == 0` → `continue` (no aborta).
   - Acumula: `fragmentos.add(wav)`; `memoria += wav.nbytes`;
     `fragmentos.add(zeros(silencioMuestras))`; `memoria += silencioMuestras * 4`.
   - **Flush parcial**: si `memoria > memoriaSafeMarginBytes` → `wavAppend(fragmentos,
     wavTrabajo)`, limpiar lista, resetear memoria, `parcialEscrito = true`.
7. Si `cancelado` → loguear y exportar lo generado hasta ahora.
8. Si `fragmentos` vacío Y `!parcialEscrito` → loguear error "No se generó ningún
   fragmento" y return (sin salidas).
9. **Exportar en 2 fases**:
   - Fase 1 (temporales): si `parcialEscrito` → `wavAppend(fragmentos, wavTrabajo)`
     y convertir a temporales (wav = el propio temporal; otros = `convertirDesdeWav`).
     Si no → `escribirAudio(fragmentos, temporal, formato)` por formato.
   - Fase 2 (publicar): cada `os.replace(temporal, destino)` es **atómico por archivo**.
     Orden: **no-WAV primero, WAV AL FINAL** (`_orden_publicacion`: sort por
     `destino.name.lower().endsWith(".wav")`). Si un formato falla (`PermissionError`
     = archivo en uso), se loguea, se **propaga**, y los demás ya publicados quedan;
     el WAV previo NO se toca.
10. `finally`: borrar temporales (ignorando FileNotFound/Permission).
11. Por cada formato: `duracionAudio(ruta)` y loguear `+ nombre (FORMATO): X.X s`.

Valores técnicos inyectados desde `data/config.dart` (ver §5): `SILENCE_SAMPLES`,
`MEMORY_SAFE_MARGIN_BYTES`.

### 4.8 Caso de uso `sintetizar_muestra`

```dart
String generar(String texto, {String lang = defaultLang, required String ruta});
```
- Sintetiza con `steps = defaultTtsSteps`, `speed = defaultSpeed`.
- Escribe WAV PCM16 con `escribirAudio([wav], ruta, 'wav')`. Devuelve la ruta.
- Lo usa el botón **Escuchar**.

---

## 5. Especificación de datos (audio, archivos, modelo)

### 5.1 Constantes técnicas — valores EXACTOS

```dart
const sampleRate = 44100;            // Hz
const silenceDurationSecs = 0.6;     // silencio entre fragmentos
const silenceSamples = 26460;        // sampleRate * silenceDurationSecs
const memoriaSafeMarginBytes = 524288000; // 500 * 1024 * 1024
const subtiposAudio = { 'wav':'PCM_16', 'flac':'PCM_16', 'ogg':'VORBIS', 'mp3':'MPEG_LAYER_III' };
```

### 5.2 WAV byte-level (`core/audio/wav_io.dart`)

- **Formato**: 44100 Hz, mono, **PCM16 little-endian**.
- Conversión float32→int16: `pcm16 = clip(audio, -1, 1) * 32767` → int16 LE.
- `escribirAudio(fragmentos, ruta, 'wav')`: `concat(fragmentos, float32)` →
  clip → int16 → escribir.
- `wavAppend(fragmentos, ruta)` (port de `wav_append`):
  - Si el archivo no existe o pesa 0 → escribir header RIFF completo nuevo.
  - Si no: append **crudo de los samples int16** al final, y **parchear el header**:
    - offset 4: tamaño del archivo RIFF (`tamaño_total - 8`, uint32 LE).
    - escanear chunks desde offset 12 leyendo `chunk_id(4) + chunk_size(4)`:
      localizar el chunk `data`, parchear su `chunk_size` (`tamaño_total -
      offset_del_data`) y salir; saltar payloads con alineación par
      (`chunk_size + (chunk_size % 2)`).
- Duración: solo header (`frames / samplerate`), **0.0 si error** (nunca carga el archivo).

### 5.3 Conversión FLAC/OGG/MP3 (`data/repositories/exportador_audio_ffmpeg.dart`)

- **Streaming por bloques**, NUNCA full-load del WAV (el desktop transmite con
  `sf.SoundFile(...).blocks(blocksize=65536)`; docs viejos decían full-load — es stale).
- Con `ffmpeg_kit_flutter_new` (Android/iOS/Windows/Linux x86_64):
  - WAV → FLAC: `-c:a flac`
  - WAV → OGG: `-c:a libvorbis`
  - WAV → MP3: `-c:a libmp3lame`
- `duracionAudio` con `FFprobeKit.getMediaInformation` (lee solo metadata).
- En Linux el ffmpeg no existe en el sistema: el paquete baja las libs al build
  (requiere `libjson-glib-dev`); en Windows también las baja automáticamente.

### 5.4 Natural sort (`core/utils/natural_sort.dart`)

Algoritmo exacto (port de `_natural_sort_key`):

```dart
// split del stem por (\\d+) → tokens alternados texto/número; números como int.
// Si no hay tokens → (stem,).
// Discriminador: 0 si el primer token es número, 1 si es texto.
// Clave: (discriminador, tokens, stem).
// Ordenar con esa clave.
```

Casos de orden verificados (tests):
- `capitulo.md < capitulo1.md < capitulo2.md < capitulo10.md`
- `archivo2.md < archivo10.md` (no lexicográfico)
- `c1s2.md < c1s10.md` (múltiples números)
- `archivo01.md < archivo1.md` (padding se ignora como int; desempate determinista por stem)
- `3.md` (empieza con número, discriminador 0) ordena antes que los de texto.
- Solo `.md` (case-insensitive en la extensión). Carpeta inexistente → lista vacía.

### 5.5 Modelo y motor TTS (`data/`)

> **Guía de inicio (verificada 2026-08-10)**: el ejemplo oficial
> `supertone-inc/supertonic/flutter/` es la referencia para copiar. `lib/helper.dart`
> (MIT) se copia verbatim a `data/helpers/supertonic_helper.dart` (ya previsto).
> El `main.dart` del ejemplo se guarda como `reference/example_main.dart`: sirve SOLO
> como guía del smoke (cómo cargar el modelo y llamar a synthesize); el `main.dart`
> de la app es el composition root con Riverpod (§3). Paquetes del ejemplo ya
> cubiertos por §3 (usa `flutter_onnxruntime` ^1.8.3, no ^1.6.0 del ejemplo; `args`
> NO aplica en móvil). **NO copiar la sección `assets:` del pubspec del ejemplo**
> (embebe el modelo): acá el modelo se descarga en runtime.

- **Modelo**: supertonic-3, ONNX, ~400 MB. **Descarga en runtime** a
  `getApplicationDocumentsDirectory()`, **resumible** con `dio` (headers `Range`,
  continuación), con aviso al usuario y verificación de integridad. **NUNCA bundle
  en el build** (aplica a las 4 plataformas: mismo `data/modelo/modelo_manager.dart`).
- **Motor**: `flutter_onnxruntime` (ORT 1.23.0) + port de `lib/helper.dart` del vendor
  (MIT) → `data/helpers/supertonic_helper.dart`: tokenización, carga de voz
  (`get_voice_style`), inferencia autoregresiva, decodificación de audio.
  - Flujo original del vendor: `TTS(auto_download=True)` → validar voz con
    `get_voice_style(voice_name=voz)` (si no existe → `ValueError` "La voz 'X' no
    está disponible"). Sintetizar con `synthesize(texto, voice_style, lang, total_steps,
    speed)` → `(wav, ...)`.
  - Fragmento silencioso (0 muestras) → devolver array vacío (no aborta).
  - Error de síntesis → `RuntimeError` con mensaje (se propaga).
- **Smoke obligatorio** en device/target real ANTES de escribir el dominio (Fase 2): valida
  ORT Android + opset + RAM. Si falla → Plan B (Kotlin + Pigeon, ver §9).

---

## 6. Especificación de presentación (UI, ajustes, i18n, Acerca de)

### 6.1 Pantallas y controles

**Home (Entrada y salida)**:
- Carpeta de origen (Examinar… con `file_picker`).
- Lista de `.md` con natural sort + checkboxes de selección.
  - "Marcá los que querés / sin marcas = todos" (behavior de la ayuda).
  - Botones: Todo / Nada / Refrescar. Conteo: "{sel}/{total} seleccionados".
- Opciones de síntesis: formato (checkboxes WAV/FLAC/OGG/MP3), voz (dropdown 10 voces,
  label "Modelo supertonic-3"), pasos (slider 5–12, "más calidad = más lento"),
  velocidad (slider 0.7–2.0, "más rápido / más lento"), idioma de la voz (dropdown de
  `LANGUAGES_VOZ`, `na` = "Auto (sin idioma)"), botón **Escuchar**.
- Registro (log) + barra de estado + botones **Procesar** / **Cancelar**.
- Formato de tiempo: "{total} s", "{min} min {seg} s", "{horas} h {min} min".
- Throttle del log: `paso = max(1, total ~/ 20)` (~20 líneas máx por archivo);
  truncado a 2500 líneas.

**Ajustes**: tema (Claro/Oscuro), estilo (Material/Neumorfismo/Skeuomorfismo),
idioma (Español/English), Acerca de.

### 6.2 Temas y paletas — valores EXACTOS (hex)

Material 3, baseline púrpura. `PALETA_CLARA`:

```dart
final paletaClara = {
  'fondo':'#F4F1FA','superficie':'#FFFFFF','superficie_variante':'#E7E0EC',
  'primario':'#6750A4','primario_claro':'#EADDFF','primario_vivo':'#7B67C8',
  'sobre_primario':'#FFFFFF','texto':'#1C1B1F','texto_secundario':'#79747E',
  'borde':'#CAC4D0','advertencia':'#B45309','error':'#B3261E','error_vivo':'#D0453E',
  'sobre_error':'#FFFFFF','snackbar_fondo':'#322F35','snackbar_texto':'#FFFFFF',
};
```

`PALETA_OSCURA`:

```dart
final paletaOscura = {
  'fondo':'#141218','superficie':'#211F26','superficie_variante':'#49454F',
  'primario':'#D0BCFF','primario_claro':'#4F378B','primario_vivo':'#BBA6F4',
  'sobre_primario':'#381E72','texto':'#E6E0E9','texto_secundario':'#CAC4D0',
  'borde':'#4A4458','advertencia':'#FDD663','error':'#F2B8B5','error_vivo':'#F8C7C4',
  'sobre_error':'#381E72','snackbar_fondo':'#E6E0E9','snackbar_texto':'#141218',
};
```

Estilos (overrides que se combinan con la paleta base):

```dart
const estilos = ['material', 'neumo', 'skeuo'];
// NEUMO_CLARA:  fondo #E8E4F0, superficie #E8E4F0, variante #DDD8EA, borde #CFC9DE,
//              luz #FDFBFF, sombra #C2BAD6, primario_luz #FFFFFF, primario_sombra #574E8C
// NEUMO_OSCURA: fondo/superficie #1C1A23, variante #232029, borde #2C2836,
//              luz #302C3C, sombra #0E0C12, primario_luz #E7D4FF, primario_sombra #8E77C8
// SKEUO_CLARA:  fondo #DEDEDE, superficie #EBEBEB, variante #CDCDCD, borde #9B9B9B,
//              luz #FFFFFF, sombra #7F7F7F, primario #2E6DB4, primario_claro #D3E3F6,
//              primario_vivo #3E7FC9, primario_luz #7FA8DE, primario_sombra #1F4A79, sobre_primario #FFFFFF
// SKEUO_OSCURA: fondo #3C3C3C, superficie #484848, variante #333333, borde #606060,
//              luz #5C5C5C, sombra #222222, primario #4D8CD6, primario_claro #314B69,
//              primario_vivo #5F9BE4, primario_luz #8AB4EA, primario_sombra #1E3A5C, sobre_primario #FFFFFF
```

Neumorfismo: superficie == fondo; elementos se distinguen solo por sombras suaves.
Skeuomorfismo: superficies grises neutras, biseles marcados, acento azul acero.
Responsive: `umbralAncho = 900` (paneles lado a lado por encima; apilados por debajo).

### 6.3 Preferencias persistidas (`shared_preferences`) — claves EXACTAS

| Clave | Tipo | Default / rango |
|-------|------|-----------------|
| `tema_oscuro` | bool | false |
| `estilo` | string | 'material' (una de `estilos`) |
| `idioma` | string | 'es' |
| `voz` | string | 'M1' |
| `steps` | int | 5 (rango 5–12) |
| `speed` | float | 1.1 (rango 0.7–2.0) |
| `lang_voz` | string | 'es' |
| `formatos` | list | ['wav','mp3'] (subconjunto de nativos) |
| `carpeta_in` | string | carpeta de entrada |
| `carpeta_out` | string | carpeta de salida |

Se guardan al: cambiar tema/estilo/idioma, iniciar procesamiento y al cerrar.

### 6.4 Acerca de — contenido EXACTO

```dart
const appNombre = 'Supertonic-AudioBook';
const appVersion = '1.0.3';
const repositorioUrl = 'https://github.com/Rafael-VH/Supertonic-AudioBook';
const modeloUrl = 'https://huggingface.co/Supertone/supertonic-3';
const modeloGithubUrl = 'https://github.com/supertone-inc/supertonic';
```

- `acerca_descripcion` ES: "Convierte tus libros Markdown en audiolibros con voz
  sintética: 100 % local, sin nube y sin GPU."
- `acerca_creditos` ES: "Modelo de voz: Supertonic 3, de Supertone Inc. (licencia OpenRAIL-M)"
- `acerca_licencia`: "Licencia MIT" (ES) / "MIT License" (EN).
- Enlaces: "Ver el modelo en Hugging Face" → `modeloUrl`; "Código fuente del modelo"
  → `modeloGithubUrl`; "Abrir repositorio en GitHub" → `repositorioUrl`.
- Muestra de voz por idioma: `TEXTO_MUESTRA_IDIOMAS` — 16 idiomas literales
  (`es`→"Hola, soy la voz de Supertonic. Esta es una muestra de audio.",
  `en`→"Hello, I am a Supertonic voice. This is an audio sample.", fr/de/pt/it/nl/pl/
  ru/uk/tr/ja/ko/ar/hi/vi con su traducción). Idiomas sin entrada usan la clave
  `muestra_texto`: "Esta es una muestra de la voz sintética." / "This is a sample of
  the synthetic voice.".
- Nombres nativos de idiomas: `IDIOMAS_VOZ_NATIVOS` (31 literales; `na` se muestra
  como "Auto (sin idioma)").

### 6.5 i18n — 83 claves ES/EN (verificadas)

Idiomas de interfaz: `IDIOMAS = {'es': 'Español', 'en': 'English'}`.
**83 claves por idioma** (NO 134 como decían docs viejas). Lista de claves:

`ventana_titulo, ajustes, tema, idioma, claro, oscuro, estilo, estilo_material,
estilo_neumorfismo, estilo_skeuomorfismo, acerca_de, acerca_descripcion,
acerca_version, acerca_licencia, acerca_creditos, acerca_ver_modelo,
acerca_ver_codigo, acerca_abrir_repositorio, cerrar, tab_entrada, tab_sintesis,
salida_audio, carpeta_origen, etiqueta_carpeta, examinar, archivos_encontrados,
todo, nada, refrescar, ayuda_seleccion, opciones_sintesis, formato, voz,
modelo_supertonic, pasos, calidad_lento, velocidad, rapido_lento, idioma_voz,
idioma_voz_auto, escuchar, muestra_texto, log_muestra, log_muestra_fin,
log_muestra_error, registro, btn_procesar, btn_cancelar, estado_listo,
estado_archivo, estado_segmentos, estado_listo_n, estado_cancelando,
estado_cancelado, estado_error, estado_con_errores, snackbar_formato,
snackbar_sin_md, snackbar_procesado, snackbar_exportado, snackbar_con_errores,
conteo_seleccionados, conteo_archivos, conteo_sin, log_inicio, log_formato_no_ok,
log_sin_md, log_cancelar, log_config_titulo, log_config_voz, log_config_lang,
log_config_formatos, log_config_salida, log_archivo, log_segmento,
log_archivo_fin, log_completado, log_con_errores, log_cancelado, log_error,
tiempo_seg, tiempo_min_seg, tiempo_hora_min`

Los textos ES/EN literales de estas 83 claves están en el dict `TRADUCCIONES` del
desktop (`app/presentation/gui.py`, líneas 203–374) — **portar palabra por palabra**
(los placeholders `{voz}`, `{lang}`, `{i}`, `{n}`, `{nombre}`, `{sel}`, `{total}`,
`{tiempo}`, `{actual}`, `{exitos}`, `{errores}`, `{pasos}`, `{vel}`, `{formatos}`,
`{salida}`, `{min}`, `{seg}`, `{horas}` y el `{texto}`). Claves con formato de tiempo:
`tiempo_seg="{total} s"`, `tiempo_min_seg="{min} min {seg} s"`,
`tiempo_hora_min="{horas} h {min} min"`.

> Si la conversación nueva no tiene acceso al dict original, reconstruirlo es un
> trabajo de traducción 1:1 que NO debe inventar textos: los mensajes de log y estado
> están normalizados arriba. Ante la duda, preguntar al usuario antes de traducir.

### 6.6 Self-test a portar (`presentation/self_test.dart`)

- Texto fijo: `"Prueba de síntesis del motor Supertonic."`
- Pasos/speed por defecto (`5`, `1.1`).
- Salida: `<carpeta_base>/audio/_self_test.wav`.
- Exit 0: `SELF-TEST OK voz=M1 muestras=<n> duracion=<d>s salida=<ruta>`.
- Exit 1: `SELF-TEST FAIL: <motivo>` (incluye "no se generó audio").
- En Flutter se ejecuta como comando opcional de la app (no hay CLI); exponer como
  opción de debug o test de integración.

---

## 7. Tests a portar (41 casos — lista literal)

Distribución verificada: `limpiar_markdown` 18, `procesar_archivo` 10,
`repositorio_archivos` 8, `segmentar_texto` 5.

### 7.1 `test_limpiar_markdown` (18)

`test_quita_titulos`, `test_quita_negrita_cursiva_y_codigo_inline`,
`test_quita_links_e_imagenes`, `test_quita_blockquotes_y_listas`,
`test_quita_bloques_de_codigo`, `test_quita_bloques_tilde`,
`test_normaliza_saltos_y_recorta`, `test_prosa_con_operadores_no_se_altera`,
`test_multiplicaciones_con_espacios_no_se_altera`,
`test_underscores_no_comen_snake_case`, `test_hr_guiones_espaciados`,
`test_hr_con_mas_de_tres_marcadores`, `test_operadores_asterisco_sin_espacios_no_se_altera`,
`test_negrita_pegada_a_palabra_no_se_mutila`, `test_comparadores_y_flechas_no_se_altera`,
`test_quita_listas_ordenadas`, `test_hr_solo_en_linea_completa`,
`test_negrita_dentro_de_bloque_de_codigo_no_se_toca`.

### 7.2 `test_segmentar_texto` (5)

`test_respeta_parrafos_existentes` (párrafo > 200 no se fusiona), `test_fusiona_parrafos_cortos`,
`test_dividir_parrafo_largo_por_oraciones` (cada segmento ≤ 1500), `test_no_parte_abreviaturas_espanolas`
("El Dr. Pérez llegó a tiempo." × 40 → conserva "Dr."), `test_parrafo_corto_se_mantiene_entero`.

### 7.3 `test_repositorio_archivos` (8)

`test_mezcla_numerados_y_no_numerados_no_crashea`, `test_orden_natural_corrige_lexicografico`,
`test_usa_multiples_numeros` (c1s2 < c1s10), `test_no_numerado_va_antes_que_su_numerado`
(capitulo.md < capitulo1.md), `test_ceros_izquierda_desempatan_determinista` (archivo01 < archivo1),
`test_lista_solo_md_ordenados`, `test_carpeta_inexistente_devuelve_vacia`, `test_leer_archivo_roundtrip`.

### 7.4 `test_procesar_archivo` (10) — usa `MotorTTSStub`

Stub del motor: devuelve `SEGMENTO = np.full(int(44100 * 0.2), 0.5, float32)` (0.2 s @44100);
variante `silencio=True` devuelve array vacío. Exportador REAL. `silencio_muestras=0`.

`test_flush_por_memoria_genera_wav_valido` (margen=1 fuerza flush; WAV válido con duración > 0),
`test_volver_a_procesar_no_duplica_audio` (dos corridas → misma duración ±0.1),
`test_flush_con_formato_no_wav_convierte_desde_temporal` (solo .flac, sin .wav residual),
`test_flush_wav_y_flac_publica_ambos`, `test_publica_wav_al_final` (orden mp3, flac, WAV),
`test_fallo_publicacion_no_wav_no_actualiza_wav` (mock de replace que falla en .flac →
solo intenta publicar .flac, WAV intacto, propaga PermissionError),
`test_archivo_vacio_no_genera_salida`, `test_cancelado_al_inicio_no_genera_salida`,
`test_cancelar_no_destruye_salida_previa`, `test_fallo_no_destruye_salida_previa`
(motor que lanza RuntimeError → salida previa intacta).

### 7.5 Tests adicionales del port Flutter

- `helper.dart` del vendor: tests específicos de tokenización/vocoder con datos sintéticos.
- Widget tests de Home/Ajustes/Acerca de.
- `integration_test`: smoke real en device (síntesis de 1 segmento + reproducción).

---

## 8. Fases paso a paso

### Fase 0 — Prerrequisitos (fuera de Opencode)

- Flutter SDK ^3.5.0, `flutter doctor` sin errores.
- **Android**: Android Studio + SDK; device/emulador **ARM64** (ARM emulado en x86
  no es representativo para ONNX).
- **iOS** (opcional para el desarrollo inicial): Xcode + CocoaPods; el build de
  iOS requiere macOS. La app se puede desarrollar en Android + desktop sin Mac.
- **Windows**: Visual Studio 2022 con "Desktop development with C++".
- **Linux**: `clang`, `cmake`, `ninja-build`, `pkg-config`, `libgtk-3-dev` y
  `libjson-glib-dev` (requisito de ffmpeg_kit_flutter_new).

### Fase 1 — Scaffold y arquitectura

1. `flutter create supertonic_audiobook --platforms=android,ios,windows,linux --org com.supertone`
2. Iniciar `opencode` en el proyecto nuevo; escribir `AGENTS.md` (contenido en §0);
   copiar este documento como `HANDOFF.md` en la raíz.
3. Cargar skill `flutter-apply-architecture-best-practices` y estructurar las capas
   (§3).
4. Dependencias con `flutter pub add`: `flutter_riverpod`, `path_provider`,
   `flutter_onnxruntime`, `dio`, `just_audio`, `just_audio_media_kit`,
   `shared_preferences`, `equatable`, `logger`, `intl` (ffmpeg y share_plus en
   Fase 4). Config de plataforma (§3): Android `proguard-rules.pro`; iOS mínimo
   16 + enlace estático.
5. `flutter analyze` limpio en las 4 plataformas y commit inicial.

> **Hecho cuando**:
> - [ ] `flutter create` generó las carpetas `android/`, `ios/`, `windows/`, `linux/`.
> - [ ] `AGENTS.md` y `HANDOFF.md` en la raíz; capas de §3 creadas.
> - [ ] `flutter pub get` sin errores; `proguard-rules.pro` y `Podfile` (iOS 16 + estático) configurados.
> - [ ] `flutter analyze` con 0 errores en Android y en un desktop; commit inicial hecho.

### Fase 2 — El modelo en cada target (Riesgo #1, ir PRIMERO)

1. Modelo: `git clone https://huggingface.co/Supertone/supertonic-3` (LFS) o descarga
   en runtime con `dio` (resumible, con aviso). NO bundle en el build.
2. Copiar/adaptar `lib/helper.dart` del vendor (MIT) → `data/helpers/supertonic_helper.dart`
   (verbatim; es el tokenizador/vocoder/ORT del ejemplo oficial).
3. **Smoke en cada target**: sintetizar una oración y reproducirla con `just_audio`.
   Mínimo obligatorio: **Android (device ARM64)** y **1 desktop** (Windows o Linux).
   iOS entra cuando haya Mac (validar que el helper NO dependa de Input/Output info).
   Valida ORT + opset + memoria. Si falla en móvil → Plan B (Kotlin + Pigeon, §9);
   en desktop no aplica Plan B (ORT desktop es directo).
4. Benchmark en 1-2 devices: RTF y RAM con un segmento de 1500 caracteres.

> **Hecho cuando** (la decisión de continuar se toma con EVIDENCIA, no por fe):
> - [ ] En Android (ARM64) y al menos 1 desktop: una oración sintetizada se escucha
>       por `just_audio`.
> - [ ] Si el helper depende de inspeccionar tensores → marcado para revisar antes
>       de iOS (no disponible en API Swift).
> - [ ] Benchmark documentado (RTF y RAM pico) para el segmento de 1500 chars.
> - [ ] Si ORT falló en móvil → Plan B activado (§9); si no, se sigue al dominio.

### Fase 3 — Dominio portado (Dart puro, con tests)

Portar §4 completo en `lib/domain/`:
- Entidad `Archivo`, contratos (§4.3), `normalizar_formatos` (§4.4),
  `limpiar_markdown` (§4.5 regex), `segmentar_texto` (§4.6), `procesar_archivo`
  (§4.7), `sintetizar_muestra` (§4.8).
- Constantes de producto (§4.1) en `constants/producto.dart`.
- **Tests**: portar los 41 casos de §7 + tests de `helper.dart`. Paridad de cobertura.
- i18n: skill `flutter-setup-localization` con las claves ES/EN de §6.5.
- **Gate**: `flutter test` verde antes de avanzar.

> **Hecho cuando**:
> - [ ] Los 41 casos de §7 portados y verdes (misma semántica que el desktop).
> - [ ] Constantes de §4.1/§4.5 exactas (verificables contra este documento, no contra memoria).
> - [ ] `test/domain/` puro: ningún import de `dart:ui`, `flutter` o plugins.
> - [ ] Tests de `helper.dart` con datos sintéticos incluidos.
> - [ ] i18n §6.5 configurado; `flutter test` + `flutter analyze` verdes.

### Fase 4 — Audio y exportación (data)

- `core/audio/wav_io.dart` (§5.2): header RIFF, append, patch de chunks.
- `ffmpeg_kit_flutter_new` (§5.3): FLAC/OGG/MP3 streaming + `duracionAudio` con ffprobe.
- `data/modelo/modelo_manager.dart`: descarga resumible (dio) + verificación.
- Reproducción con `just_audio`; `share_plus` para exportar.
- Procesamiento en `Isolate.run` con progreso vía Stream.

> **Hecho cuando**:
> - [ ] `wav_io.dart` probado: header RIFF nuevo + append que parchea `data` chunk
>       (verificar con un reproductor o leyendo el header: duración correcta).
> - [ ] Conversión FLAC/OGG/MP3 funciona por streaming en desktop (y en Android).
> - [ ] Cancelación con exportación parcial verificada (no daña salidas previas).
> - [ ] `duracionAudio` lee solo metadata; devuelve 0.0 ante error.
> - [ ] Descarga del modelo resumible verificada (cortar y retomar).

### Fase 5 — UI Flutter (presentación)

- Home: lista de `.md` (natural sort), checkboxes, botones Todo/Nada/Refrescar,
  opciones de síntesis (voz, idioma, pasos, velocidad, formatos), Escuchar,
  Procesar/Cancelar, barra de progreso, log.
- Ajustes: tema, estilo (material/neumo/skeuo), idioma, Acerca de (§6.4).
- Temas con las paletas de §6.2; persistencia con §6.3.
- Skills: `flutter-add-widget-test`, `flutter-build-responsive-layout`,
  `flutter-add-widget-preview`, `flutter-setup-declarative-routing`.

> **Hecho cuando**:
> - [ ] Paletas de §6.2 aplicadas exactas (los hex están acá, no inventar variantes).
> - [ ] Los 3 estilos (material/neumo/skeuo) y tema claro/oscuro cambiables.
> - [ ] Ajustes persisten (claves de §6.3) entre cierres de app.
> - [ ] Home funcional: lista natural sort, selección, Escuchar, Procesar/Cancelar,
>       barra de progreso y log con throttle.
> - [ ] i18n ES/EN completo (83 claves, §6.5) sin textos hardcodeados.
> - [ ] Widget tests de Home/Ajustes/Acerca de presentes.

### Fase 6 — QA y release

1. `flutter analyze` + `flutter test` + smoke en 2 devices (o device + desktop).
2. Gate de calidad (skill `judgment-day`: 2 jueces ciegos).
3. Builds por plataforma:
   - Android: `flutter build appbundle --release` (o APK).
   - Windows: `flutter build windows --release` (carpeta `build/windows/...`, zip).
   - Linux: `flutter build linux --release` (AppImage/deb con `linuxdeploy`).
   - iOS: `flutter build ipa` (requiere macOS + firma).
   **Revisar licencia GPL de ffmpeg_kit_flutter_new antes de distribuir.**
4. Distribución: Google Play (interno/cerrado), TestFlight/App Store (iOS) y
   release en GitHub (desktop).

> **Hecho cuando**:
> - [ ] `flutter analyze` 0 errores + `flutter test` verde en todas las plataformas.
> - [ ] Judgment-day aprobado (2 jueces ciegos, hallazgos confirmados corregidos).
> - [ ] Smoke manual en device real + desktop (síntesis, reproducción, cancelación).
> - [ ] Licencia GPL de ffmpeg_kit_flutter_new evaluada y documentada.
> - [ ] Builds de §6 generados y probados (appbundle/APK, bundle Windows, Linux, IPA).

---

## 9. Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| `flutter_onnxruntime` no corre en Android (solo probado en macOS por el vendor) | Media | Smoke temprano en Fase 2; Plan B Kotlin + Pigeon (solo móvil) |
| iOS: `Input/Output info` / `Model Metadata` no disponibles (API Swift) | Media | El helper NO debe depender de inspeccionar tensores (validar en Fase 2 al tener Mac) |
| `just_audio` en Windows/Linux necesita `just_audio_media_kit` | Baja | Dependencia declarada desde Fase 1; misma API `AudioPlayer` |
| `ffmpeg_kit_flutter_new` en Linux requiere `libjson-glib-dev` | Baja | Documentado en Fase 0/§3 |
| Rendimiento autoregressive en device entry-level | Media | Benchmark en device real; ajustar steps/velocidad; acotar segmento a 1500 |
| Modelo ~400 MB | Alta | Descarga en runtime resumible (dio + Range), NO bundle; avisar antes de descargar |
| FLAC/OGG/MP3 sin encoder Dart puro | Alta | `ffmpeg_kit_flutter_new` (fork mantenido; decisión tomada) — revisar GPL al publicar |
| RAM en libros grandes | Media | Volcado incremental (`wavAppend` portado) + Isolate |
| i18n/literales desactualizados en docs viejas | Resuelto | Verificado: 83 claves (no 134); 41 tests (no 43); conversión streaming (no full-load) |

**Plan B (si ORT no corre en móvil)**: plataforma nativa Kotlin con
`com.microsoft.onnxruntime:onnxruntime-android` + puente **Pigeon**/MethodChannel,
portando tokenizer + vocoder a Kotlin usando `helper.dart` como referencia. Solo
aplica a Android/iOS; en Windows/Linux ORT desktop es directo (el plugin ya lo
soporta). NO intentar parchear sobre la marcha: decidir rápido y pivote.

---

## 10. Fuentes (verificadas 2026-08-10)

- Modelo: https://huggingface.co/Supertone/supertonic-3 (OpenRAIL-M; sample code MIT)
- Repo del motor: https://github.com/supertone-inc/supertonic (dir `flutter/`, helper.dart)
- Paquete ONNX: https://pub.dev/packages/flutter_onnxruntime (1.8.3, ORT 1.23.0; CPU ✅ Android/iOS/Windows/Linux)
- Fork FFmpeg: https://pub.dev/packages/ffmpeg_kit_flutter_new (4.6.2, mantiene el FFmpegKit retirado; Android/iOS/macOS/Windows x86_64/Linux x86_64)
- Reproducción desktop: https://pub.dev/packages/just_audio_media_kit (Windows/Linux)
- Estado: https://pub.dev/packages/flutter_riverpod (3.4.2, requiere Dart ^3.12)
- ONNX Runtime: https://onnxruntime.ai
