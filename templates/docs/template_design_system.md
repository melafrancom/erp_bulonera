# 🎨 Estándares de Plantillas y Componentes DRY

Este documento detalla las convenciones frontend, la estructura del motor de plantillas de Django, la integración de TailwindCSS y Alpine.js, y los componentes de interfaz reutilizables aplicados en **BULONERA ERP**.

---

## 🌓 Detección e Inyección de Tema (Modo Oscuro)

Para evitar el parpadeo de pantalla en blanco (FOUC - Flash of Unstyled Content) al recargar vistas, el archivo [templates/base/base.html](file:///c:/Users/frank/Desktop/BULONERA_ERP/templates/base/base.html) inyecta de forma inmediata en el `<head>` un bloque JavaScript bloqueante de renderizado:

```javascript
// Detección automática en head
if (localStorage.getItem('theme') === 'dark' ||
    (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
  document.documentElement.classList.add('dark');
} else {
  document.documentElement.classList.remove('dark');
}
```

---

## 🧱 Estructura Base del Layout

La estructura global de las pantallas de salón del ERP sigue una composición espacial fluida de tres bloques principales:

```
  ┌────────────────────────────────────────────────────────┐
  │                   Navbar (Superior)                    │ (Perfil, Notificaciones, Teme Toggle)
  ├────────────────────────────────────────────────────────┤
  │  Sidebar (Lateral Izquierdo)  │                        │
  │  - Ventas                     │   Main Content Area    │
  │  - Inventario                 │   (Páginas de          │
  │  - Facturación                │    Vistas específicas) │
  │  - Cobros                     │                        │
  │  - Gastos                     │                        │
  └───────────────────────────────┴────────────────────────┘
```

---

## ⚡ Convenciones de TailwindCSS y Alpine.js

Para garantizar un código limpio, mantenible y DRY:

### 1. Clases de Utilidad de Tailwind
*   **Regla de Oro:** Está estrictamente prohibido utilizar estilos en línea (`style="..."`) o archivos CSS tradicionales. Toda la composición se realiza mediante clases de utilidad.
*   **Modo Oscuro Completo:** Todo componente interactivo o contenedor estructural debe poseer clases de modo oscuro (`dark:`). Ejemplo:
    ```html
    <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700/50">
    ```

### 2. Interactividad Ligera con Alpine.js
Para evitar la complejidad de cargar frameworks SPA (React/Vue) pero mantener interfaces vivas y reactivas en el mostrador, se utiliza **Alpine.js**:
*   **Manejo de Estados Locales (Modales, Dropdowns):** Se definen en los elementos HTML mediante `x-data`.
*   **Efectos Visuales y Transiciones:** Uso de `x-show`, `x-transition` y directivas del cliente.
    ```html
    <!-- Modal en Alpine.js -->
    <div x-data="{ open: false }">
        <button @click="open = true" class="bg-blue-600 text-white px-4 py-2 rounded">Abrir</button>
        <div x-show="open" @click.away="open = false" class="fixed inset-0 bg-black/50 flex items-center justify-center">
            <div class="bg-white dark:bg-slate-900 p-6 rounded-lg">
                <h3>Detalle del Registro</h3>
                <button @click="open = false" class="mt-4">Cerrar</button>
            </div>
        </div>
    </div>
    ```

---

## 🗂️ Componentes Visuales Comunes (DRY)

El directorio `templates/includes/` define componentes que se inyectan mediante etiquetas `{% include "..." %}`:

*   **Tarjetas Universales (Cards):**
    `bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700/50 rounded-lg p-4 shadow-sm`
*   **Badges de Estado (badges.html):**
    Visualización estándar de etiquetas con colores HSL calculados según el estado (ej. Borrador: plomo, Confirmada: azul, Pagada: verde, Cancelada: rojo).
*   **Controles de Formulario:**
    Estilo homogéneo de inputs (`input`, `select`, `textarea`) con bordes redondeados y efectos de foco (`focus:ring-2 focus:ring-blue-500/20`).
