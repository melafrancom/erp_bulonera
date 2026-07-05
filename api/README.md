# 📦 Módulo API — Cerebro Local

## 🎯 Propósito
El módulo `api` encapsula la infraestructura técnica global de la API REST expuesta mediante **Django REST Framework (DRF)**. No contiene modelos comerciales de base de datos; en su lugar, centraliza las políticas del sistema respecto al formato unificado de respuestas (JSON enveloping), el manejo global de excepciones y códigos de error impositivos/comerciales, la paginación estándar de registros, los middlewares de monitoreo de peticiones HTTP, y las restricciones de frecuencia de tráfico (throttling).

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   Ninguno (es infraestructura del framework).
*   **Es consumido por:**
    *   Todas las APIs de negocio expuestas en el ERP (`sales/api/`, `inventory/api/`, `bills/api/`, `payments/api/`, etc.) para dar formato consistente a sus respuestas y aplicar políticas globales de control.

## 🛠️ Componentes Clave (No-Modelos)
Al ser un módulo puramente de infraestructura, consta de los siguientes archivos de configuración global:
*   **`exceptions.py`**: Intercepta todos los errores no controlados (errores de validación, fallos de permisos, excepciones de base de datos) y los traduce a una respuesta estructurada JSON limpia y con códigos legibles.
*   **`renderers.py`**: Formatea automáticamente todas las respuestas exitosas y con error en una envoltura única (Envelope JSON).
*   **`pagination.py`**: Implementa la clase `StandardResultsSetPagination`, definiendo el tamaño de página por defecto (100 registros) y la estructura de metadatos de paginación (`count`, `next`, `previous`).
*   **`throttling.py`**: Define el control de tasa de peticiones, implementando límites específicos de PWA Offline (`SyncThrottle`) para proteger la base de datos de picos de carga.
*   **`middleware.py`**: Middleware de logging de peticiones REST para diagnóstico de endpoints.

## ⚡ Servicios y Middleware
*   `custom_exception_handler(exc, context)`: Transforma excepciones del sistema (ej. Django ValidationError o fallos de conexión) en estructuras estandarizadas de API REST, logueando en `logs/api.log` con nivel `ERROR`.
*   `StandardJSONRenderer`: Renderer que asegura que toda respuesta de DRF se devuelva con el formato de envoltura común (envelope), agregando metadatos de éxito y errores.

## 📝 Documentación de Detalle
*   [Estándares de API y Envoltura JSON](docs/api_standards.md): Estructura del payload JSON, manejo centralizado de excepciones y especificaciones técnicas de paginación.
