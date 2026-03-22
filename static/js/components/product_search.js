/**
 * Alpine.js component for Advanced Product Search
 * Part of BULONERA ERP shared components.
 */
function productSearchComponent(addToCallback = null) {
  return {
    productSearch: {
      showPanel: false,
      query: '',
      category: '',
      subcategory: '',
      brand: '',
      supplier: '',
      isSearching: false,
      results: []
    },

    async searchProducts() {
      if (!this.productSearch.query && !this.productSearch.category && !this.productSearch.subcategory && !this.productSearch.brand && !this.productSearch.supplier) {
        return;
      }

      this.productSearch.isSearching = true;
      try {
        const params = new URLSearchParams({
          q: this.productSearch.query,
          category: this.productSearch.category,
          subcategory: this.productSearch.subcategory,
          brand: this.productSearch.brand,
          supplier: this.productSearch.supplier
        });
        
        const response = await fetch(`/api/products/search/?${params.toString()}`);
        if (response.ok) {
          this.productSearch.results = await response.json();
        }
      } catch (e) {
        console.error("Error searching products:", e);
      } finally {
        this.productSearch.isSearching = false;
      }
    },

    addProductToSale(product) {
       // This method name is legacy for compatibility with sale_form.html and quote_form.html
       // It delegates to the main form's addItem logically.
       if (typeof this.addItem === 'function') {
           this.addItem(product);
       } else if (addToCallback) {
           addToCallback(product);
       } else {
           console.warn("No addItem function found in scope for product:", product);
       }
    }
  };
}
