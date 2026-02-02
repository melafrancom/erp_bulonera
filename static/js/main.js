/**
 * MAIN.JS - Bulonera Alvear ERP/CRM
 * Funciones principales y inicialización
 */

// Esperar a que el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
  console.log('ERP Bulonera Alvear - Sistema inicializado');
  
  // Inicializar componentes
  initLucideIcons();
  initDismissableAlerts();
  initFormValidation();
  initTooltips();
});

/**
 * Inicializar iconos de Lucide
 */
function initLucideIcons() {
  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }
}

/**
 * Permitir cerrar alertas de Django messages
 */
function initDismissableAlerts() {
  const alerts = document.querySelectorAll('.alert-dismissable');
  
  alerts.forEach(alert => {
    const closeBtn = alert.querySelector('.alert-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        alert.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => {
          alert.remove();
        }, 300);
      });
    }
  });
}

/**
 * Validación de formularios en tiempo real
 */
function initFormValidation() {
  const forms = document.querySelectorAll('form[data-validate]');
  
  forms.forEach(form => {
    const inputs = form.querySelectorAll('input, select, textarea');
    
    inputs.forEach(input => {
      input.addEventListener('blur', function() {
        validateField(this);
      });
      
      input.addEventListener('input', function() {
        if (this.classList.contains('is-invalid')) {
          validateField(this);
        }
      });
    });
    
    form.addEventListener('submit', function(e) {
      let isValid = true;
      
      inputs.forEach(input => {
        if (!validateField(input)) {
          isValid = false;
        }
      });
      
      if (!isValid) {
        e.preventDefault();
      }
    });
  });
}

/**
 * Validar un campo individual
 */
function validateField(field) {
  const value = field.value.trim();
  const errorContainer = field.parentElement.querySelector('.form-error');
  
  // Limpiar errores previos
  field.classList.remove('is-invalid');
  if (errorContainer) {
    errorContainer.textContent = '';
  }
  
  // Validar campo requerido
  if (field.hasAttribute('required') && !value) {
    showFieldError(field, 'Este campo es obligatorio');
    return false;
  }
  
  // Validar email
  if (field.type === 'email' && value) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) {
      showFieldError(field, 'Ingrese un email válido');
      return false;
    }
  }
  
  // Validar longitud mínima
  if (field.hasAttribute('minlength')) {
    const minLength = parseInt(field.getAttribute('minlength'));
    if (value.length < minLength) {
      showFieldError(field, `Mínimo ${minLength} caracteres`);
      return false;
    }
  }
  
  return true;
}

/**
 * Mostrar error en campo
 */
function showFieldError(field, message) {
  field.classList.add('is-invalid');
  
  let errorContainer = field.parentElement.querySelector('.form-error');
  if (!errorContainer) {
    errorContainer = document.createElement('span');
    errorContainer.className = 'form-error';
    field.parentElement.appendChild(errorContainer);
  }
  
  errorContainer.textContent = message;
}

/**
 * Inicializar tooltips (si se usa una librería)
 */
function initTooltips() {
  const tooltips = document.querySelectorAll('[data-tooltip]');
  
  tooltips.forEach(element => {
    element.setAttribute('title', element.getAttribute('data-tooltip'));
  });
}

/**
 * Confirmar acción peligrosa
 */
function confirmAction(message = '¿Estás seguro?') {
  return confirm(message);
}

/**
 * Mostrar notificación toast (simple)
 */
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type} animate-fade-in`;
  toast.textContent = message;
  
  const colors = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    warning: 'bg-yellow-500',
    info: 'bg-blue-500'
  };
  
  toast.classList.add(colors[type] || colors.info);
  toast.style.cssText = `
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    padding: 1rem 1.5rem;
    color: white;
    border-radius: 0.5rem;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    z-index: 9999;
  `;
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.style.animation = 'fadeOut 0.3s ease-out';
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 3000);
}

/**
 * Debounce para búsquedas en tiempo real
 */
function debounce(func, wait = 300) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Formatear número como moneda
 */
function formatCurrency(amount) {
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS'
  }).format(amount);
}

/**
 * Formatear fecha
 */
function formatDate(date) {
  return new Intl.DateTimeFormat('es-AR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  }).format(new Date(date));
}

// Exportar funciones globales
window.confirmAction = confirmAction;
window.showToast = showToast;
window.debounce = debounce;
window.formatCurrency = formatCurrency;
window.formatDate = formatDate;
