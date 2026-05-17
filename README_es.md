# Polyglot Site Translator

Aplicación gráfica basada en Kivy para auditoría, traducción y gestión de proyectos/sitios multi-framework orientados a flujos de localización.

La documentación en inglés se mantiene en [README.md](README.md). Todo cambio
visible para usuarios o desarrolladores debe actualizar `README.md` y
`README_es.md` en el mismo patch.

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
- mini design system Kivy con tokens centralizados de spacing, typography,
  radius, tamaños de componentes y superficies/acciones reutilizables
- localización de la UI con gettext, inglés por defecto y selector dinámico
  basado en catálogos `.po`/`.mo` empaquetados
- contratos de servicios para la UI
- persistencia real en TOML para settings generales de la app
- persistencia real en TOML para `Translation Settings`, incluyendo `default_project_locale`, `default_compile_mo`, `default_use_external_translator`, `default_use_translation_cache`, `translation_cache_path`, `default_only_fuzzy`, `default_dry_run`, `default_stats_only` y `default_report_inconsistencies` usados por nuevos proyectos
- persistencia real en SQLite para `site_registry`
- persistencia real en SQLite para reglas compartidas de sync (`global`/`framework` + `use_gitignore_rules`)
- configuración general de la app para definir `database_directory` y `database_filename`
- cifrado local reversible para persistir passwords remotos encriptados en SQLite
- subsistema real de conexiones remotas opcionales separado del proyecto
- catálogo discoverable de tipos de conexión remota con opción explícita "No Remote Connection"
- test de conexión estructurado para `ftp`, `ftps_explicit`, `ftps_implicit`, `sftp` y `scp`
- sync real bidireccional sobre la conexión remota persistida del proyecto
- descarga real `remote -> local` al `local_path` con creación automática de directorios locales faltantes
- subida real `local -> remote` con creación automática de directorios remotos faltantes
- filtros de sync definidos por adapter/framework y reutilizables por ambos sentidos
- inclusiones y exclusiones de sync específicas por framework, por ejemplo `.venv/` y `__pycache__/` para stacks Python
- preferencia persistida por proyecto para elegir entre `filtered sync` y `full sync`
- ABM general de reglas globales de sync compartidas por todos los proyectos, persistidas en SQLite
- ABM general de reglas de sync por tipo de proyecto/framework, persistidas en SQLite
- opción persistida para derivar exclusiones desde `.gitignore`
- catálogo visible en Project Editor del scope resuelto por framework para sync filtrado
- overrides persistidos por proyecto para agregar includes/excludes extra y habilitar/deshabilitar reglas individuales del catálogo
- resultado tipado y controlado de sync con conteo de archivos y código de error cuando falla
- ejecución de sync en background desde Project Detail, con una ventana dedicada de progreso
- barra de progreso y log visible de comandos remotos/locales durante el sync
- migración automática de columnas heredadas `ftp_*` a una tabla relacionada de conexiones remotas
- registry real de adapters/framework detection con resultados tipados
- detección efectiva de proyectos WordPress, Django y Flask a partir de `local_path`
- auto-discovery dinámico de adapters al iniciar, sin registro manual en el runtime
- workflow real de traducción basado en catálogos PO con descubrimiento `.po`, agrupación por familia, reutilización entre archivos/familias, caché persistente opcional de traducciones, traducción externa de faltantes y compilado `.mo`
- proveedor externo de traducción PO reutilizando el mismo loop async por hilo para evitar reiniciar el transporte HTTP en cada entrada
- acción `Translate` con popup para elegir locales y overridear en esa corrida `Compile MO Files`, `Use External Translator`, `Use Translation Cache`, `Only Fuzzy Entries`, `Dry-run`, `Stats Only` y `Report Inconsistencies`, precargado con la configuración persistida del proyecto y ejecución en background para no bloquear la UI
- barra de progreso en la pantalla de traducción basada en entradas gettext completadas para saber cuántas líneas faltantes ya se resolvieron
- la pantalla de traducción muestra además el archivo `.po` actual y el `msgid` actual para hacer trazable el avance durante ejecuciones largas
- sincronización PO con identidad gettext (`msgctxt`, `msgid`, `msgid_plural`) y soporte de plurales
- resumen visible de PO processing con métricas equivalentes al `ProcessStats` legacy: archivos/familias encontradas y procesadas, entradas totales/faltantes/fuzzy, completadas por sincronización inicial, reutilizadas desde otra variante, traducidas desde caché o proveedor, omitidas por modo sync-only, `.po` escritos, `.mo` compilados, fallos por entrada y fallos de compilación cuando aplica
- omisión explícita de tokens tipo hashtag como `#tag1` para no enviar slugs/no-text al traductor externo
- el adaptador `googletrans` trata errores HTTP/protocolo como fallos controlados de traducción para que el workflow continúe con las demás entradas
- framework detection y sync scope envuelven fallos de adapters, `.gitignore` y settings persistidos en errores tipados para que los workflows fallen de forma controlada
- los secretos remotos corruptos leídos desde SQLite se reportan como errores explícitos de persistencia en vez de dejar escapar errores de decoding
- los workflows que dependen de adapters externos endurecen sus fallos operacionales en errores tipados y mensajes controlados antes de llegar a la UI
- los proveedores remotos `ftp`, `ftps_explicit`, `ftps_implicit`, `sftp` y `scp` diferencian fallos de dependencia, transporte, listing, download, creación de directorios y upload con subtipos operacionales estables
- el proveedor externo `googletrans` diferencia fallos de configuración, transporte/protocolo y respuesta inválida bajo el contrato compartido de PO translation
- el runtime gráfico enruta errores no controlados de main thread, background threads y callbacks Kivy hacia estados visibles de la UI cuando la app puede recuperarse sin abortar
- escritura real de cambios en archivos `.po` del workspace con resultado tipado para UI
- integración real del flujo principal de proyectos con `site_registry` persistido
- validación de `default_locale` en el editor como locale simple o lista separada por comas, con persistencia normalizada sin espacios superfluos
- audit preview del runtime real enriquecido por el resultado de framework detection
- implementaciones fake/in-memory para workflows de desarrollo y dobles aislados de tests
- escenarios BDD y tests de presentación/orquestación
- selector de archivos/carpetas locales (Kivy Garden `FileBrowser`) junto a campos de ruta en el editor de proyecto y en ajustes del registro SQLite; en rutas de proyecto/carpeta el listado se limita a directorios
- fuente **Material Icons** incluida en el paquete (Apache 2.0, ver `presentation/kivy/assets/fonts/NOTICE.txt`) para iconos de UI como mostrar/ocultar contraseña sin depender de emojis o fuentes del sistema
- documentación arquitectónica para guiar futuras iteraciones

Todavía no están implementados en forma real:

- presets o perfiles más avanzados de sync selectivo por entorno/dirección
- scanner de auditoría
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
- `domain/sync/`: dirección de sync, archivos remotos/locales, resultados, summaries y errores explícitos
- `domain/sync/scope.py`: filtros tipados de sync por adapter, reglas globales, reglas por framework, catálogo de reglas resueltas, overrides persistidos por proyecto, y scopes reutilizables por ambos sentidos
- `domain/framework_detection/`: contratos, resultados tipados y errores explícitos para detección de framework
- `services/site_registry.py`: validación y CRUD del site registry
- `services/remote_connections.py`: validación opcional, catálogo discoverable y test de conexión
- `services/project_sync.py`: sync real `remote -> local` y `local -> remote` con resultados tipados, errores controlados y eventos de progreso
- `services/framework_detection.py`: orquestación de detección desde el registry de adapters
- `services/framework_sync_scope.py`: resolución explícita de filtros y exclusiones de sync por framework/adapter
- `domain/po_processing/`: modelos tipados, contratos y errores explícitos para procesamiento compartido de catálogos PO
- `services/po_processing.py`: descubrimiento, agrupación por familia y sincronización de traducciones faltantes entre variantes
- `adapters/base.py`: contrato base discoverable para nuevos adapters
- `infrastructure/settings.py`: persistencia TOML de settings generales por usuario
- `infrastructure/sync_gitignore.py`: traducción explícita de patrones soportados de `.gitignore` a exclusiones de sync
- `infrastructure/database_location.py`: resolución del path final de SQLite desde settings
- `infrastructure/site_registry_sqlite.py`: repositorio SQLite real con schema y mapeo fila ↔ modelo, incluyendo overrides persistidos de reglas de sync por proyecto
- `infrastructure/remote_connections/`: registry discoverable y providers concretos de conexión remota
- `infrastructure/remote_connections/base.py`: contrato base compartido para materialización acotada de listados remotos e iteración incremental completa
- `infrastructure/sync_local.py`: preparación del workspace local, listado de archivos fuente y persistencia de archivos descargados durante sync
- `infrastructure/po_files.py`: lectura/escritura real de archivos `.po` con `polib`
- `infrastructure/site_secrets.py`: cifrado local de secretos persistidos del site registry
- `adapters/framework_registry.py`: registry/resolver real de adapters con descubrimiento dinámico por paquete
- `adapters/wordpress.py`, `adapters/django.py`, `adapters/flask.py`: detección framework-specific y evidencia estructurada
- `presentation/contracts.py`: contratos de servicios que consume la UI
- `presentation/view_models.py`: modelos tipados para pantallas y paneles
- `presentation/ui_localization.py`: descubrimiento de catálogos gettext de
  UI, idioma activo y opciones dinámicas para el selector de idioma
- `presentation/locale/`: catálogos `.po` y `.mo` empaquetados para los
  idiomas disponibles de la interfaz
- `presentation/frontend_shell.py`: orquestación de navegación y estado
- `presentation/site_registry_services.py`: adapters entre el servicio real de site registry, el subsistema remoto, la detección de framework y la UI
- `presentation/fakes.py`: wiring real del runtime para settings TOML + `site_registry` SQLite; los dobles seeded de tests viven fuera de `src/`
- `presentation/kivy/`: app Kivy, `ScreenManager`, screens y widgets
- `presentation/kivy/design_tokens.py`: escala centralizada para spacing,
  typography, radius, elevación ligera y tamaños de componentes
- `presentation/kivy/widgets/surfaces.py`: cards, headers de sección, banners
  de estado y paneles de empty state reutilizables
- `presentation/kivy/widgets/actions.py`: intents visuales para acciones
  primarias, secundarias y destructivas
- `presentation/kivy/widgets/forms.py`: field cards reutilizables para formularios

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
- Project Editor con secciones (`General Settings`, `Translation Settings`, `Remote Connection Settings`, `Sync Settings`); la pestaña `General Settings` quedó acotada a metadatos generales (`name`, `framework`, `local_path`, `is_active`), mientras que locale, preferencias `Compile MO Files`, `Use External Translator`, `Use Translation Cache`, `Only Fuzzy Entries`, `Dry-run`, `Stats Only` y `Report Inconsistencies`, conexión remota y sync se editan solo en sus pestañas específicas. El editor mantiene el draft al cambiar de sección, usa combo dinámico de framework, combo dinámico de tipo de conexión remota, switch persistido para elegir `Use Adapter Sync Filters`, catálogo visible del scope resuelto y editor de reglas adicionales por proyecto; la contraseña remota incluye un control tipo “ojo” para mostrar u ocultar el texto mientras se edita
- acción "Test Connection" en el editor, resuelta por servicios y con resultado estructurado en pantalla; si el error es `unknown_ssh_host_key`, se ofrece el mismo popup de confianza de host key que en sync y se puede reintentar el test con TOFU en `known_hosts`
- Audit Screen con preview basado en la detección real del proyecto en vez de un conteo fijo del runtime
- Sync Screen con wiring real de `remote -> local` y `local -> remote`, con resumen estructurado del resultado
- ventana de progreso de sync abierta desde Project Detail para no bloquear el hilo principal de Kivy en ambos sentidos
- Audit Screen para mostrar resultados fake de auditoría
- Translation Screen con resumen real de archivos/familias encontradas y procesadas, entradas totales/faltantes/fuzzy, entradas completadas por sincronización inicial, entradas reutilizadas desde otra variante, entradas sincronizadas/traducidas, entradas resueltas desde caché, entradas resueltas vía proveedor, entradas omitidas por modo sync-only, archivos `.po` escritos, diferencias entre variantes e items de detalle cuando aplica, y `.mo` compilados; la acción `Translate` abre un popup previo que permite overridear locales, `Compile MO Files`, `Use External Translator`, `Use Translation Cache`, `Only Fuzzy Entries`, `Dry-run`, `Stats Only` y `Report Inconsistencies` para esa corrida
- Settings generales con persistencia TOML, una sección `Translation Settings` para configurar `default_project_locale`, `default_compile_mo`, `default_use_external_translator`, `default_use_translation_cache`, `translation_cache_path`, `default_only_fuzzy`, `default_dry_run`, `default_stats_only` y `default_report_inconsistencies`; esos defaults se heredan al crear un proyecto nuevo y luego pueden overridearse por proyecto y por corrida desde el popup de `Translate`
- El selector `UI Language` se alimenta de los catálogos gettext empaquetados
  y cambia el idioma de la interfaz sin hardcodear la lista de idiomas en
  pantallas Kivy
- Los textos visibles de la UI, incluidos summaries de workflows, evidencia de
  adapters, estados y métricas, pasan por la localización de presentación antes
  de renderizarse; los logs operativos y rutas se mantienen como salida
  diagnóstica cruda.

La navegación mantiene el contexto del proyecto seleccionado. El flujo principal de create/list/detail/update, sync bidireccional y PO processing ya usan servicios reales para `site_registry`, subsistema remoto y procesamiento de `.po`; el audit sigue usando servicios fake detrás de los mismos contratos de UI.
Cuando la preferencia `Use Adapter Sync Filters` está activa en la configuración remota persistida del proyecto, ambos sentidos de sync usan el scope resuelto por `FrameworkSyncScopeService`; cuando está desactivada, el servicio ejecuta full sync. Ese scope ahora compone reglas globales persistidas en settings, reglas persistidas por framework, reglas base del adapter, overrides persistidos por proyecto y exclusiones derivadas de `.gitignore` cuando la opción está habilitada. El Project Editor sigue mostrando el catálogo resuelto por proyecto y permite activar/desactivar reglas individuales y agregar includes/excludes adicionales persistidos por proyecto. La pantalla general de Settings ahora expone el ABM de reglas globales y por framework más el toggle `Use .gitignore Exclusions`. Si el proyecto pide sync filtrado pero no existe un scope utilizable, el sync falla de forma explícita en vez de caer en un fallback silencioso.
Si la resolución del scope falla por un adapter roto, por lectura de `.gitignore` o por persistencia/configuración compartida, el editor y el workflow de sync muestran un error controlado con mensaje explícito sin romper el runtime.
La detección de framework también envuelve fallos operacionales del registry/discovery en errores tipados, y la lectura de secretos remotos corruptos en SQLite falla con un error de persistencia explícito en vez de propagar errores crudos de base64/UTF-8.

El entrypoint gráfico por defecto (`create_kivy_app()` / `python -m polyglot_site_translator`) arranca con settings TOML y `site_registry` SQLite reales. Los bundles fake seeded quedan reservados para tests y escenarios de desarrollo controlados.
Ese entrypoint también desactiva el file logger de Kivy por defecto e instala hooks globales para convertir fallos no controlados en estados visibles del frontend cuando existe una ruta de recuperación.
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

## Validación recomendada

El workflow de calidad del repositorio debe validar explícitamente:

- `python -m ruff check .`
- `python -m ruff format --check .`
- `python -m mypy .`
- `python tests/run_docstring_audit.py`
- `python -m pytest`

El auditor de docstrings falla si cualquier clase, función o método, público o privado, queda sin
docstring estructurado de varias líneas o sin secciones relevantes (`Args:`, `Returns:`,
`Raises:`, `Attributes:`) cuando corresponden.

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
Dentro de esos settings también se persisten `default_project_locale`, `default_compile_mo`, `default_use_external_translator`, `default_use_translation_cache`, `translation_cache_path`, `default_dry_run`, `default_stats_only`, `default_report_inconsistencies`, `database_directory`, `database_filename` y `sync_progress_log_limit`.
El idioma de interfaz (`ui_language`) usa inglés por defecto y solo acepta
valores con un catálogo compilado empaquetado bajo
`src/polyglot_site_translator/presentation/locale/<idioma>/LC_MESSAGES/`.
Las reglas globales de sync, las reglas por framework y el toggle `use_gitignore_rules` ahora pueden vivir en SQLite para el runtime de sync mientras la configuración general sigue registrada en TOML.
Ese último valor define cuántas operaciones recientes conserva en memoria y muestra la ventana de progreso del sync.
Cuando la caché de traducción está habilitada, el runtime guarda entradas reutilizables en un almacén `shelve` persistente bajo `translation_cache_path`; el proyecto puede deshabilitar su uso y el popup `Translate` puede overridearlo por corrida sin cambiar la preferencia persistida.

Para agregar un idioma de UI, sumá
`presentation/locale/<codigo>/LC_MESSAGES/polyglot_site_translator.po` y su
compilado `.mo` equivalente. El selector de idioma lo mostrará
automáticamente si el `.mo` está empaquetado.

La contraseña remota no se guarda en texto plano en SQLite.
Se persiste cifrada con una key local almacenada junto al config dir de la app.
Si el runtime encuentra una base heredada con columnas `ftp_*`, migra esos datos a la tabla de conexiones remotas relacionadas sin convertir el ciphertext a texto plano durante la migración.
Para SFTP/SCP, la verificación de host key queda activa por defecto. Si un host todavía no está en `known_hosts`, el sync falla de forma controlada con `unknown_ssh_host_key` y la ventana de progreso ofrece un popup explícito para confiar el host y reintentar. El mismo diálogo compartido está disponible en el editor de proyecto cuando "Test Connection" devuelve ese código. En sync, la acción solo está disponible mientras el progreso actual está fallido por host key desconocida; al confirmar y comenzar el reintento, se oculta para evitar aceptar el host otra vez durante la sincronización. Al confirmar, la app crea/carga `~/.ssh/known_hosts` y permite que Paramiko agregue la host key desconocida, equivalente al flujo TOFU de aceptar un host nuevo en `ssh`.

El flujo de sync actual usa la conexión remota persistida del proyecto para listar/descargar el contenido remoto y también para crear directorios/subir archivos desde el árbol local.
Cuando se dispara desde Project Detail, el trabajo corre en background y se abre una ventana dedicada con barra de progreso y log de comandos del transporte y del workspace local.
Ese log no crece sin límite: conserva solo las últimas `N` operaciones según `sync_progress_log_limit`, para evitar crecimiento de memoria cuando el remoto tiene árboles muy grandes.
En el subsistema remoto, la iteración completa del árbol se hace por `iter_remote_files()`. La API `list_remote_files()` queda reservada para casos acotados y materializa como máximo un conjunto seguro de archivos por llamada, para no reintroducir cargas masivas en memoria desde otro protocolo o caller.
La descarga es incremental: el sync empieza a grabar archivos locales a medida que los descubre en el árbol remoto, sin esperar a completar todo el recorrido.
La subida local también es incremental: el servicio lista el árbol local, prepara directorios remotos faltantes y sube los archivos uno a uno sin materializar ni reconectar por cada archivo.
Para un sync completo, el servicio abre una única sesión remota reutilizable con estado explícito y la usa para listar, descargar o subir todos los archivos y cerrar la conexión; no reconecta por cada archivo.
Los adapters de framework ahora también pueden declarar filtros de sync reutilizables. WordPress expone `wp-content/languages`, `wp-content/themes` y `wp-content/plugins`; Django expone `locale`; Flask expone `translations` y `babel.cfg`.
La resolución de esos filtros no vive en la UI ni en `ProjectSyncService`: la hace `FrameworkSyncScopeService`, que devuelve un scope explícito con estados como `filtered`, `no_filters`, `framework_unresolved` o `adapter_unavailable`. Ese servicio ahora también compone reglas globales, reglas por framework persistidas en settings, overrides por proyecto y exclusiones derivadas de `.gitignore` cuando están habilitadas.
`ProjectSyncService` ya puede recibir ese scope resuelto y aplicarlo tanto a `remote -> local` como a `local -> remote`, aunque en esta etapa todavía no existe el control final en la UI para alternar entre sync full y filtrado.
En SFTP/SCP, el recorrido remoto descarga solo archivos regulares y saltea symlinks, sockets, devices u otros tipos especiales con operaciones `SFTP SKIP` en el log, para evitar fallos genéricos del servidor al intentar leer rutas que no son archivos descargables.
Si la conexión, el recorrido remoto o una descarga falla, esa misma ventana queda en estado `failed` y muestra un mensaje accionable con operación, proyecto, protocolo, host, puerto, ruta remota/local relevante y causa reportada por el transporte cuando está disponible. Los tests de conexión remota también devuelven mensajes con contexto de host, puerto, tipo de conexión, ruta remota y código estable de error, no solo el texto crudo de la librería.
Si el workspace local no existe durante `remote -> local`, se crea automáticamente.
Si el remoto está vacío, el sync devuelve un resultado válido con `0` archivos descargados.
Si el árbol local está vacío durante `local -> remote`, el sync devuelve un resultado válido con `0` archivos subidos.
En esta etapa todavía no existen controles de sync selectivo/full desde la UI.

## Testing y validación

Comandos recomendados:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy src tests features/steps
.venv/bin/python -m pytest
.venv/bin/python -m behave features/presentation/frontend_shell.feature features/presentation/settings.feature features/presentation/site_registry.feature features/presentation/framework_detection.feature features/presentation/remote_connections.feature features/presentation/sync.feature features/presentation/sync_filters.feature features/presentation/po_processing.feature
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
- introducir atributos de instancia solo en `__init__`
- usar sentencias Python `assert` solo en tests de pytest bajo `tests/`
- no introducir cambios arquitectónicos sin actualizar documentación

## Limitaciones actuales

- la detección actual cubre WordPress, Django y Flask con heurísticas explícitas y testeables, no layouts arbitrarios
- para agregar un framework nuevo, hoy alcanza con sumar un módulo/adaptador discoverable sin tocar el wiring del runtime
- la UI consume resultados de detección ya resueltos; no expone todavía un flujo dedicado de inspección manual de evidencia
- auditoría sigue con servicios fake en el runtime principal

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
