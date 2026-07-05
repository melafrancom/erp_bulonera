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
    newCustomer: { name: '', phone: '', email: '', cuit: '', tax_condition: '', billing_address: '' },
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
      this.newCustomer = { name: '', phone: '', email: '', cuit: '', tax_condition: '', billing_address: '' };
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
          if (d.domicilio) {
              this.newCustomer.billing_address = d.domicilio;
          }
          if (d.condicion_iva) {
              // El backend retorna el código normalizado: 'RI', 'MONO', 'EX', 'CF'
              const validCodes = ['RI', 'MONO', 'EX', 'CF', 'NR'];
              const code = d.condicion_iva.toUpperCase().trim();
              if (validCodes.includes(code)) {
                  this.newCustomer.tax_condition = code;
              } else {
                  const upper = code;
                  if (upper.includes('INSCRIPTO') || upper.includes('RESPONSABLE')) 
                      this.newCustomer.tax_condition = 'RI';
                  else if (upper.includes('MONOTRIBUT')) 
                      this.newCustomer.tax_condition = 'MONO';
                  else if (upper.includes('EXENTO')) 
                      this.newCustomer.tax_condition = 'EX';
                  else 
                      this.newCustomer.tax_condition = 'CF';
              }
              console.log(`[AFIP] Condición IVA recibida: "${d.condicion_iva}" → mapeada: "${this.newCustomer.tax_condition}"`);

              // ADVERTENCIA: ws_sr_padron_a13 no retorna impuestos en producción,
              // por lo que CF puede ser un falso negativo. Avisar al usuario.
              if (this.newCustomer.tax_condition === 'CF') {
                  alert(
                      '⚠️ ATENCIÓN: AFIP retornó "Consumidor Final".\n\n' +
                      'El servicio de AFIP actualmente no puede determinar la condición IVA automáticamente. ' +
                      'Si el cliente es Responsable Inscripto, Monotributista o Exento, ' +
                      'seleccionelo manualmente en el campo "Condición ante el IVA" debajo.'
                  );
              }
          } else {
              // AFIP no retornó condición: dejar vacío para que el usuario elija
              this.newCustomer.tax_condition = '';
              alert(
                  '⚠️ AFIP no retornó la condición IVA para este CUIT.\n' +
                  'Por favor seleccione la condición manualmente.'
              );
          }
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
      if (!this.newCustomer.tax_condition) {
        alert('Debe seleccionar la Condición ante el IVA antes de guardar.');
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
            tax_condition: this.newCustomer.tax_condition,
            billing_address: this.newCustomer.billing_address,
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
