# Polyglot Site Translator

Aplicación gráfica basada en Kivy para auditoría, traducción y gestión de proyectos/sitios multi-framework orientados a flujos de localización.

El objetivo del repositorio es construir una base mantenible y extensible para trabajar con:

- registro de sitios/proyectos
- sincronización por FTP
- detección de framework
- procesamiento de archivos `.po/.mo`
- auditoría de código fuente y plantillas
- reporting
- servicios compartidos reutilizables entre WordPress, Django, Flask y futuros targets

## Estado actual

El repositorio está en una etapa temprana y hoy incluye principalmente:

- una base de frontend Kivy bajo `src/polyglot_site_translator/`
- navegación inicial con `ScreenManager`
- pantallas base para dashboard, proyectos, detalle, sync, audit y PO processing
- contratos de servicios para la UI
- persistencia real en TOML para settings generales de la app
- implementaciones fake/in-memory para catálogo y workflows de desarrollo
- escenarios BDD y tests de presentación/orquestación
- documentación arquitectónica para guiar futuras iteraciones

Todavía no están implementados en forma real:

- SQLite
- FTP
- adapters de frameworks
- scanner de auditoría
- procesamiento real de `.po/.mo`
- reporting final

## Objetivos del proyecto

Esta aplicación busca ofrecer una shell gráfica capaz de crecer sin reescrituras grandes cuando entren las capas reales del sistema.

El diseño apunta a:

- mantener la UI separada de la lógica de dominio e infraestructura
- permitir servicios compartidos framework-agnostic
- aislar comportamiento específico de cada framework detrás de adapters/plugins
- sostener typing estricto y testabilidad
- soportar crecimiento hacia flujos más complejos de localización y auditoría

## Arquitectura resumida

La arquitectura esperada se organiza en capas:

1. Presentación
2. Application services
3. Domain logic
4. Framework adapters / plugins
5. Infrastructure

La base actual implementa sobre todo la capa de presentación, con estas piezas:

- `app.py` y `__main__.py`: entrypoints de la app gráfica
- `bootstrap.py`: wiring inicial del frontend shell
- `infrastructure/settings.py`: persistencia TOML de settings generales por usuario
- `presentation/contracts.py`: contratos de servicios que consume la UI
- `presentation/view_models.py`: modelos tipados para pantallas y paneles
- `presentation/frontend_shell.py`: orquestación de navegación y estado
- `presentation/fakes.py`: catálogo/workflows fake y doubles de settings para desarrollo y pruebas
- `presentation/kivy/`: app Kivy, `ScreenManager`, screens y widgets
La UI no debe hablar directamente con:

- SQLite
- FTP
- scanners
- adapters concretos
- parsers `.po`
- report writers

## Funcionalidad base del frontend

La base actual del frontend incluye:

- Home / Dashboard como punto de entrada
- Projects / Sites List para listar proyectos fake/in-memory
- Project / Site Detail con acciones futuras ya modeladas
- Sync Screen para mostrar estado fake de sincronización
- Audit Screen para mostrar resultados fake de auditoría
- PO Processing Screen para mostrar resultados fake de procesamiento

La navegación mantiene el contexto del proyecto seleccionado y deja preparado el reemplazo futuro de fakes por servicios reales.

## Estructura del repositorio

```text
src/
  polyglot_site_translator/
    app.py
    __main__.py
    bootstrap.py
    presentation/
      contracts.py
      errors.py
      fakes.py
      frontend_shell.py
      router.py
      view_models.py
      kivy/
        app.py
        root.py
        screens/
        widgets/

tests/
  unit/
  integration/

features/
  presentation/
  steps/

requirements/
  base.txt
  dev.txt

legacy/
  README.md
  traducir.py
```

## Requisitos

- Python 3.12+
- entorno virtual recomendado (`venv`)
- dependencias de Kivy compatibles con tu sistema operativo

## Instalación

Crear entorno virtual e instalar dependencias:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements/dev.txt
```

En Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements/dev.txt
```

## Ejecutar la aplicación

La app gráfica puede iniciarse con:

```bash
pip install -e .
python -m polyglot_site_translator
```

O desde el entorno virtual del repositorio:

```bash
.venv/bin/pip install -e .
.venv/bin/python -m polyglot_site_translator
```

Si querés ejecutar la app local sin instalación editable, usá el launcher del repositorio:

```bash
.venv/bin/python run_app.py
```

Los settings generales se guardan en `settings.toml` dentro del directorio de configuración del usuario.
Para desarrollo o pruebas locales, podés overridear la ubicación con `POLYGLOT_SITE_TRANSLATOR_CONFIG_DIR`.

## Testing y validación

Comandos recomendados:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy src tests features/steps
.venv/bin/python -m pytest
.venv/bin/python -m behave features/presentation/frontend_shell.feature
```

El repositorio sigue un flujo obligatorio BDD + TDD:

1. definir caso de uso
2. definir criterios de aceptación
3. escribir escenarios BDD
4. escribir tests unitarios/integración
5. confirmar fallos iniciales
6. implementar lo mínimo
7. volver a validar
8. recién después refactorizar

## Documentación importante

Antes de extender el sistema conviene leer:

- `AGENTS.md`
- `STYLE.md`
- `TESTING.md`
- `ARCHITECTURE.md`
- `REPO_MAP.md`
- `ARCHITECTURE_DECISIONS.md`
- `ARCHITECTURE_GUARDRAILS.md`
- `AI_CONTEXT.md`
- `CODEBASE_ENTRYPOINTS.md`
- `DOMAIN_MAP.md`

## Estado de calidad esperado

Todo cambio relevante debe respetar:

- PEP8
- PEP257
- PEP484
- Ruff
- mypy
- pytest
- BDD + TDD
- separación estricta entre UI, servicios, dominio e infraestructura

Reglas clave:

- no usar `except Exception`
- no empujar lógica de negocio a widgets/screens
- no acoplar la UI a infraestructura real
- no introducir cambios arquitectónicos sin actualizar documentación

## Legacy

El directorio `legacy/` conserva código previo como referencia de migración.

Ese código:

- no forma parte de la aplicación activa
- no debe importarse desde producción
- puede servir como material de referencia para reimplementar lógica de forma modular en `src/`

## Próximos pasos naturales

La base actual está preparada para integrar en iteraciones futuras:

- repositorio SQLite para site registry
- servicios FTP reales
- resolver/registry de adapters
- scanner de auditoría
- servicios compartidos de PO processing
- reporting en formatos como Markdown, JSON o CSV
- ejecución en background cuando haya operaciones largas

## Licencia

MIT. Ver `LICENSE`.
