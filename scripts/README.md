# 📦 Scripts de Utilidad y Diagnóstico — Cerebro Local

## 🎯 Propósito
Este directorio y la raíz del proyecto contienen scripts auxiliares y herramientas de consola desarrolladas para diagnosticar fallos, auditar la base de datos, configurar integraciones fiscales en frío y optimizar la administración de **BULONERA ERP**.

---

## 🛠️ Scripts en el Directorio `scripts/`

*   [scripts/audit_slugs_erp.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/scripts/audit_slugs_erp.py): Audita y regenera de forma segura los slugs de productos en la base de datos, asegurando la compatibilidad de URLs y previniendo caracteres especiales que rompan el ruteo del frontend.
*   [scripts/cleanup_old_logs.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/scripts/cleanup_old_logs.py): Script de mantenimiento cron. Elimina de forma segura logs antiguos del host VPS que superen un tamaño o antigüedad límite, protegiendo el almacenamiento del servidor.
*   [scripts/list_urls.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/scripts/list_urls.py): Utilidad de desarrollo que lista e imprime por consola de forma estructurada todas las rutas (URLs) registradas en el enrutador global de Django.

---

## 🔍 Scripts de Diagnóstico en la Raíz del Proyecto

Para facilitar el desarrollo local y el debugging directo dentro del contenedor Docker sin interactuar con la UI, se crearon las siguientes herramientas de consola:

### 1. Integración Fiscal (AFIP)
*   [check_afip_config.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/check_afip_config.py): Verifica la conexión contra los servidores de AFIP y valida el estado de la clave privada y certificado PEM cargado.
*   [create_afip_config.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/create_afip_config.py): Crea de forma automatizada las instancias de `ConfiguracionARCA` requeridas en base de datos para pruebas.
*   [test_padron_debug.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/test_padron_debug.py): Ejecuta llamadas directas de prueba al Padrón impositivo de AFIP (Constancia de Inscripción A5) para verificar la respuesta del servidor.

### 2. Inventario y Costos (COGS)
*   [check_cogs_audit.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/check_cogs_audit.py): Audita y calcula el Costo de Mercadería Vendida (COGS) y el margen de ganancia histórico de los productos.
*   [diagnose_unit_cost.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/diagnose_unit_cost.py): Diagnostica inconsistencias y desvíos de precios y costos unitarios de los ítems de inventario.

### 3. APIs y Diagnóstico General
*   [debug_api.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/debug_api.py): Ejecuta peticiones de prueba simulando clientes DRF para verificar el formato de los payloads de respuesta JSON.
*   [test_api_direct.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/test_api_direct.py): Ejecuta testeos HTTP directos contra las APIs de negocio.
*   [test_imports.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/test_imports.py): Valida la integridad del proyecto verificando que todas las importaciones relativas de Python se resuelvan sin arrojar `ImportError`.

### 4. Datos y Reportes
*   [init_expenses_data.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/init_expenses_data.py): Script de inicialización de base de datos. Siembra (seeds) las categorías predefinidas de egresos operativos (OPEX) en la base de datos local.
*   [debug_export.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/debug_export.py): Diagnostica el rendimiento de los motores de generación y descarga de reportes financieros.
*   [scratch_pdf_gen.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/scratch_pdf_gen.py) y [read_pdf.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/read_pdf.py): Sandbox de pruebas para optimizar la generación de reportes y facturas en formato PDF (ReportLab / WeasyPrint).

---

## 🐳 Ejecución de Scripts (Docker)
De acuerdo a la **regla crítica del entorno Docker**, ningún script debe correr directamente en la terminal del host. Se deben ejecutar dentro del contenedor `web`:
```powershell
docker compose exec web python nombre_script.py
```
