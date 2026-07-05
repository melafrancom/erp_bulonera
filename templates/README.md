# 📦 UI Templates — Cerebro Local

## 🎯 Propósito
El directorio `templates` consolida todas las interfaces de usuario web (HTML layouts) del ERP renderizadas en servidor mediante el motor de plantillas de Django. Sigue el patrón estético premium "**The Bulonera Pattern**", estructurando el frontend mediante **TailwindCSS v3** para estilos atómicos, **Alpine.js** para interactividad asíncrona ligera en el cliente y **Lucide Icons** para iconografía vectorizada.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   Ninguno (es la capa de presentación de la interfaz de usuario).
*   **Es consumido por:**
    *   Las vistas web tradicionales de todas las aplicaciones de Django (`{app}/web/views/views.py`) que especifican qué plantilla renderizar para responder a las solicitudes GET de los usuarios.

## 🛠️ Estructura de Directorios
*   **`base/`**: Plantilla maestra global (`base.html`) y layouts principales. Configura el `<head>`, detecta y aplica automáticamente el modo oscuro, y define los bloques de contenido (`content`, `extra_js`, `extra_css`).
*   **`includes/`**: Componentes visuales comunes e independientes (DRY). Contiene bloques reutilizables de layouts como barras de navegación lateral (`sidebar.html`), pies de página y elementos de UI comunes.
*   **Carpetas por App (`sales/`, `inventory/`, etc.)**: Plantillas específicas para la visualización y operaciones web de cada módulo, separadas de forma limpia.

## ⚡ Estándares de Diseño y Componentes DRY
*   **Detección Automática de Modo Oscuro:** El archivo base ejecuta en el `<head>` un bloque JavaScript inline que lee la preferencia en el `localStorage` o el esquema de color del sistema operativo (`prefers-color-scheme: dark`) para inyectar la clase `dark` al elemento raíz HTML antes del renderizado de la página, mitigando parpadeos visuales (flashes).
*   **Diseño Spatial Composition:** Se aplican layouts fluidos con bordes sutiles, esquinas redondeadas y micro-interacciones de hover que responden instantáneamente a las acciones del usuario.

## 📝 Documentación de Detalle
*   [Estándares de Plantillas y Componentes DRY](docs/template_design_system.md): Detalla las reglas de codificación de templates, composición de layouts modulares, y la biblioteca de componentes comunes en el ERP.
