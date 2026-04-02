/**
 * import-products.js
 * 
 * Drag & drop para subir archivos Excel/CSV al formulario de importación.
 * - Validación de tipo de archivo (.xlsx, .csv)
 * - Validación de tamaño (máximo 10 MB)
 * - Spinner al enviar el formulario
 * 
 * Dependencias: Ninguna (Vanilla JS)
 */

document.addEventListener('DOMContentLoaded', function () {

  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const defaultState = document.getElementById('dropZoneDefault');
  const selectedState = document.getElementById('dropZoneSelected');
  const fileNameDisplay = document.getElementById('selectedFileName');
  const fileSizeDisplay = document.getElementById('selectedFileSize');
  const clearFileBtn = document.getElementById('clearFileBtn');
  const fileError = document.getElementById('fileError');
  const fileErrorMsg = document.getElementById('fileErrorMsg');
  const submitBtn = document.getElementById('submitBtn');
  const submitIcon = document.getElementById('submitIcon');
  const submitSpinner = document.getElementById('submitSpinner');
  const submitText = document.getElementById('submitText');
  const importForm = document.getElementById('importForm');

  if (!dropZone || !fileInput) return;

  // Extensiones y tamaño máximo permitidos
  const VALID_EXTENSIONS = ['.xlsx', '.csv'];
  const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

  /**
   * Valida el archivo seleccionado.
   * @param {File} file
   * @returns {string|null} Mensaje de error o null si es válido
   */
  function validateFile(file) {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!VALID_EXTENSIONS.includes(ext)) {
      return 'Formato no soportado: ' + ext + '. Usá .xlsx o .csv';
    }
    if (file.size > MAX_SIZE) {
      const sizeMB = (file.size / 1024 / 1024).toFixed(1);
      return 'Archivo demasiado grande (' + sizeMB + ' MB). Máximo: 10 MB';
    }
    return null;
  }

  /**
   * Formatea bytes a formato legible.
   */
  function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  }

  /**
   * Muestra el archivo seleccionado en la zona de drop.
   */
  function showFile(file) {
    const error = validateFile(file);
    if (error) {
      showError(error);
      clearFile();
      return;
    }

    hideError();
    fileNameDisplay.textContent = file.name;
    fileSizeDisplay.textContent = formatSize(file.size);
    defaultState.classList.add('hidden');
    selectedState.classList.remove('hidden');
    dropZone.classList.add('border-emerald-400', 'dark:border-emerald-500', 'bg-emerald-50/30', 'dark:bg-emerald-900/10');
    dropZone.classList.remove('border-gray-100', 'dark:border-slate-900', 'bg-white', 'dark:bg-slate-800');
    submitBtn.disabled = false;
  }

  /**
   * Limpia el archivo seleccionado.
   */
  function clearFile() {
    fileInput.value = '';
    defaultState.classList.remove('hidden');
    selectedState.classList.add('hidden');
    dropZone.classList.remove('border-emerald-400', 'dark:border-emerald-500', 'bg-emerald-50/30', 'dark:bg-emerald-900/10');
    dropZone.classList.add('border-gray-100', 'dark:border-slate-900', 'bg-white', 'dark:bg-slate-800');
    submitBtn.disabled = true;
  }

  /**
   * Muestra error de validación.
   */
  function showError(msg) {
    fileErrorMsg.textContent = msg;
    fileError.classList.remove('hidden');
  }

  /**
   * Oculta error de validación.
   */
  function hideError() {
    fileError.classList.add('hidden');
  }

  // ── Eventos del drop zone ────────────────────────────────────────

  // Click → abrir file picker
  dropZone.addEventListener('click', function () {
    fileInput.click();
  });

  // Teclado: Enter o Space → abrir file picker
  dropZone.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInput.click();
    }
  });

  // File input change
  fileInput.addEventListener('change', function () {
    if (this.files && this.files[0]) {
      showFile(this.files[0]);
    }
  });

  // Drag & Drop
  dropZone.addEventListener('dragover', function (e) {
    e.preventDefault();
    e.stopPropagation();
    this.classList.add('border-blue-400', 'bg-blue-50');
  });

  dropZone.addEventListener('dragleave', function (e) {
    e.preventDefault();
    e.stopPropagation();
    this.classList.remove('border-blue-400', 'bg-blue-50');
  });

  dropZone.addEventListener('drop', function (e) {
    e.preventDefault();
    e.stopPropagation();
    this.classList.remove('border-blue-400', 'bg-blue-50');

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      // Asignar archivo al input (no se puede hacer directamente con FileList,
      // así que usamos DataTransfer)
      try {
        fileInput.files = e.dataTransfer.files;
      } catch (err) {
        // Fallback para navegadores que no permiten asignar FileList
        console.warn('No se pudo asignar archivos al input:', err);
      }
      showFile(e.dataTransfer.files[0]);
    }
  });

  // Limpiar archivo
  if (clearFileBtn) {
    clearFileBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      clearFile();
      hideError();
    });
  }

  // ── Submit con spinner ───────────────────────────────────────────

  if (importForm) {
    importForm.addEventListener('submit', function () {
      if (!fileInput.files || !fileInput.files[0]) return;

      // Deshabilitar botón y mostrar spinner
      submitBtn.disabled = true;
      submitText.textContent = 'Importando...';
      if (submitIcon) submitIcon.classList.add('hidden');
      if (submitSpinner) submitSpinner.classList.remove('hidden');
    });
  }
});
