# AGENTS.md — Guía para agentes de IA

Documentación del proyecto en `docs/`. Léela antes de modificar código, buscar información o revisar funciones.

## Puntos de entrada

| Si querés... | Empezá por |
|--------------|------------|
| Saber en qué capa vive cada cosa | `docs/architecture.md` |
| Reglas de negocio, contratos, casos de uso | `docs/domain.md` |
| Implementaciones (Supertonic, soundfile, config) | `docs/data.md` |
| CLI, GUI o self-test | `docs/presentation.md` |
| Empaquetado (.exe, instaladores) | `docs/packaging.md` |
| Mapa rápido "qué carpeta tocar" | `docs/README.md` |

## Reglas no negociables

1. **Regla de dependencia**: solo `app/main.py` importa `data/`. Si un archivo fuera de `app/data/` importa `from data...`, es un error de arquitectura.
2. `app/main.py` se ejecuta con `cwd = app/` (imports absolutos). El spec de PyInstaller usa `pathex=[SPECPATH]`.
3. **Idioma**: código, docstrings y docs en español. La UI de la GUI es bilingüe ES/EN (`TRADUCCIONES` en `presentation/gui.py`). Commits en conventional commits, sin atribución de IA.
4. No comprometas secretos ni API keys.

## Comandos útiles

```bash
# Verificar que compila
python -m py_compile app/main.py app/domain/repositories/motor_tts.py app/domain/use_cases/procesar_archivo.py app/data/config.py app/data/repositories/motor_tts.py app/data/repositories/exportador_audio.py app/presentation/cli.py app/presentation/gui.py app/presentation/self_test.py

# Verificar imports de presentación (desde app/)
python -c "from presentation.gui import AppLector; from presentation.self_test import self_test; from presentation.cli import main"

# Ayuda de la CLI (desde app/)
python main.py --cli --help

# Self-test completo (hace síntesis real; lento, descarga modelo la 1ra vez)
python main.py --self-test
```
