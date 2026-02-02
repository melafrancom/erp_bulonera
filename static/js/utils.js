/**
 * UTILS.JS - Bulonera Alvear ERP/CRM
 * Funciones utilitarias y helpers
 */

/**
 * Obtener cookie por nombre (útil para CSRF token)
 */
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

/**
 * Realizar petición AJAX con CSRF token
 */
async function ajaxRequest(url, method = 'GET', data = null) {
  const csrftoken = getCookie('csrftoken');
  
  const options = {
    method: method,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrftoken
    },
    credentials: 'same-origin'
  };
  
  if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
    options.body = JSON.stringify(data);
  }
  
  try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error en la petición:', error);
    throw error;
  }
}

/**
 * Copiar texto al portapapeles
 */
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    showToast('Copiado al portapapeles', 'success');
    return true;
  } catch (err) {
    console.error('Error al copiar:', err);
    showToast('Error al copiar', 'error');
    return false;
  }
}

/**
 * Descargar archivo desde blob
 */
function downloadFile(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

/**
 * Validar CUIT/CUIL argentino
 */
function validateCUIT(cuit) {
  // Remover guiones y espacios
  cuit = cuit.replace(/[-\s]/g, '');
  
  // Verificar longitud
  if (cuit.length !== 11) {
    return false;
  }
  
  // Verificar que sean solo números
  if (!/^\d+$/.test(cuit)) {
    return false;
  }
  
  // Algoritmo de validación
  const multiplicadores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
  let suma = 0;
  
  for (let i = 0; i < 10; i++) {
    suma += parseInt(cuit[i]) * multiplicadores[i];
  }
  
  const resto = suma % 11;
  const digitoVerificador = resto === 0 ? 0 : resto === 1 ? 9 : 11 - resto;
  
  return parseInt(cuit[10]) === digitoVerificador;
}

/**
 * Formatear CUIT con guiones (XX-XXXXXXXX-X)
 */
function formatCUIT(cuit) {
  cuit = cuit.replace(/[-\s]/g, '');
  
  if (cuit.length === 11) {
    return `${cuit.substring(0, 2)}-${cuit.substring(2, 10)}-${cuit.substring(10)}`;
  }
  
  return cuit;
}

/**
 * Validar código de barras (EAN-13)
 */
function validateEAN13(barcode) {
  if (!/^\d{13}$/.test(barcode)) {
    return false;
  }
  
  let sum = 0;
  for (let i = 0; i < 12; i++) {
    sum += parseInt(barcode[i]) * (i % 2 === 0 ? 1 : 3);
  }
  
  const checkDigit = (10 - (sum % 10)) % 10;
  return checkDigit === parseInt(barcode[12]);
}

/**
 * Generar slug desde texto
 */
function slugify(text) {
  return text
    .toString()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // Remover acentos
    .replace(/[^\w\s-]/g, '') // Remover caracteres especiales
    .replace(/\s+/g, '-') // Reemplazar espacios por guiones
    .replace(/--+/g, '-') // Remover guiones múltiples
    .trim();
}

/**
 * Calcular porcentaje
 */
function calculatePercentage(value, total) {
  if (total === 0) return 0;
  return ((value / total) * 100).toFixed(2);
}

/**
 * Redondear a 2 decimales
 */
function roundToTwo(num) {
  return Math.round((num + Number.EPSILON) * 100) / 100;
}

/**
 * Verificar si un elemento está visible en el viewport
 */
function isInViewport(element) {
  const rect = element.getBoundingClientRect();
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
}

/**
 * Scroll suave a elemento
 */
function smoothScrollTo(elementId) {
  const element = document.getElementById(elementId);
  if (element) {
    element.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });
  }
}

/**
 * Generar ID único
 */
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Capitalizar primera letra
 */
function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

/**
 * Truncar texto
 */
function truncate(str, maxLength = 50) {
  if (str.length <= maxLength) return str;
  return str.substring(0, maxLength - 3) + '...';
}

// Exportar funciones
window.utils = {
  getCookie,
  ajaxRequest,
  copyToClipboard,
  downloadFile,
  validateCUIT,
  formatCUIT,
  validateEAN13,
  slugify,
  calculatePercentage,
  roundToTwo,
  isInViewport,
  smoothScrollTo,
  generateUUID,
  capitalize,
  truncate
};
