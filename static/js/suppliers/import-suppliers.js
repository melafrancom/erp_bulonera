/**
 * import-suppliers.js
 * Maneja la lógica de validación y drag & drop para la vista de importación de proveedores.
 */

document.addEventListener('DOMContentLoaded', () => {
    initSupplierImport();
});

function initSupplierImport() {
    const fileInput = document.getElementById('fileInput');
    const importForm = document.getElementById('importForm');
    
    if (!fileInput || !importForm) return;

    const dropZone = document.getElementById('dropZone');
    const dropContent = document.getElementById('dropContent');
    const fileSelectedUI = document.getElementById('fileSelectedUI');
    const fileNameDisplay = document.getElementById('fileName');
    const fileSizeDisplay = document.getElementById('fileSize');
    const fileError = document.getElementById('fileError');
    const errorMessage = document.getElementById('errorMessage');
    
    const submitBtn = document.getElementById('submitBtn');
    const submitText = document.getElementById('submitText');
    const submitIcon = document.getElementById('submitIcon');
    const submitSpinner = document.getElementById('submitSpinner');

    const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
    const ALLOWED_EXTENSIONS = ['.xlsx', '.csv'];

    // Prevenir comportamientos por defecto del drag&drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Efectos visuales al arrastrar
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        dropZone.classList.add('border-blue-500', 'bg-blue-50');
        dropZone.classList.remove('border-gray-300', 'bg-gray-50');
    }

    function unhighlight(e) {
        dropZone.classList.remove('border-blue-500', 'bg-blue-50');
        dropZone.classList.add('border-gray-300', 'bg-gray-50');
    }

    // Manejar el archivo soltado
    dropZone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        let dt = e.dataTransfer;
        let files = dt.files;
        if (files.length > 0) {
            fileInput.files = files; // Forzar el input a tener el archivo
            handleFileValidation(files[0]);
        }
    }

    // Manejar la selección manual (click)
    fileInput.addEventListener('change', function(e) {
        if (this.files.length > 0) {
            handleFileValidation(this.files[0]);
        } else {
            resetFileUI();
        }
    });

    // Validar el archivo e interactuar con la UI
    function handleFileValidation(file) {
        hideError();
        
        // 1. Validar extensión
        const ext = getExtension(file.name).toLowerCase();
        if (!ALLOWED_EXTENSIONS.includes(ext)) {
            showError(`El formato "${ext}" no es válido. Solo se admiten archivos .xlsx o .csv.`);
            resetFileUI(false);
            return;
        }

        // 2. Validar tamaño
        if (file.size > MAX_FILE_SIZE) {
            showError(`El archivo pesa ${(file.size / (1024*1024)).toFixed(2)}MB. El máximo permitido es 10MB.`);
            resetFileUI(false);
            return;
        }

        // Si es válido, actualizar UI
        showSelectedFileUI(file);
    }

    function showSelectedFileUI(file) {
        // Ocultar zona de drop, mostrar UI de archivo seleccionado
        dropContent.classList.add('hidden');
        fileSelectedUI.classList.remove('hidden');
        
        // Poner el texto on top
        fileSelectedUI.classList.add('z-20');
        
        fileNameDisplay.textContent = file.name;
        fileSizeDisplay.textContent = formatBytes(file.size);
        
        // Estilar el borde para indicar éxito
        dropZone.classList.add('border-green-500', 'bg-green-50');
        dropZone.classList.remove('border-gray-300', 'hover:bg-gray-100');

        // Habilitar submit
        submitBtn.disabled = false;
    }

    function resetFileUI(clearInput = true) {
        if (clearInput) {
            fileInput.value = '';
        }
        
        // Restaurar estado inicial de UI
        dropContent.classList.remove('hidden');
        fileSelectedUI.classList.add('hidden');
        fileSelectedUI.classList.remove('z-20');
        
        dropZone.classList.remove('border-green-500', 'bg-green-50');
        dropZone.classList.add('border-gray-300', 'hover:bg-gray-100');

        submitBtn.disabled = true;
    }

    function showError(msg) {
        errorMessage.textContent = msg;
        fileError.classList.remove('hidden');
    }

    function hideError() {
        fileError.classList.add('hidden');
        errorMessage.textContent = '';
    }

    // Al hacer submit, mostrar spinner y evitar múltiples clicks
    importForm.addEventListener('submit', function(e) {
        if (!fileInput.files.length) {
            e.preventDefault();
            return;
        }
        
        submitBtn.disabled = true;
        submitText.textContent = 'Importando...';
        submitIcon.classList.add('hidden');
        submitSpinner.classList.remove('hidden');
        dropZone.classList.add('opacity-50', 'pointer-events-none');
    });

    // Permite volver a cambiar de archivo haciendo click en "Cambiar archivo"
    const retryBtn = fileSelectedUI.querySelector('.underline');
    if (retryBtn) {
        retryBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Evitar que dispare el input de nuevo inmediatamente
            resetFileUI();
            fileInput.click();
        });
    }

    // --- Helpers ---
    function getExtension(filename) {
        return filename.substring(filename.lastIndexOf('.'));
    }

    function formatBytes(bytes, decimals = 2) {
        if (!+bytes) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
    }
}
