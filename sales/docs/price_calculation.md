# 📐 Cálculo Bidireccional de Precios (Modo Mostrador)

Este documento detalla el mecanismo matemático que permite a los vendedores de salón de **Bulonera Alvear** cotizar productos de forma flexible en el mostrador. Soporta el ingreso del precio unitario para obtener el total, o el ingreso de un total objetivo para deducir automáticamente el precio unitario neto antes de impuestos y descuentos.

---

## 🎯 Caso de Uso en Negocio

1.  **Venta por Unidad de Medida (UOM):** Tornillos o tuercas que se venden en volumen o peso (ej. kilos). El vendedor indica la cantidad y el precio por unidad, calculando el total automáticamente.
2.  **Ajuste por Presupuesto del Cliente:** El cliente indica que tiene un presupuesto exacto (ej. `$5000` finales). El vendedor ingresa `$5000` como "Total Objetivo" y el sistema deduce el precio unitario del artículo para que el total (incluyendo IVA y descuentos) dé exactamente `$5000`.

---

## 🧮 Modelos Matemáticos de Cálculo

Cada ítem de la venta (`SaleItem` o `QuoteItem`) implementa el método `smart_recalculate()` que opera según el campo `calculation_mode`:

### Modo 1: `price_to_total` (Precio → Total)
El total final se calcula progresivamente desde el precio unitario:
$$\text{Subtotal Base} = \text{precio\_unitario} \times \text{cantidad}$$
$$\text{Subtotal con Descuento} = \text{Subtotal Base} - \text{monto\_descuento}$$
$$\text{Total} = \text{Subtotal con Descuento} \times \left(1 + \frac{\text{alicuota\_iva}}{100}\right)$$

### Modo 2: `total_to_price` (Total Objetivo → Precio)
El sistema ejecuta el cálculo inverso para deducir el `unit_price` a partir del `target_total`. 
El flujo de cálculo inverso implementado en [SaleItem._calculate_unit_price_from_total](file:///c:/Users/frank/Desktop/BULONERA_ERP/sales/models.py#L196-L217) sigue estos pasos:

1.  **Reversión del Impuesto (IVA):**
    $$\text{Subtotal antes de IVA} = \frac{\text{target\_total}}{1 + \frac{\text{alicuota\_iva}}{100}}$$
2.  **Reversión del Descuento:**
    *   Si el descuento es porcentual (`discount_type='percentage'`):
        $$\text{Subtotal antes de Descuento} = \frac{\text{Subtotal antes de IVA}}{1 - \frac{\text{valor\_descuento}}{100}}$$
    *   Si el descuento es de monto fijo (`discount_type='fixed'`):
        $$\text{Subtotal antes de Descuento} = \text{Subtotal antes de IVA} + \text{valor\_descuento}$$
3.  **Deducción del Precio Unitario:**
    $$\text{precio\_unitario} = \frac{\text{Subtotal antes de Descuento}}{\text{cantidad}}$$

---

## 🛑 Validaciones Críticas (`clean()`)

Para evitar inconsistencias en la base de datos de MariaDB y errores en ARCA/AFIP:
*   **Cantidad Positiva:** Se requiere que `cantidad > 0`. No es posible cotizar cantidades nulas o negativas.
*   **Precio Unitario Límite:** El `precio_unitario` resultante de la reversión no puede ser negativo ni menor a `$0.00`.
*   **Límite de Descuento:** Un descuento porcentual no puede ser mayor o igual a `100%`, ya que produciría una división por cero en la reversión.
*   **Transabilidad de Totales:** En el modo `total_to_price`, el campo `target_total` es obligatorio.
