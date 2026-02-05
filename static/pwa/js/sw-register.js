// Registro del Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
        .then(registration => {
            console.log('SW registrado con éxito')
        }).catch(error => {
            console.log('Error al registrar al SW', error)
        })
    })
}
