/**
 * supplier-form.js
 * Maneja la interacción del formulario de proveedores:
 * - Formateo automático de CUIT (XX-XXXXXXXX-X)
 * - Restricciones de input
 */

document.addEventListener('DOMContentLoaded', () => {
    initCuitFormatting();
});

/**
 * Inicializa el formateo automático del campo CUIT
 */
function initCuitFormatting() {
    const cuitInput = document.getElementById('id_cuit');
    const cuitError = document.getElementById('cuitError');

    if (!cuitInput) return;

    // Solo permitir números y guiones al tipear
    cuitInput.addEventListener('keypress', (e) => {
        // Permitir teclas de control, backspace, etc
        if (e.key.length !== 1 || e.ctrlKey || e.metaKey) return;
        
        const isNumber = /^[0-9]$/.test(e.key);
        const isDash = e.key === '-';

        if (!isNumber && !isDash) {
            e.preventDefault();
        }
    });

    // Formatear al escribir/pegar
    cuitInput.addEventListener('input', (e) => {
        let value = e.target.value.replace(/[^0-9]/g, ''); // Quitar todo lo no numérico
        
        // Limitar a 11 dígitos
        if (value.length > 11) {
            value = value.substring(0, 11);
        }

        let formatted = value;

        // Agregar formato XX-XXXXXXXX-X
        if (value.length > 2) {
            formatted = value.substring(0, 2) + '-' + value.substring(2);
        }
        if (value.length > 10) {
            formatted = formatted.substring(0, 11) + '-' + value.substring(10);
        }

        e.target.value = formatted;

        // Validar longitud final y mostrar/ocultar error básico
        if (value.length > 0 && value.length !== 11) {
            if (cuitError) cuitError.classList.remove('hidden');
            cuitInput.classList.add('border-red-500', 'focus:ring-red-500');
            cuitInput.classList.remove('border-gray-300', 'focus:ring-blue-500');
        } else {
            if (cuitError) cuitError.classList.add('hidden');
            cuitInput.classList.remove('border-red-500', 'focus:ring-red-500');
            cuitInput.classList.add('border-gray-300', 'focus:ring-blue-500');
        }
    });

    // Al perder el foco (blur), limpiar caracteres sueltos si el input quedó por la mitad
    cuitInput.addEventListener('blur', (e) => {
        const rawLength = e.target.value.replace(/[^0-9]/g, '').length;
        if (rawLength > 0 && rawLength < 11) {
            if (cuitError) cuitError.classList.remove('hidden');
            cuitInput.classList.add('border-red-500', 'focus:ring-red-500');
        }
    });
}
