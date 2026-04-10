# Polyglot Site Translator

Aplicación gráfica basada en Kivy para auditoría, traducción y gestión de proyectos/sitios multi-framework orientados a flujos de localización.

El objetivo del repositorio es construir una base mantenible y extensible para trabajar con:

- registro de sitios/proyectos
- configuración remota opcional por proyecto
- sincronización remota multi-transporte
- detección de framework
- procesamiento de archivos `.po/.mo`
- auditoría de código fuente y plantillas
- reporting
- servicios compartidos reutilizables entre WordPress, Django, Flask y futuros targets

## Estado actual

El repositorio está en una etapa temprana y hoy incluye principalmente:

- una base de frontend Kivy bajo `src/polyglot_site_translator/`
- navegación inicial con `ScreenManager`
- pantallas base para dashboard, proyectos, detalle, editor de proyectos, sync, audit y PO processing
- contratos de servicios para la UI
- persistencia real en TOML para settings generales de la app
- persistencia real en SQLite para `site_registry`
- configuración general de la app para definir `database_directory` y `database_filename`
- cifrado local reversible para persistir passwords remotos encriptados en SQLite
- subsistema real de conexiones remotas opcionales separado del proyecto
- catálogo discoverable de tipos de conexión remota con opción explícita "No Remote Connection"
- test de conexión estructurado para `ftp`, `ftps_explicit`, `ftps_implicit`, `sftp` y `scp`
- primera base real de sync `remote -> local` usando la configuración remota persistida del proyecto
- descarga real de archivos remotos al `local_path` con creación automática de directorios locales faltantes
- resultado tipado y controlado de sync con conteo de archivos y código de error cuando falla
- ejecución de sync en background desde Project Detail, con una ventana dedicada de progreso
- barra de progreso y log visible de comandos remotos/locales durante el sync
- migración automática de columnas heredadas `ftp_*` a una tabla relacionada de conexiones remotas
- registry real de adapters/framework detection con resultados tipados
- detección efectiva de proyectos WordPress, Django y Flask a partir de `local_path`
- auto-discovery dinámico de adapters al iniciar, sin registro manual en el runtime
- integración real del flujo principal de proyectos con `site_registry` persistido
- audit preview del runtime real enriquecido por el resultado de framework detection
- implementaciones fake/in-memory para workflows de desarrollo y dobles aislados de tests
- escenarios BDD y tests de presentación/orquestación
- documentación arquitectónica para guiar futuras iteraciones

Todavía no están implementados en forma real:

- sync `local -> remote`
- filtros de sync por adapter o por subconjuntos
- controles de sync full/selectivo en UI
- scanner de auditoría
- procesamiento real de `.po/.mo`
- reporting final

## Objetivos del proyecto

Esta aplicación busca ofrecer una shell gráfica capaz de crecer sin reescrituras grandes a medida que entren más capas reales del sistema.

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

La base actual implementa una base funcional de presentación, settings y `site_registry`, con estas piezas:

- `app.py` y `__main__.py`: entrypoints de la app gráfica
- `bootstrap.py`: wiring inicial del frontend shell
- `domain/site_registry/`: modelos tipados, errores y contratos del dominio de site registry
- `domain/remote_connections/`: modelos tipados, contratos y resultados estructurados de conexiones remotas
- `domain/sync/`: dirección de sync, archivos remotos, resultados, summaries y errores explícitos
- `domain/framework_detection/`: contratos, resultados tipados y errores explícitos para detección de framework
- `services/site_registry.py`: validación y CRUD del site registry
- `services/remote_connections.py`: validación opcional, catálogo discoverable y test de conexión
- `services/project_sync.py`: sync real `remote -> local` con resultados tipados, errores controlados y eventos de progreso
- `services/framework_detection.py`: orquestación de detección desde el registry de adapters
- `adapters/base.py`: contrato base discoverable para nuevos adapters
- `infrastructure/settings.py`: persistencia TOML de settings generales por usuario
- `infrastructure/database_location.py`: resolución del path final de SQLite desde settings
- `infrastructure/site_registry_sqlite.py`: repositorio SQLite real con schema y mapeo fila ↔ modelo
- `infrastructure/remote_connections/`: registry discoverable y providers concretos de conexión remota
- `infrastructure/remote_connections/base.py`: contrato base compartido para materialización acotada de listados remotos e iteración incremental completa
- `infrastructure/sync_local.py`: preparación del workspace local y persistencia de archivos descargados durante sync
- `infrastructure/site_secrets.py`: cifrado local de secretos persistidos del site registry
- `adapters/framework_registry.py`: registry/resolver real de adapters con descubrimiento dinámico por paquete
- `adapters/wordpress.py`, `adapters/django.py`, `adapters/flask.py`: detección framework-specific y evidencia estructurada
- `presentation/contracts.py`: contratos de servicios que consume la UI
- `presentation/view_models.py`: modelos tipados para pantallas y paneles
- `presentation/frontend_shell.py`: orquestación de navegación y estado
- `presentation/site_registry_services.py`: adapters entre el servicio real de site registry, el subsistema remoto, la detección de framework y la UI
- `presentation/fakes.py`: wiring real del runtime para settings TOML + `site_registry` SQLite; los dobles seeded de tests viven fuera de `src/`
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
- Projects / Sites List para listar proyectos persistidos en SQLite
- Project / Site Detail con lectura real del registry persistido y metadata de detección de framework
- Project Editor con combo dinámico de framework y combo dinámico de tipo de conexión remota
- acción "Test Connection" en el editor, resuelta por servicios y con resultado estructurado en pantalla
- Audit Screen con preview basado en la detección real del proyecto en vez de un conteo fijo del runtime
- Sync Screen con wiring real de `remote -> local` y resumen estructurado del resultado
- ventana de progreso de sync abierta desde Project Detail para no bloquear el hilo principal de Kivy
- Audit Screen para mostrar resultados fake de auditoría
- PO Processing Screen para mostrar resultados fake de procesamiento
- Settings generales con persistencia TOML y campos para configurar la ubicación/nombre de la base SQLite

La navegación mantiene el contexto del proyecto seleccionado. El flujo principal de create/list/detail/update y el sync `remote -> local` ya usan servicios reales para `site_registry` y el subsistema remoto; audit y PO processing siguen usando servicios fake detrás de los mismos contratos de UI.

El entrypoint gráfico por defecto (`create_kivy_app()` / `python -m polyglot_site_translator`) arranca con settings TOML y `site_registry` SQLite reales. Los bundles fake seeded quedan reservados para tests y escenarios de desarrollo controlados.
Los doubles/stubs de test para funcionalidades ya implementadas viven en soporte de tests y no forman parte del runtime productivo.

## Estructura del repositorio

```text
src/
  polyglot_site_translator/
    app.py
    __main__.py
    bootstrap.py
    domain/
      framework_detection/
      remote_connections/
      sync/
      site_registry/
    services/
      framework_detection.py
      project_sync.py
      remote_connections.py
      site_registry.py
    adapters/
      common.py
      framework_registry.py
      wordpress.py
      django.py
      flask.py
    infrastructure/
      database_location.py
      remote_connections/
      settings.py
      site_registry_sqlite.py
      site_secrets.py
      sync_local.py
    presentation/
      contracts.py
      errors.py
      fakes.py
      frontend_shell.py
      router.py
      site_registry_services.py
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
Dentro de esos settings también se persisten `database_directory`, `database_filename` y `sync_progress_log_limit`.
Ese último valor define cuántas operaciones recientes conserva en memoria y muestra la ventana de progreso del sync remoto.

La contraseña remota no se guarda en texto plano en SQLite.
Se persiste cifrada con una key local almacenada junto al config dir de la app.
Si el runtime encuentra una base heredada con columnas `ftp_*`, migra esos datos a la tabla de conexiones remotas relacionadas sin convertir el ciphertext a texto plano durante la migración.
Para SFTP/SCP, la verificación de host key queda activa por defecto. Si un host todavía no está en `known_hosts`, el sync falla de forma controlada con `unknown_ssh_host_key` y la ventana de progreso ofrece un popup explícito para confiar el host y reintentar. Esa acción solo está disponible mientras el progreso actual está fallido por host key desconocida; al confirmar y comenzar el reintento, se oculta para evitar aceptar el host otra vez durante la sincronización. Al confirmar, la app crea/carga `~/.ssh/known_hosts` y permite que Paramiko agregue la host key desconocida, equivalente al flujo TOFU de aceptar un host nuevo en `ssh`.

El flujo de sync actual usa la conexión remota persistida del proyecto para listar el contenido remoto y descargar archivos al `local_path`.
Cuando se dispara desde Project Detail, el trabajo corre en background y se abre una ventana dedicada con barra de progreso y log de comandos del transporte y del workspace local.
Ese log no crece sin límite: conserva solo las últimas `N` operaciones según `sync_progress_log_limit`, para evitar crecimiento de memoria cuando el remoto tiene árboles muy grandes.
En el subsistema remoto, la iteración completa del árbol se hace por `iter_remote_files()`. La API `list_remote_files()` queda reservada para casos acotados y materializa como máximo un conjunto seguro de archivos por llamada, para no reintroducir cargas masivas en memoria desde otro protocolo o caller.
La descarga es incremental: el sync empieza a grabar archivos locales a medida que los descubre en el árbol remoto, sin esperar a completar todo el recorrido.
Para un sync completo, el servicio abre una única sesión remota reutilizable con estado explícito y la usa para listar, descargar todos los archivos y cerrar la conexión; no reconecta por cada archivo.
En SFTP/SCP, el recorrido remoto descarga solo archivos regulares y saltea symlinks, sockets, devices u otros tipos especiales con operaciones `SFTP SKIP` en el log, para evitar fallos genéricos del servidor al intentar leer rutas que no son archivos descargables.
Si la conexión, el recorrido remoto o una descarga falla, esa misma ventana queda en estado `failed` y muestra un mensaje accionable con operación, proyecto, protocolo, host, puerto, ruta remota/local relevante y causa reportada por el transporte cuando está disponible. Los tests de conexión remota también devuelven mensajes con contexto de host, puerto, tipo de conexión, ruta remota y código estable de error, no solo el texto crudo de la librería.
Si el workspace local no existe, se crea automáticamente.
Si el remoto está vacío, el sync devuelve un resultado válido con `0` archivos descargados.
En esta etapa todavía no existe sync `local -> remote`, ni filtros por adapter, ni controles de sync selectivo/full desde la UI.

## Testing y validación

Comandos recomendados:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy src tests features/steps
.venv/bin/python -m pytest
.venv/bin/python -m behave features/presentation/frontend_shell.feature features/presentation/settings.feature features/presentation/site_registry.feature features/presentation/framework_detection.feature features/presentation/remote_connections.feature features/presentation/sync.feature
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
- no acoplar la UI directamente a infraestructura real
- no introducir cambios arquitectónicos sin actualizar documentación

## Limitaciones actuales

- la detección actual cubre WordPress, Django y Flask con heurísticas explícitas y testeables, no layouts arbitrarios
- para agregar un framework nuevo, hoy alcanza con sumar un módulo/adaptador discoverable sin tocar el wiring del runtime
- la UI consume resultados de detección ya resueltos; no expone todavía un flujo dedicado de inspección manual de evidencia
- FTP, auditoría y procesamiento `.po/.mo` siguen con servicios fake en el runtime principal

## Legacy

El directorio `legacy/` conserva código previo como referencia de migración.

Ese código:

- no forma parte de la aplicación activa
- no debe importarse desde producción
- puede servir como material de referencia para reimplementar lógica de forma modular en `src/`

## Próximos pasos naturales

La base actual está preparada para integrar en iteraciones futuras:

- servicios FTP reales
- resolver/registry de adapters
- scanner de auditoría
- servicios compartidos de PO processing
- reporting en formatos como Markdown, JSON o CSV
- ejecución en background cuando haya operaciones largas

## Licencia

MIT. Ver `LICENSE`.
