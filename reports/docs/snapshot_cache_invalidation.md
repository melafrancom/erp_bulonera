# ⏱️ Estrategia de Caché e Invalidación de Snapshots

Este documento detalla el ciclo de vida del caché financiero (`FinancialSnapshot`) en **BULONERA ERP**, explicando la arquitectura de invalidación reactiva por Signals y la reconstrucción en segundo plano con Celery.

---

## 🏗️ Ciclo de Vida del Reporte Financiero

Calcular reportes agregados como el P&L (Pérdidas y Ganancias) o el Cash Flow mensual exige escanear miles de transacciones de ventas, ítems, alocaciones de pagos y gastos operativos en la base de datos de MariaDB. Para asegurar tiempos de respuesta menores a 100ms en la API, el sistema implementa una caché persistente en base de datos:

```
  Solicitud GET /api/v1/reports/pnl/
                  │
                  ▼
      Buscar FinancialSnapshot
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
   ¿Existe y fresh?     ¿No existe o is_stale=True?
        │                   │
        │ Sí                │ No
        ▼                   ▼
   Retornar JSON       Calcular on-the-fly (Services)
   desde snapshot      │
                       ├────────────────────────┐
                       ▼                        ▼
                  Retornar JSON           Guardar/Actualizar
                   al cliente             FinancialSnapshot
                                          (is_stale=False)
```

Un snapshot se considera fresco (`is_fresh()`) si cumple con dos condiciones:
1.  **Falta de obsolescencia:** El flag `is_stale` debe ser `False`.
2.  **Límite de edad:** La marca `generated_at` debe ser menor a **1 hora** (evitando servir datos excesivamente viejos incluso si no hubo modificaciones).

---

## ⚡ Invalidación Reactiva por Signals

Cuando ocurre una transacción comercial, de tesorería o de gastos, los datos de períodos anteriores cambian (ej. se registra un pago para una factura del mes pasado). El sistema intercepta estas escrituras mediante Django Signals ([reports/signals.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/reports/signals.py)):

*   **Modelos Observados:**
    *   `sales.Sale` (mutación de montos confirmados).
    *   `bills.Invoice` (facturación impositiva y Notas de Crédito).
    *   `payments.Payment` / `payments.PaymentAllocation` (ingresos de caja).
    *   `expenses.Expense` (egresos de OPEX).
*   **Lógica de Inactivación:**
    Al crearse o editarse cualquiera de estas entidades:
    1.  Se extrae el año y mes contable del registro afectado.
    2.  Se localizan los snapshots correspondientes a ese período (`pnl_monthly` y `cashflow_monthly`).
    3.  Se actualiza masivamente el campo `is_stale = True`.
    4.  El próximo operador que pida el reporte de ese mes disparará la regeneración automática de datos.

---

## 🐳 Regeneración Programada (Celery Beat)

Para evitar que los usuarios experimenten esperas por cálculos en caliente (on-the-fly) al iniciar la jornada comercial, Celery Beat tiene configurada una tarea cron programada:

*   **Horario:** Todos los días a las **02:00 AM** (hora de menor tráfico en el servidor).
*   **Tarea:** `reports.tasks.regenerate_stale_snapshots`
*   **Comportamiento:**
    1.  Busca todos los registros de `FinancialSnapshot` marcados como obsoletos (`is_stale=True`).
    2.  Invoca a `PNLService` y `CashFlowService` para reconstruir los reportes.
    3.  Actualiza el payload JSON en `data`, guarda la marca de tiempo `generated_at` y establece `is_stale=False`.
    4.  Pre-calienta la caché de los últimos 3 meses del año en curso para asegurar respuestas instantáneas.
