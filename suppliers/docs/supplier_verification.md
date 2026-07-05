# 🔍 Validaciones de Proveedores y Protección de CUIT

Este documento detalla los controles y validaciones estructurales aplicados a los proveedores de **BULONERA ERP** para asegurar la calidad de la base de datos fiscal y bancaria.

---

## ⚖️ Restricciones y Unicidad del CUIT

El campo `cuit` en el modelo `Supplier` representa la identificación tributaria argentina única del proveedor. Se aplican las siguientes reglas:

1.  **Validación de Formato:** El CUIT se valida mediante la expresión regular `^\d{2}-\d{8}-\d{1}$` (ej. `20-18054557-4`), requiriendo los guiones correspondientes.
2.  **Checksum Modulus 11:** Al igual que con los clientes, se evalúa que el dígito verificador final sea correcto.
3.  **Unicidad Condicional (`UniqueConstraint`):**
    Para permitir proveedores informales o en proceso de registro que aún no poseen CUIT cargado, la base de datos permite valores nulos o vacíos. Sin embargo, si el CUIT está presente, debe ser estrictamente único. Esto se logra mediante la restricción de Django en [Supplier.Meta](file:///c:/Users/frank/Desktop/BULONERA_ERP/suppliers/models.py#L238-L244):
    ```python
    models.UniqueConstraint(
        fields=['cuit'],
        condition=~models.Q(cuit=None) & ~models.Q(cuit=''),
        name='unique_supplier_cuit_if_not_null'
    )
    ```

---

## 🔄 Liberación de CUIT en Eliminación Lógica

Para permitir registrar nuevamente a un proveedor que fue archivado (eliminado lógicamente), el método `delete()` de `Supplier` aplica un comportamiento de liberación impositiva (mangling):

*   Al borrar al proveedor, si posee CUIT, se le antepone el prefijo `__deleted_<id>_` (ej. `20-12345678-9` pasa a ser `__deleted_42_20-12345678-9`).
*   Esto libera el CUIT original, permitiendo volver a dar de alta al proveedor sin conflictos de base de datos.
*   El mismo patrón se aplica en `SupplierTag` con los campos `name` y `slug`.

---

## 🏦 Datos Bancarios y Plazos de Pago

*   **Clave Bancaria Uniforme (CBU):** Se valida que el CBU ingresado consista de una cadena de exactamente **22 dígitos numéricos**.
*   **Alias Bancario:** Permite un alias alfanumérico para agilizar las transferencias en mostrador.
*   **Día de Pago (`payment_day_of_month`):** Se restringe estrictamente entre el día **1 y 28** del mes para evitar errores en meses cortos (como Febrero) y garantizar el cálculo atómico de plazos de pago.
*   **Descuento Pronto Pago (`early_payment_discount`):** Porcentaje comercial de descuento si se abona antes de la fecha límite (se valida que sea $\ge 0.00\%$).
