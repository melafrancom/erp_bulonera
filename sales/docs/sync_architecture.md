# 🔄 Arquitectura de Sincronización Offline (PWA)

Este documento detalla el diseño y el flujo de control del sistema de sincronización offline-first de **BULONERA ERP**, que permite a los vendedores de salón registrar operaciones sin conectividad a internet.

---

## 🏗️ Resumen del Flujo

```mermaid
sequenceDiagram
    participant PWA as Cliente PWA (Salón)
    participant API as Django REST API (SaleSyncViewSet)
    participant DB as MariaDB (erp_db)

    Note over PWA: Modo Offline
    PWA->>PWA: Crear Venta con local_id (UUID)
    Note over PWA: Volver Online
    PWA->>API: POST /api/v1/sales/sync/upload/ (Venta JSON + local_id)
    
    rect rgb(240, 248, 255)
        Note over API: Validación en Server
        API->>DB: Buscar Venta por local_id
        alt No existe (Nueva)
            API->>DB: Crear Venta + Items (Estado: synced)
            API-->>PWA: HTTP 201 Created (ID asignado + Success)
        alt Existe y coincide versión
            API-->>PWA: HTTP 200 OK (Ya sincronizado, omitir)
        alt Conflicto de versión
            API-->>PWA: HTTP 409 Conflict (Requiere resolución)
        end
    end
```

---

## 🔑 Componentes y Reglas de Negocio

### 1. Identificación Local (`local_id`)
*   **UUID v4:** Cada venta iniciada en el cliente PWA se identifica de forma única en el navegador mediante un UUID en el campo `local_id`.
*   **Evitar Duplicados:** La base de datos local de Django cuenta con un índice en `local_id` para garantizar que un reintento de subida por fallos de red no genere registros duplicados en el servidor.

### 2. Estados de Sincronización
La sincronización se rastrea en la venta mediante los siguientes campos:
*   `sync_status`:
    *   `synced`: Subida exitosa y consolidada en el servidor.
    *   `pending`: Transacción local en cola esperando conectividad.
    *   `conflict`: Datos en el servidor difieren de los locales y requieren intervención.
    *   `error`: Rechazado por reglas de validación de negocio (ej. falta CUIT válido o stock insuficiente en el servidor).
*   `sync_succeeded_at`: Marca temporal del éxito.
*   `sync_last_attempt`: Último intento realizado.
*   `sync_attempt_count`: Contador de reintentos para mitigar bucles infinitos.

### 3. Resolución de Conflictos (`/sync/resolve/`)
Cuando el servidor detecta que la venta ya existe pero ha sido modificada externamente antes de la sincronización (ej. otra terminal editó el presupuesto asociado), el endpoint `/sync/resolve/` permite al cliente resolver mediante tres estrategias:
1.  `server_wins` (Servidor manda): Se descartan los cambios locales del PWA y se sobrescriben con los datos actuales de la base de datos central.
2.  `client_wins` (Cliente manda): Se aplican los cambios locales, incrementando el número de versión y forzando la actualización en el servidor.
3.  `manual` (Resolución manual): Se presenta una vista en la UI comparando diferencias para que el operador decida.

---

## 🔒 Throttling y Seguridad
*   **SyncThrottle:** Configurado para limitar los reintentos a **50 sincronizaciones por hora** por usuario. Esto evita saturación del servidor (VPS Hostinger) ante bucles de reintento en el service worker del cliente.
*   **Autenticación:** Todo sync requiere un token válido (`TokenAuthentication`) y los permisos correspondientes de vendedor o administrador.

---

## 📝 Registro y Monitoreo (uWSGI Logs)
Los eventos de sincronización se registran en `logs/sync.log` con rotación automática (5MB, máx 3 archivos):
*   `INFO ... sync_views Sale synced successfully`: Transacción completada con éxito.
*   `WARNING ... sync_views Sync validation failed: invalid CUIT`: Rechazo por formato.
*   `ERROR ... sync_views Sync upload: Item validation error`: Excepciones de negocio graves durante la persistencia.
