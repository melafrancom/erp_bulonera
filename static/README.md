# Static Files Structure - Bulonera Alvear ERP/CRM

Estructura modular de archivos estáticos para el proyecto.

## 📁 Estructura de Carpetas

```
static/
├── css/                    # Hojas de estilo CSS
│   ├── base.css           # Variables CSS, estilos globales, utilidades
│   └── forms.css          # Estilos para formularios de Django
├── js/                     # JavaScript
│   ├── main.js            # Funciones principales, inicialización
│   └── utils.js           # Funciones utilitarias (AJAX, validaciones, etc.)
└── img/                    # Imágenes
    └── .gitkeep           # Placeholder para Git
```

## 📄 Archivos CSS

### `css/base.css`
- **Variables CSS personalizadas** (colores, espaciado, bordes, sombras)
- **Componentes reutilizables**: botones, cards, badges
- **Utilidades de animación**
- **Media queries** para responsive design

**Variables principales:**
- `--color-primary`, `--color-secondary`: Colores del tema
- `--color-success`, `--color-warning`, `--color-error`: Estados
- `--spacing-*`: Sistema de espaciado consistente
- `--shadow-*`: Sombras predefinidas

### `css/forms.css`
- **Estilos para formularios de Django**
- **Estados de validación** (is-invalid)
- **Input personalizado** (text, select, textarea, checkbox, radio)
- **File upload** personalizado
- **Mensajes de error** compatibles con Django (errorlist)

## 🔧 Archivos JavaScript

### `js/main.js`
Funciones principales y de inicialización:
- `initLucideIcons()`: Inicializa iconos Lucide
- `initDismissableAlerts()`: Permite cerrar alertas
- `initFormValidation()`: Validación de formularios en tiempo real
- `validateField(field)`: Valida campos individuales
- `showToast(message, type)`: Notificaciones toast
- `debounce(func, wait)`: Debouncing para búsquedas
- `formatCurrency(amount)`: Formato de moneda argentina (ARS)
- `formatDate(date)`: Formato de fecha español

### `js/utils.js`
Utilidades y helpers:
- **AJAX**: `ajaxRequest(url, method, data)` con CSRF token
- **CUIT/CUIL**: `validateCUIT(cuit)`, `formatCUIT(cuit)`
- **Códigos de barra**: `validateEAN13(barcode)`
- **Texto**: `slugify()`, `capitalize()`, `truncate()`
- **Clipboard**: `copyToClipboard(text)`
- **Descarga**: `downloadFile(blob, filename)`
- **Scroll**: `smoothScrollTo(elementId)`
- **UUID**: `generateUUID()`

## 🎨 Uso en Templates

### Cargar archivos estáticos en un template:

```django
{% load static %}

{# En el <head> #}
<link rel="stylesheet" href="{% static 'css/base.css' %}" />
<link rel="stylesheet" href="{% static 'css/forms.css' %}" />

{# Antes del </body> #}
<script src="{% static 'js/utils.js' %}"></script>
<script src="{% static 'js/main.js' %}"></script>
```

### Ejemplos de uso:

#### Usar variables CSS:
```css
.mi-componente {
  background-color: var(--color-primary);
  padding: var(--spacing-lg);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow-md);
}
```

#### Usar clases predefinidas:
```html
<button class="btn btn-primary">Guardar</button>
<div class="card">Contenido del card</div>
<span class="badge badge-success">Activo</span>
```

#### Usar funciones JavaScript:
```javascript
// Mostrar notificación
showToast('Guardado exitosamente', 'success');

// Validar CUIT
if (utils.validateCUIT('20-12345678-9')) {
  console.log('CUIT válido');
}

// Formatear moneda
const precio = utils.formatCurrency(1500.50); // "$1.500,50"

// Petición AJAX
utils.ajaxRequest('/api/productos/', 'GET')
  .then(data => console.log(data))
  .catch(error => console.error(error));
```

## 🚀 Comando collectstatic

En **producción**, ejecutar:

```bash
docker-compose exec web python manage.py collectstatic --noinput
```

Esto copiará todos los archivos de `static/` a `staticfiles/` para que el servidor web los sirva.

## 📝 Notas

- **Desarrollo**: Django sirve archivos estáticos automáticamente desde `static/`
- **Producción**: Usar `collectstatic` y configurar servidor web (Nginx/Apache)
- Los archivos CSS usan **variables personalizadas** compatibles con Tailwind
- JavaScript está **modularizado** para facilitar mantenimiento
- Todas las funciones tienen **validaciones específicas para Argentina** (CUIT, formato de moneda)

---

**Última actualización**: Enero 2026
