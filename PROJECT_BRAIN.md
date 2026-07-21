# 🧠 BULONERA ERP — Cerebro del Proyecto

> Archivo central de referencia. Cargado al inicio de cada sesión. Para detalles profundos, seguir los links de cada sección.

---

## 🏗️ Contexto del Proyecto
Estamos creando esta ERP en el directorio /var/www/erp/ y además tenemos una app que ya estaba construida en el servidor de Hostinger, en un directorio /var/www/bulonera/bulonera/ y que funcionaba correctamente. Ahora ambas appss son API REST y PWA.
Ambas apps, la del ERP y la de la bulonera_web, compartirán la misma 'media' en el directorio /var/www/shared/media/. Pero NO comparten la misma base de datos MariaDB ni el mismo servidor Redis. 

La base de datos de ambas apps están construida con MariaDB. La de la web se llama 'buloneraalvearDB' y el usuario es 'bulonera_user', ya tiene datos cargados. La BD del erp se llama 'erp_db' y el usuario es 'erp_user', hemos cargados 14.000 productos aprox, de PRUEBA unicamente.
Las bases de datos de ambas apps se encuentran en /var/backups/databases/:
| /var/backups/databases/buloneraalvearDB
| /var/backups/databases/erp_db


Directorio de apps:
adminbuloneraalvear@buloneraalvear:/var/www$ ls
bulonera  erp  shared

Actual en servidor:
/var/www/bulonera/web_bulonera/manage.py
/var/www/erp/src/manage.py


adminbuloneraalvear@buloneraalvear:/var/www/erp$ ls
bills  logs  media  src  static  uwsgi.production.ini

Acceso a la web actual:
https://buloneraalvear.online/   ---> cuenta con SSL
Acceso al panel de control de OpenLiteSpeed:
http://212.85.12.132:7080/

Acceso a ssh:
ssh adminbuloneraalvear@212.85.12.132

---



## 🏗️ Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Backend | Django 5.0 + Django REST Framework |
| Base de Datos | MariaDB (utf8mb4_spanish_ci) |
| Caché / Broker | Redis (django-redis) |
| Cola de Tareas | Celery + Celery Beat |
| Monitor Celery | Flower (`http://localhost:5555`) |
| Frontend | TailwindCSS v3 + Alpine.js + Lucide Icons |
| Autenticación | TokenAuthentication (PWA) + SessionAuthentication (web) |
| Infraestructura | Docker Compose (dev y producción) |
| Servidor Web (prod) | OpenLiteSpeed + uWSGI |

---

## 🐳 Entorno de Desarrollo (Docker Local)

### Contenedores

| Contenedor | Puerto | Propósito |
|---|---|---|
| `web` (bulonera_web) | `8000` | Django runserver |
| `db` (bulonera_mariadb) | `3307` | MariaDB |
| `redis` (bulonera_redis) | `6379` | Caché y broker Celery |
| `celery_worker` | — | Tareas async |
| `celery_beat` | — | Scheduler |
| `flower` | `5555` | Monitor Celery |

### Comandos Esenciales (Local)

```powershell
# Levantar todos los servicios
docker-compose up -d

# Chequear que Django está bien
docker-compose exec web python manage.py check

# Aplicar migraciones
docker-compose exec web python manage.py migrate

# Correr tests (SIEMPRE con settings de test)
docker-compose exec -e DJANGO_SETTINGS_MODULE=erp_crm_bulonera.settings.test web pytest -v

# Tests con cobertura (target > 90% en servicios)
docker-compose exec -e DJANGO_SETTINGS_MODULE=erp_crm_bulonera.settings.test web pytest --cov=. --cov-report=html --cov-report=term-missing

# Tests de una app específica
docker-compose exec -e DJANGO_SETTINGS_MODULE=erp_crm_bulonera.settings.test web pytest sales/tests/ -v
docker-compose exec -e DJANGO_SETTINGS_MODULE=erp_crm_bulonera.settings.test web pytest products/tests/test_services.py::test_name -v

# Ver logs en vivo
docker-compose logs -f web
docker-compose logs -f celery_worker
docker-compose logs celery_worker --tail=40
docker-compose logs redis --tail=40
docker-compose exec redis redis-cli ping
docker-compose exec web python manage.py check

# Shell de Django
docker-compose exec web python manage.py shell

# ############################### RESTART SERVICES ###############################
docker-compose restart web
docker-compose restart celery_beat
docker-compose restart celery_worker

# ############################### CHECK SERVICES ###############################
docker-compose ps

# ############################### CHECK DATABASE ###############################
docker-compose exec web python manage.py check --database=default
```

### Settings por Ambiente

| Ambiente | Archivo | `DJANGO_SETTINGS_MODULE` |
|---|---|---|
| Desarrollo | `local.py` | `erp_crm_bulonera.settings.local` |
| **Tests** | **`test.py`** | **`erp_crm_bulonera.settings.test`** |
| Producción | `production.py` | `erp_crm_bulonera.settings.production` |

> ⚠️ **REGLA ABSOLUTA**: Nunca ejecutar `python manage.py`, `pytest` o `pip` directamente en el host. Todo va dentro del contenedor `web`.

---

## 🚀 Producción (VPS Hostinger)

**Servidor:** `212.85.12.132` | **Usuario:** `adminbuloneraalvear` | **App:** `/var/www/erp/src`

### Flujo de Deploy

```
1. (PC local) git add . && git commit -m "..." && git push origin main
2. (VPS)      sudo deploy_erp.sh       ← pull + build + migrate + collectstatic + restart
3. (VPS)      sudo erp_status.sh       ← verificar que todo esté OK
```

### Comandos de Producción

```bash
# Deploy completo
sudo deploy_erp.sh

# Solo reiniciar (sin rebuild)
docker compose -f /var/www/erp/src/docker-compose.production.yml restart

# Ver estado de contenedores
docker compose -f /var/www/erp/src/docker-compose.production.yml ps

# Logs en tiempo real (Persistidos en host, stdout de Docker está silenciado para optimizar CPU/RAM)
tail -f /var/www/erp/logs/uwsgi_erp.log     # uWSGI (peticiones web)
tail -f /var/www/erp/logs/django_prod.log   # Django (warnings/errores)
tail -f /var/www/erp/logs/celery_worker.log # Celery Worker (tareas en segundo plano)
tail -f /var/www/erp/logs/celery_beat.log   # Celery Beat (tareas programadas)

# Migraciones manuales en producción
docker compose -f /var/www/erp/src/docker-compose.production.yml run --rm web python manage.py migrate --no-input

# Ver estado de migraciones
docker exec erp_web python manage.py showmigrations

# Collectstatic manual
docker compose -f /var/www/erp/src/docker-compose.production.yml run --rm web python manage.py collectstatic --no-input

# ############################### DIAGNÓSTICO RÁPIDO (PROD) ###############################

# Ver logs en vivo (Persistidos en host)
tail -f /var/www/erp/logs/uwsgi_erp.log
tail -f /var/www/erp/logs/django_prod.log
tail -f /var/www/erp/logs/celery_worker.log
tail -n 40 /var/www/erp/logs/celery_worker.log
docker compose -f /var/www/erp/src/docker-compose.production.yml logs --tail=40 redis

# Pings de conectividad interna
docker exec erp_redis redis-cli ping
docker exec erp_web curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/

# Chequeo de Django
docker exec erp_web python manage.py check

# Abrir shell Django en producción
docker exec -it erp_web python manage.py shell
```

### Base de Datos (Producción)

```bash
# Conectar a MariaDB
sudo mysql -u erp_user -p erp_db

# Backup manual
sudo ~/backup_databases.sh

# Ver backups existentes
ls -lh /var/backups/databases/erp_db/
```

### Seguridad (Producción)

```bash
# Ver IPs baneadas por Fail2ban
sudo fail2ban-client status django-erp | grep "Banned IP"

# Desbanear una IP
sudo fail2ban-client set django-erp unbanip <IP>

# Ver firewall
sudo ufw status numbered
```

### Infraestructura de Volúmenes Compartida (Producción)

**Configuración:** Ambas aplicaciones (ERP y Web Bulonera) ahora comparten un directorio único de media en `/var/www/shared/media/`.

#### Volúmenes Montados en `docker-compose.production.yml`

```yaml
# Servicio 'web' (uWSGI)
volumes:
  - /var/www/erp/static:/app/staticfiles       # Estáticos del ERP
  - /var/www/shared/media:/app/media           # COMPARTIDO: fotos, facturas, comprobantes
  - /var/www/erp/src/afip/certs:/app/afip/certs:ro
  - /var/www/erp/logs:/app/logs

# Servicio 'celery_worker'
volumes:
  - /var/www/erp/logs:/app/logs
  - /var/www/shared/media:/app/media           # COMPARTIDO: acceso para generar PDFs
  - /var/www/erp/src/afip/certs:/app/afip/certs:ro

# Servicio 'celery_beat'
volumes:
  - /var/www/erp/logs:/app/logs
  - /var/www/shared/media:/app/media           # COMPARTIDO: acceso de solo lectura
```

#### Dentro del Contenedor
- ERP ve archivos en `/app/media`
- Web Bulonera también accede a `/app/media`
- Django settings (`production.py`): `MEDIA_ROOT = env('MEDIA_ROOT', default='/app/media')`

#### Configuración del Host
Asegurar que el directorio exista y tenga los permisos correctos:

```bash
# Crear directorio si no existe
sudo mkdir -p /var/www/shared/media

# Establecer permisos
sudo chown -R www-data:www-data /var/www/shared/media
sudo chmod 755 /var/www/shared/media

# Verificar permisos (web debe escribir aquí)
ls -ld /var/www/shared/media
```

#### Migración de Datos (One-time)
Si había datos en `/var/www/erp/media` o `/var/www/bulonera/bulonera/media`, migrar a la nueva ubicación:

```bash
# Consolidar media antiguo de ambos directorios
sudo cp -r /var/www/erp/media/* /var/www/shared/media/
sudo cp -r /var/www/bulonera/bulonera/media/* /var/www/shared/media/

# Verificar que todo se copió
ls -lh /var/www/shared/media/
```

### OpenLiteSpeed

```bash
# Reiniciar OLS
sudo /usr/local/lsws/bin/lswsctrl restart

# Ver logs de errores
sudo tail -f /usr/local/lsws/logs/error.log
```

---

## 🧪 Testing Strategy (Fase 5)

### Arquitectura de Pruebas por Capas

```
{app}/tests/
├── __init__.py
├── conftest.py         ← Fixtures específicos de la app
├── factories.py        ← FactoryBoy factories para modelos
├── test_models.py      ← Validaciones de modelos y BaseModel
├── test_services.py    ← CRÍTICO: Lógica de negocio (AAA pattern)
├── test_api.py         ← Endpoints REST: HTTP codes, permisos
└── test_web.py         ← Rendimiento de templates Django
```

### Fixtures Globales (`/tests/conftest.py`)

```python
@pytest.fixture
def authenticated_user(db):
    """Usuario autenticado para tests de API."""
    return User.objects.create_user('test@example.com', 'password')

@pytest.fixture
def authenticated_admin(db):
    """Admin autenticado con todos los permisos."""
    user = User.objects.create_superuser('admin@example.com', 'password')
    return user

@pytest.fixture
def api_client():
    """DRF APIClient con autenticación."""
    client = APIClient()
    user = User.objects.create_user('api@example.com', 'password')
    client.force_authenticate(user=user)
    return client

@pytest.fixture
def client():
    """Django test client."""
    return Client()
```

### Pruebas de Servicios (AAA Pattern)

```python
# test_services.py - Ejemplo
class TestQuoteService:
    
    def test_create_quote_success(self, db):
        # Arrange
        customer = CustomerFactory(name='Acme')
        data = {'customer': customer, 'items': []}
        
        # Act
        quote = QuoteService.create(data)
        
        # Assert
        assert quote.id is not None
        assert quote.status == Quote.Status.DRAFT
    
    def test_create_quote_invalid_customer(self, db):
        # Arrange
        data = {'customer': None, 'items': []}
        
        # Act & Assert
        with pytest.raises(InvalidQuote):
            QuoteService.create(data)
    
    def test_confirm_quote_insufficient_items(self, db):
        # Arrange
        quote = QuoteFactory(items=[])
        
        # Act & Assert
        with pytest.raises(QuoteError):
            QuoteService.confirm(quote)
```

### Cobertura Mínima

| Capa | Target | Prioridad |
|---|---|---|
| Services | **> 90%** | CRÍTICA |
| API ViewSets | > 80% | Alta |
| Models (clean) | > 70% | Media |
| Web Views | > 60% | Baja |

### Ejecución en CI/CD

```yaml
# .github/workflows/test.yml (ejemplo)
script:
  - docker-compose exec -e DJANGO_SETTINGS_MODULE=erp_crm_bulonera.settings.test web pytest --cov --cov-report=xml
  - docker-compose exec -e DJANGO_SETTINGS_MODULE=erp_crm_bulonera.settings.test web pytest --cov-fail-under=90 sales/tests/
```

---

## 🎨 Design System (The Bulonera Pattern)

> **📖 Single Source of Truth:** Ver [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) para arquitectura completa de UI.

### Colores Base (Light/Dark)

| Elemento | Light | Dark |
|---|---|---|
| Fondo Principal | `bg-white` | `dark:bg-slate-950` |
| Fondo Secundario | `bg-slate-50` | `dark:bg-slate-900` |
| Texto Primario | `text-slate-900` | `dark:text-slate-50` |
| Texto Secundario | `text-slate-600` | `dark:text-slate-400` |
| Border | `border-slate-200` | `dark:border-slate-700/50` |

### Componentes Estándar

```html
<!-- Card Universal (Light + Dark) -->
<div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700/50 rounded-lg p-4 shadow-sm dark:shadow-slate-900/50">
  <h3 class="text-lg font-bold text-slate-900 dark:text-slate-50">Título</h3>
  <p class="text-sm text-slate-600 dark:text-slate-400 mt-2">Descripción</p>
</div>

<!-- Badge -->
<span class="px-2 py-1 text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded">Status</span>

<!-- Button Primary -->
<button class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-500">
  Acción
</button>
```

### Dark Mode - Detección Automática

```javascript
// En base.html <head> - detecta y aplica tema
if (localStorage.getItem('theme') === 'dark' ||
    (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
  document.documentElement.classList.add('dark');
}
```

### Reglas de Tailwind

✅ **DO:**
```html
<!-- Siempre ambos modos -->
<div class="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-50">
```

❌ **DON'T:**
```html
<!-- Estilos inline -->
<div style="background: #f8fafc; padding: 1rem;">❌</div>

<!-- Solo dark sin light -->
<div class="dark:bg-slate-900">❌</div>
```

---

## 📦 Apps Activas

| App | Propósito |
|---|---|
| [`core`](core/README.md) | Modelos base (BaseModel, soft-delete, audit) |
| [`common`](common/README.md) | Middleware, excepciones, permisos globales |
| `products` | Catálogo de productos |
| [`sales`](sales/README.md) | Ventas y presupuestos (con sync PWA offline) |
| [`customers`](customers/README.md) | Clientes y Cuentas Corrientes (modalidades formal/informal, pre-check de crédito, refacturación y aging) |
| [`suppliers`](suppliers/README.md) | Proveedores |
| [`inventory`](inventory/README.md) | Stock y movimientos |
| [`payments`](payments/README.md) | Pagos y asignaciones |
| [`bills`](bills/README.md) | Facturación |
| [`expenses`](expenses/README.md) | Gastos operativos (OPEX) y clasificación en P&L |
| [`afip`](afip/README.md) | Integración fiscal Argentina (AFIP/ARCA) |
| [`reports`](reports/README.md) | Dashboard y reportes |
| [`api`](api/README.md) | Configuración central de la API REST |
| [`erp_crm_bulonera`](erp_crm_bulonera/README.md) | Configuración raíz del proyecto y Celery |
| [`templates`](templates/README.md) | UI: Plantillas HTML, Tailwind y Alpine.js |
| [`deployment`](deployment/README.md) | Configuración de Docker, uWSGI y Entorno de Producción |
| [`scripts`](scripts/README.md) | Scripts de mantenimiento, auditoría y diagnóstico |
| [`tmp`](tmp/README.md) | Espacio temporal de pruebas y scratch scripts (excluido de Git) |
| [`.agents`](.agents/README.md) | Habilidades, reglas de estilo y workflows de Agentes de IA |

---

## 🗺️ Arquitectura de URLs

### Web (Templates HTML)
```
GET /sales/           → sales/web/views/
GET /products/        → products/web/views/
GET /bills/           → bills/web/views/
GET /inventory/       → inventory/web/views/
GET /payments/        → payments/web/views/
GET /reports/         → reports/web/views/
GET /expenses/        → expenses/web/views/
GET /customers/       → customers/web/views/
GET /suppliers/       → suppliers/web/views/
GET /afip/            → afip/web/views/
```

### API REST (JSON/DRF)
```
/api/v1/sales/quotes/       → QuoteViewSet
/api/v1/sales/sales/        → SaleViewSet
/api/v1/sales/sync/         → SaleSyncViewSet
/api/v1/products/products/  → ProductViewSet
/api/v1/bills/bills/        → BillViewSet
/api/v1/inventory/stocks/   → StockViewSet
/api/v1/payments/payments/  → PaymentViewSet
/api/v1/expenses/expenses/  → ExpenseViewSet
/api/v1/expenses/categories/ → ExpenseCategoryViewSet
/api/v1/customers/          → CustomerViewSet
/api/v1/suppliers/          → SupplierViewSet
```

---

## 📐 Convenciones de Arquitectura

### Estructura de App (Canónica)
```
{app}/
├── models.py          ← Modelos Django
├── services.py        ← Lógica de negocio (TODO va aquí)
├── admin.py
├── signals.py
├── tasks.py           ← Tareas Celery
├── migrations/
├── api/
│   ├── serializers.py
│   ├── views/views.py ← ViewSets (AuditMixin + ModulePermission + IsAuthenticated)
│   └── urls/urls.py   ← Router DRF
├── web/
│   ├── views/views.py ← Vistas Django tradicionales
│   └── urls/urls.py
└── tests/
    ├── test_models.py
    ├── test_services.py  ← CRÍTICO
    ├── test_api.py
    └── test_web.py
```

### Reglas Fundamentales
- **Lógica SOLO en `services.py`** — las vistas sólo rutean y validan el request
- **Tests separados por capa** — nunca un `tests.py` monolítico
- **Serializers en `api/serializers.py`** — nunca inline en las vistas
- **`__init__.py` exporta** símbolos explícitamente con `__all__`
- **Migraciones siempre antes de deploy** — nunca pushear código con modelos sin migrar
- **TailwindCSS + Alpine.js + Lucide** — stack frontend inamovible
- **No escribir CSS raw** — todo a través de clases Tailwind

---

## 🤖 Estrategia de IA (Model Routing)

### El Arquitecto (Modelos de Razonamiento Profundo)
*Cuándo:* Features grandes, decisiones de arquitectura, diseño de módulos nuevos.
```
"Adopta el rol de Arquitecto. Lee la app `{nombre}` y genera un
implementation_plan.md usando la skill `django-canonical`. NO ESCRIBAS CÓDIGO TODAVÍA."
```
Añadir `Ultrathink` al final para forzar razonamiento paso a paso.

### El Ejecutor (Modelos Veloces)
*Cuándo:* Después de que el plan está aprobado, en el 80% del día a día.
```
"Lee el implementation_plan.md. Entra en modo ejecución. Resuelve el paso 1.
Usa las skills `template-standardization` y `verification-before-completion`."
```

### Modificadores de Prompt Avanzados

| Modificador | Cuándo usar |
|---|---|
| `"Busca documentación reciente en internet antes de implementar"` | Librerías de terceros, APIs externas, versiones nuevas |
| `"Usa subagentes para esta tarea"` | Tareas paralelizables (ej: programar vista + validar en browser) |
| `"Diseño Anti-Slop: Spatial Composition asimétrica, micro-interacciones sutiles"` | Dashboards nuevos, portales, pantallas de login |

---

## 🔍 Descubrimiento Semántico y Grafos de Conocimiento (MCP & Obsidian)

Este proyecto utiliza un ecosistema híbrido de grafos de conocimiento y documentación estructurada para acelerar el desarrollo y mantener un contexto alineado con las reglas de negocio:

### 1. Codebase Memory Graph (`codebase-memory-mcp`)
Analiza la estructura física y sintáctica del código Python/Django (AST). 
*   **Cuándo usar:** Exploración técnica, trazabilidad de llamadas de métodos (`trace_path`), ubicación de clases y extracción rápida de snippets de código (`get_code_snippet`).
*   **Prioridad:** Siempre prefiere las herramientas de `codebase-memory-mcp` (`search_graph`, `trace_path`, `get_code_snippet`) sobre búsquedas planas (`grep_search` / `glob`) para exploración de código.

### 2. Semantic Context Graph (`Graphify MCP`)
Conecta semánticamente el código fuente con la documentación comercial de Obsidian y los layouts visuales.
*   **Archivo del Grafo:** [`graphify-out/graph.json`](file:///c:/Users/frank/Desktop/BULONERA_ERP/graphify-out/graph.json) (Contiene 400+ comunidades semánticas).
*   **Herramientas MCP:** `query_graph`, `find_path` (para buscar la ruta más corta entre conceptos, ej. de una vista al archivo Markdown de negocio), `get_neighbors`.
*   **Mantenimiento (Host Windows):** Para regenerar el grafo tras cambios importantes en el código o documentación, ejecutar en PowerShell:
    ```powershell
    $env:GEMINI_API_KEY="tu_clave_de_api"
    graphify .
    ```

### 3. Segundo Cerebro de Negocio (Obsidian)
Estructura de documentación distribuida por módulos para entender el **por qué** y el **cómo** de las decisiones comerciales:
*   **Estructura:** Cada módulo posee su `README.md` (Cerebro Local) y notas atómicas en su carpeta `docs/` vinculadas mediante enlaces Markdown relativos.
*   **Uso en Agentes:** Antes de escribir código para solucionar un requerimiento impositivo o comercial, la IA debe consultar el `README.md` del módulo correspondiente en Obsidian para alinear el diseño con las directrices del negocio.

### Cuándo volver a grep / búsquedas de archivos:
- Al buscar constantes literales específicas, mensajes de error literales de logs, o configuraciones de strings.
- Al explorar archivos de configuración plana no estructurados (Dockerfiles, `.env`, configs de uWSGI).
- Cuando los grafos de conocimiento (MCP) retornen resultados insuficientes..

---

## 🛠️ Skills Disponibles

| Skill | Trigger Natural |
|---|---|
| `agent-core-rules` | Siempre activa — comportamiento base |
| `docker-environment` | Cualquier comando de ejecución/test |
| `django-canonical` | Crear o refactorizar una app Django |
| `template-standardization` | Crear o editar archivos en `templates/` |
| `design-quality` | Crear o editar templates HTML del ERP, validación visual anti-slop |
| `test-standardization` | Crear o editar archivos en `tests/` |
| `tech-lead-advisor` | Debate de arquitectura o decisiones de diseño |
| `prompt-engineering` | Automatización de roles y prompts XML |
| `verification-before-completion` | Antes de declarar cualquier tarea terminada |
| `skill-creator` | Crear una nueva skill para el proyecto |
| `feature-rollout` | Al terminar de escribir el código de una nueva feature |

---

## 📚 Documentación Detallada

| Documento | Contenido |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Arquitectura completa del módulo Sales (modelos, API, PWA) |
| [DATABASE_ARCHITECTURE.md](DATABASE_ARCHITECTURE.md) | Flujos transaccionales, decisiones e ingeniería inversa de Base de Datos ([HTML](DATABASE_ARCHITECTURE.html)) |
| [FULL_DATABASE_ER_DIAGRAM.md](FULL_DATABASE_ER_DIAGRAM.md) | Diagrama Entidad-Relación (Mermaid) completo y exhaustivo de la base de datos ([HTML](FULL_DATABASE_ER_DIAGRAM.html)) |
| [DATABASE_ARCHITECTURE.md](DATABASE_ARCHITECTURE.md) | Flujos transaccionales, decisiones e ingeniería inversa de Base de Datos ([HTML](DATABASE_ARCHITECTURE.html)) |
| [FULL_DATABASE_ER_DIAGRAM.md](FULL_DATABASE_ER_DIAGRAM.md) | Diagrama Entidad-Relación (Mermaid) completo y exhaustivo de la base de datos ([HTML](FULL_DATABASE_ER_DIAGRAM.html)) |
| [API_STRUCTURE.md](API_STRUCTURE.md) | Todos los endpoints REST documentados |
| [REQUEST_FLOW.md](REQUEST_FLOW.md) | Flujo de request end-to-end |
| [ARCHITECTURE_VIEWS.md](ARCHITECTURE_VIEWS.md) | Separación Web vs API explicada |
| [ROLES_Y_PROMPTS.md](ROLES_Y_PROMPTS.md) | Framework de Prompts y Roles (XML) |
| [VALIDATION_CHECKLIST.md](VALIDATION_CHECKLIST.md) | Checklist de QA antes de mergear |
| [PWA-IMPLEMENTATION.md](PWA-IMPLEMENTATION.md) | Implementación PWA offline-first |
| [script_creados.md](script_creados.md) | Historial de scripts de infraestructura creados |
| [PRODUCTION_DEPLOY_STEPS.md](PRODUCTION_DEPLOY_STEPS.md) | Pasos de sincronización y despliegue en producción |
| [.agents/workflows/feature-rollout.md](.agents/workflows/feature-rollout.md) | Protocolo de E2E y Monitoreo post-lanzamiento |

---

*Última actualización: Julio 2026*
