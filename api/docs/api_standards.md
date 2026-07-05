# 📡 Estándares de API y Envoltura JSON

Este documento detalla los estándares técnicos aplicados a la API REST de **BULONERA ERP** para garantizar la interoperabilidad, consistencia en el manejo de errores y rendimiento móvil (PWA offline).

---

## ✉️ Envoltura de Respuesta JSON (Envelope Standard)

Toda respuesta emitida por los endpoints REST del ERP se envuelve en una estructura común formateada por el renderer personalizado `StandardJSONRenderer` (definido en [api/renderers.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/api/renderers.py)):

### 1. Respuesta Exitosa (Success Payload)
```json
{
  "success": true,
  "data": {
    "id": 42,
    "number": "0001-00001234",
    "total": "5400.00"
  },
  "errors": []
}
```
*   **`success`:** Booleano que indica el resultado de la operación.
*   **`data`:** El payload solicitado (objeto o arreglo JSON).
*   **`errors`:** Arreglo vacío.

### 2. Respuesta de Error (Error Payload)
```json
{
  "success": false,
  "data": null,
  "errors": [
    {
      "code": "validation_error",
      "message": "Este campo es requerido.",
      "field": "customer_id"
    }
  ]
}
```
*   **`success`:** `false`.
*   **`data`:** `null`.
*   **`errors`:** Lista de objetos con detalle del fallo:
    *   `code`: Código string estandarizado para traducción en frontend (ej. `validation_error`, `permission_denied`, `afip_error`).
    *   `message`: Explicación legible.
    *   `field`: Nombre del campo de entrada afectado (opcional, útil para validaciones de formulario).

---

## 🛡️ Manejador Global de Excepciones

El manejador `custom_exception_handler` ([api/exceptions.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/api/exceptions.py)) intercepta todas las excepciones y las traduce:

1.  **Excepciones de validación de DRF:** Convierte los errores de los serializadores en el arreglo `errors` con el código `validation_error`.
2.  **Excepciones de Permisos e Inexistencias:** Traduce HTTP 403 a `permission_denied` y HTTP 404 a `not_found`.
3.  **Errores de AFIP/ARCA:** Captura fallos de conectividad SOAP o denegaciones del Web Service, catalogándolos con el código `afip_error` para que el cliente PWA sepa que el problema es del servidor fiscal y no del ERP local.
4.  **Excepciones no controladas (HTTP 500):** Envía la traza detallada del error a `logs/django_prod.log` y retorna un error genérico imprevisto protegiendo la seguridad de los datos de la infraestructura.

---

## 📊 Estándar de Paginación

Para optimizar el uso de red y memoria (especialmente en Hostinger VPS), las listas grandes utilizan paginación:

*   **Clase:** `StandardResultsSetPagination` ([api/pagination.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/api/pagination.py)).
*   **Tamaño por defecto:** **100 registros** por página.
*   **Estructura de datos paginados (dentro de `data`):**
    ```json
    {
      "success": true,
      "data": {
        "count": 1450,
        "next": "http://localhost:8000/api/v1/sales/sales/?page=2",
        "previous": null,
        "results": [ ... ]
      },
      "errors": []
    }
    ```

---

## 🚦 Control de Frecuencia (Throttling)

*   **`SyncThrottle`:** Throttling especializado para sincronización offline-first de salón. Limita la subida de ventas offline a un máximo de **50 peticiones por hora** por usuario.
*   **Comportamiento de rechazo:** Si el cliente excede la tasa, el sistema responde con HTTP 429 Too Many Requests y el payload:
    ```json
    {
      "success": false,
      "data": null,
      "errors": [
        {
          "code": "throttled",
          "message": "Límite de solicitudes excedido. Intente nuevamente en 72 segundos."
        }
      ]
    }
    ```
