/**
 * Alpine.js component for Customer Selection
 * Part of BULONERA ERP shared components.
 */
function customerSelectorComponent() {
  return {
    customerMode: 'anonymous',
    customerSearchQuery: '',
    customerSearching: false,
    customerResults: [],
    showCustomerResults: false,
    selectedCustomer: null,
    newCustomer: { name: '', phone: '', email: '', cuit: '' },
    isVerifyingAfip: false,
    isSubmittingCustomer: false,

    async searchCustomers() {
      if (this.customerSearchQuery.length < 2) {
        this.customerResults = [];
        return;
      }
      this.customerSearching = true;
      try {
        const response = await fetch(`/api/v1/customers/?search=${encodeURIComponent(this.customerSearchQuery)}`);
        if (response.ok) {
          const body = await response.json();
          const targetData = body.data || body;
          this.customerResults = targetData.results || targetData || [];
        }
      } catch (e) {
        console.error("Error searching customers:", e);
      } finally {
        this.customerSearching = false;
      }
    },

    selectCustomer(customer) {
      this.selectedCustomer = customer;
      this.showCustomerResults = false;
      this.customerSearchQuery = '';
      if (this.onCustomerSelect) {
        this.onCustomerSelect(customer);
      }
    },

    setCustomerMode(mode) {
      this.customerMode = mode;
      this.selectedCustomer = null;
      this.newCustomer = { name: '', phone: '', email: '', cuit: '' };
      this.customerResults = [];
      this.customerSearchQuery = '';
    },

    async verifyAfip() {
      if (!this.newCustomer.cuit) return;
      this.isVerifyingAfip = true;
      try {
        const response = await fetch(`/afip/api/padron/${this.newCustomer.cuit}/`);
        const data = await response.json();
        if (data.success && data.data) {
          const d = data.data;
          this.newCustomer.name = d.razon_social || ((d.nombre || '') + ' ' + (d.apellido || '')) || this.newCustomer.name;
        } else {
          alert('No se encontraron datos en AFIP para este CUIT.');
        }
      } catch (e) {
        console.error("Error verifying AFIP:", e);
        alert('Error al conectar con el servicio de AFIP.');
      } finally {
        this.isVerifyingAfip = false;
      }
    },

    async registerCustomer() {
      if (!this.newCustomer.name || !this.newCustomer.cuit) {
        alert('Por favor complete Nombre y CUIT/DNI.');
        return;
      }

      this.isSubmittingCustomer = true;
      try {
        const response = await fetch('/api/v1/customers/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
          },
          body: JSON.stringify({
            business_name: this.newCustomer.name,
            phone: this.newCustomer.phone,
            email: this.newCustomer.email,
            cuit_cuil: this.newCustomer.cuit,
            is_active: true
          })
        });

        const body = await response.json();
        if (response.ok) {
          this.selectCustomer(body);
          this.customerMode = 'existing';
          alert('Cliente guardado y seleccionado.');
        } else {
          let errMsg = body?.error?.message || body?.detail || JSON.stringify(body);
          if (body.cuit_cuil) errMsg = 'Error en CUIT/DNI: ' + body.cuit_cuil[0];
          alert('No se pudo guardar el cliente: ' + errMsg);
        }
      } catch (e) {
        console.error("Error registering customer:", e);
        alert('Error inesperado al conectar con el servidor.');
      } finally {
        this.isSubmittingCustomer = false;
      }
    }
  };
}
