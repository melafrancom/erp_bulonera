# 📦 Directorio Temporal (`tmp/`) — Cerebro Local

## 🎯 Propósito
El directorio `tmp/` actúa como un espacio de trabajo efímero para pruebas locales, scripts experimentales (scratch scripts) y almacenamiento de archivos de caché generados en tiempo de ejecución. 

---

## 🔒 Regla de Git (.gitignore)
Este directorio se encuentra excluido del control de versiones en el archivo [.gitignore](file:///c:/Users/frank/Desktop/BULONERA_ERP/.gitignore):
*   Los desarrolladores y agentes de IA son libres de crear scripts de depuración rápida o almacenar archivos de salida de pruebas (ej: PDFs generados, volcados de base de datos) en este directorio sin riesgo de contaminar el repositorio de Git.
*   **Advertencia:** No almacenes código fuente del negocio o configuraciones que requieran persistencia en producción dentro de esta carpeta, ya que no se desplegarán al VPS.

---

## 🛠️ Contenido Actual
*   [tmp/test_celery.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/tmp/test_celery.py): Script de prueba liviano utilizado para validar la conexión con Redis e inyectar tareas básicas en la cola de Celery para verificar el procesamiento asíncrono local del worker.
