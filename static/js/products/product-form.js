/**
 * product-form.js
 * 
 * Cálculos en tiempo real para el formulario de creación/edición de productos.
 * - Precio de venta con IVA
 * - Porcentaje de ganancia (costo vs venta)
 * 
 * Dependencias: Ninguna (Vanilla JS)
 */

document.addEventListener('DOMContentLoaded', function () {

  // Referencias a inputs
  const costInput = document.getElementById('id_cost');
  const priceInput = document.getElementById('id_price');
  const taxRateSelect = document.getElementById('id_tax_rate');

  // Referencias a displays de cálculo
  const priceWithTaxDisplay = document.getElementById('calc-price-with-tax');
  const profitDisplay = document.getElementById('calc-profit');

  if (!costInput || !priceInput || !taxRateSelect) return;

  /**
   * Calcula y muestra el precio con IVA y el % de ganancia.
   */
  function recalculate() {
    const cost = parseFloat(costInput.value) || 0;
    const price = parseFloat(priceInput.value) || 0;
    const taxRate = parseFloat(taxRateSelect.value) || 0;

    // Precio con IVA
    const priceWithTax = price * (1 + taxRate / 100);
    priceWithTaxDisplay.textContent = '$' + priceWithTax.toFixed(2);

    // Ganancia
    if (cost > 0) {
      const profitPct = ((price - cost) / cost * 100).toFixed(1);

      if (profitPct > 0) {
        profitDisplay.textContent = '↑ ' + profitPct + '%';
        profitDisplay.className = 'font-bold text-green-700';
      } else if (profitPct < 0) {
        profitDisplay.textContent = '↓ ' + profitPct + '%';
        profitDisplay.className = 'font-bold text-red-700';
      } else {
        profitDisplay.textContent = '0%';
        profitDisplay.className = 'font-bold text-gray-700';
      }
    } else {
      profitDisplay.textContent = '—';
      profitDisplay.className = 'font-bold text-gray-500';
    }
  }

  // Escuchar cambios en los tres inputs
  costInput.addEventListener('input', recalculate);
  priceInput.addEventListener('input', recalculate);
  taxRateSelect.addEventListener('change', recalculate);

  // Calcular al cargar (para modo edición)
  recalculate();
});
