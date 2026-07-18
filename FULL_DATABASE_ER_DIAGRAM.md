```mermaid
erDiagram
    User {
        ForeignKey logentry
        ForeignKey outstandingtoken
        ForeignKey user_created_by
        ForeignKey user_updated_by
        ForeignKey user_deleted_by
        ForeignKey userlog_created_by
        ForeignKey userlog_updated_by
        ForeignKey userlog_deleted_by
        ForeignKey logs
        ForeignKey registrationrequest_created_by
        ForeignKey registrationrequest_updated_by
        ForeignKey registrationrequest_deleted_by
        ForeignKey reviewed_requests
        ForeignKey emaillog_created_by
        ForeignKey emaillog_updated_by
        ForeignKey emaillog_deleted_by
        ForeignKey audit_logs
        ForeignKey customersegment_created_by
        ForeignKey customersegment_updated_by
        ForeignKey customersegment_deleted_by
        ForeignKey customer_created_by
        ForeignKey customer_updated_by
        ForeignKey customer_deleted_by
        ForeignKey customernote_created_by
        ForeignKey customernote_updated_by
        ForeignKey customernote_deleted_by
        ForeignKey quote_created_by
        ForeignKey quote_updated_by
        ForeignKey quote_deleted_by
        ForeignKey quoteitem_created_by
        ForeignKey quoteitem_updated_by
        ForeignKey quoteitem_deleted_by
        ForeignKey sale_updated_by
        ForeignKey sale_deleted_by
        ForeignKey created_sales
        ForeignKey stock_reservations
        ForeignKey saleitem_created_by
        ForeignKey saleitem_updated_by
        ForeignKey saleitem_deleted_by
        ForeignKey quoteconversion_created_by
        ForeignKey quoteconversion_updated_by
        ForeignKey quoteconversion_deleted_by
        ForeignKey quoteconversion
        ForeignKey category_created_by
        ForeignKey category_updated_by
        ForeignKey category_deleted_by
        ForeignKey subcategory_created_by
        ForeignKey subcategory_updated_by
        ForeignKey subcategory_deleted_by
        ForeignKey product_created_by
        ForeignKey product_updated_by
        ForeignKey product_deleted_by
        ForeignKey pricelist_created_by
        ForeignKey pricelist_updated_by
        ForeignKey pricelist_deleted_by
        ForeignKey productimage_created_by
        ForeignKey productimage_updated_by
        ForeignKey productimage_deleted_by
        ForeignKey stockmovement_created_by
        ForeignKey stockmovement_updated_by
        ForeignKey stockmovement_deleted_by
        ForeignKey stockcount_created_by
        ForeignKey stockcount_updated_by
        ForeignKey stockcount_deleted_by
        ForeignKey stock_counts
        ForeignKey stockcountitem_created_by
        ForeignKey stockcountitem_updated_by
        ForeignKey stockcountitem_deleted_by
        ForeignKey payment_created_by
        ForeignKey payment_updated_by
        ForeignKey payment_deleted_by
        ForeignKey paymentallocation_created_by
        ForeignKey paymentallocation_updated_by
        ForeignKey paymentallocation_deleted_by
        ForeignKey invoice_created_by
        ForeignKey invoice_updated_by
        ForeignKey invoice_deleted_by
        ForeignKey facturas_emitidas
        ForeignKey invoiceitem_created_by
        ForeignKey invoiceitem_updated_by
        ForeignKey invoiceitem_deleted_by
        ForeignKey suppliertag_created_by
        ForeignKey suppliertag_updated_by
        ForeignKey suppliertag_deleted_by
        ForeignKey supplier_created_by
        ForeignKey supplier_updated_by
        ForeignKey supplier_deleted_by
        ForeignKey expensecategory_created_by
        ForeignKey expensecategory_updated_by
        ForeignKey expensecategory_deleted_by
        ForeignKey expense_created_by
        ForeignKey expense_updated_by
        ForeignKey expense_deleted_by
        CharField password
        DateTimeField last_login
        BooleanField is_superuser
        CharField username
        CharField first_name
        CharField last_name
        BooleanField is_staff
        DateTimeField date_joined
        CharField email
        BooleanField password_change_required
        CharField role
        DateTimeField last_access
        BooleanField can_manage_users
        BooleanField can_manage_products
        BooleanField can_manage_customers
        BooleanField can_manage_sales
        BooleanField can_manage_quotes
        BooleanField can_manage_inventory
        BooleanField can_manage_payments
        BooleanField can_manage_bills
        BooleanField can_manage_suppliers
        BooleanField can_view_reports
    }
    UserLog {
        CharField action
        TextField details
    }
    RegistrationRequest {
        CharField username
        CharField email
        CharField first_name
        CharField last_name
        CharField phone
        CharField status
        TextField reason
        DateTimeField reviewed_at
        TextField rejection_reason
        CharField requested_role
    }
    EmailLog {
        CharField subject
        CharField recipient
        CharField status
        TextField error_message
    }
    AuditLog {
        CharField event_type
        DateTimeField timestamp
        CharField object_id
        CharField object_repr
        JSONField changes
        GenericIPAddressField ip_address
    }
    CustomerSegment {
        ForeignKey customers
        ForeignKey sales_with_segment_discount
        CharField name
        TextField description
        CharField color
        DecimalField discount_percentage
    }
    Customer {
        ForeignKey customer_notes
        ForeignKey quotes
        ForeignKey sales
        ForeignKey payments
        ForeignKey facturas
        CharField customer_type
        CharField business_name
        CharField trade_name
        CharField cuit_cuil
        CharField tax_condition
        CharField email
        CharField phone
        CharField mobile
        CharField website
        CharField contact_person
        CharField billing_address
        CharField billing_city
        CharField billing_state
        CharField billing_zip_code
        CharField billing_country
        IntegerField payment_term
        DecimalField credit_limit
        DecimalField discount_percentage
        BooleanField allow_credit
        TextField notes
    }
    CustomerNote {
        CharField title
        TextField content
        BooleanField is_important
    }
    Quote {
        ForeignKey items
        UUIDField uuid
        CharField number
        DateField date
        DateField valid_until
        CharField customer_name
        CharField customer_phone
        CharField customer_email
        CharField customer_cuit
        CharField status
        BooleanField is_printed
        BooleanField sent_via_wa
        BooleanField sent_via_email
        TextField notes
        TextField internal_notes
        DecimalField _cached_subtotal
        DecimalField _cached_discount
        DecimalField _cached_tax
        DecimalField _cached_total
    }
    QuoteItem {
        DecimalField quantity
        DecimalField unit_price
        CharField discount_type
        DecimalField discount_value
        CharField discount_reason
        DecimalField tax_percentage
        TextField notes
        PositiveIntegerField line_order
        CharField calculation_mode
        DecimalField target_total
    }
    Sale {
        ForeignKey items
        ForeignKey payment_allocations
        ForeignKey facturas
        ForeignKey comprobantes_arca
        CharField number
        DateTimeField date
        DateTimeField confirmed_at
        CharField customer_name
        CharField customer_phone
        CharField customer_email
        CharField customer_cuit
        CharField status
        CharField payment_status
        CharField fiscal_status
        CharField payment_method
        TextField notes
        TextField internal_notes
        TextField delivery_address
        DateField delivery_date
        DateTimeField stock_reserved_at
        DecimalField _cached_subtotal
        DecimalField _cached_discount
        DecimalField _cached_tax
        DecimalField _cached_total
        CharField global_discount_type
        DecimalField global_discount_value
        CharField global_discount_reason
        CharField sync_status
        CharField local_id
        PositiveIntegerField version
        DateTimeField sync_last_attempt
        DateTimeField sync_succeeded_at
        PositiveIntegerField sync_attempt_count
        TextField sync_error
        CharField conflict_resolution
        JSONField conflict_data
    }
    SaleItem {
        DecimalField quantity
        DecimalField unit_price
        DecimalField unit_cost
        CharField discount_type
        DecimalField discount_value
        CharField discount_reason
        DecimalField tax_percentage
        TextField notes
        PositiveIntegerField line_order
    }
    QuoteConversion {
        DateTimeField converted_at
        JSONField original_quote_data
        JSONField modifications
    }
    Category {
        ForeignKey subcategories
        ForeignKey products
        CharField name
        SlugField slug
        TextField description
        FileField image
        IntegerField order
    }
    Subcategory {
        CharField name
        SlugField slug
        TextField description
        JSONField faqs
    }
    Product {
        ForeignKey quoteitem
        ForeignKey sale_items
        ForeignKey images
        ForeignKey stock_movements
        ForeignKey count_items
        CharField code
        CharField sku
        CharField other_codes
        CharField name
        SlugField slug
        TextField description
        DecimalField price
        DecimalField cost
        DecimalField tax_rate
        CharField diameter
        CharField length
        CharField material
        CharField grade
        CharField norm
        CharField colour
        CharField product_type
        CharField form
        CharField thread_format
        CharField origin
        CharField brand
        CharField barcode
        CharField qr_code
        CharField gtin
        CharField mpn
        IntegerField stock_quantity
        IntegerField min_stock
        BooleanField stock_control_enabled
        CharField unit_of_sale
        IntegerField min_sale_unit
        DateField last_purchase_date
        DecimalField last_purchase_price
        FileField main_image
        CharField condition
        CharField meta_title
        TextField meta_description
        CharField meta_keywords
        CharField google_category
        IntegerField sold_count
    }
    PriceList {
        CharField name
        CharField list_type
        DecimalField percentage
        TextField description
        IntegerField priority
    }
    ProductImage {
        FileField image
        CharField alt_text
        BooleanField is_main
        IntegerField order
    }
    StockMovement {
        CharField movement_type
        PositiveIntegerField quantity
        CharField reference
        TextField notes
        IntegerField previous_stock
        IntegerField new_stock
    }
    StockCount {
        ForeignKey items
        DateField count_date
        CharField status
        TextField notes
    }
    StockCountItem {
        IntegerField expected_quantity
        IntegerField counted_quantity
        TextField notes
    }
    Payment {
        ForeignKey allocations
        DecimalField amount
        CharField method
        CharField status
        CharField reference
        DateField date
        TextField notes
    }
    PaymentAllocation {
        DecimalField allocated_amount
        TextField notes
    }
    Invoice {
        ForeignKey payment_allocations
        ForeignKey items
        UUIDField uuid
        CharField number
        IntegerField tipo_comprobante
        IntegerField punto_venta
        IntegerField numero_secuencial
        CharField cliente_cuit
        CharField cliente_razon_social
        CharField cliente_condicion_iva
        CharField cliente_domicilio
        DecimalField subtotal
        DecimalField descuento_total
        DecimalField neto_gravado
        DecimalField monto_iva
        DecimalField monto_no_gravado
        DecimalField monto_exento
        DecimalField total
        CharField cae
        DateField cae_vencimiento
        CharField estado_fiscal
        TextField observaciones_afip
        DateField fecha_emision
        DateField fecha_vto_pago
        TextField observaciones
    }
    InvoiceItem {
        CharField producto_nombre
        CharField producto_codigo
        DecimalField cantidad
        DecimalField precio_unitario
        DecimalField descuento
        DecimalField subtotal
        DecimalField alicuota_iva
        DecimalField monto_iva
        DecimalField total
        PositiveIntegerField numero_linea
    }
    WSAAToken {
        CharField cuit
        CharField servicio
        CharField ambiente
        TextField token
        TextField sign
        DateTimeField generado_en
        DateTimeField expira_en
    }
    ConfiguracionARCA {
        ForeignKey comprobante
        CharField empresa_cuit
        CharField ambiente
        CharField ruta_certificado
        CharField password_certificado
        CharField razon_social
        CharField email_contacto
        IntegerField punto_venta
        BooleanField activo
        DateTimeField creado_en
        DateTimeField actualizado_en
    }
    Comprobante {
        ForeignKey renglones
        ForeignKey logarca
        IntegerField tipo_compr
        IntegerField punto_venta
        IntegerField numero
        DateField fecha_compr
        IntegerField cbte_asoc_tipo
        IntegerField cbte_asoc_pto_vta
        IntegerField cbte_asoc_numero
        DateField fecha_vto_pago
        IntegerField doc_cliente_tipo
        CharField doc_cliente
        CharField razon_social_cliente
        IntegerField condicion_iva_receptor
        DecimalField monto_neto
        DecimalField monto_iva
        DecimalField monto_total
        CharField cae
        DateField fecha_vto_cae
        CharField estado
        JSONField respuesta_arca_json
        TextField error_msg
        DateTimeField creado_en
        DateTimeField actualizado_en
        CharField usuario_creacion
    }
    ComprobRenglon {
        IntegerField numero_linea
        CharField descripcion
        DecimalField cantidad
        DecimalField precio_unitario
        DecimalField subtotal
        DecimalField alicuota_iva
    }
    LogARCA {
        CharField tipo
        DateTimeField timestamp
        CharField cuit
        CharField servicio
        TextField request_xml
        TextField response_xml
        IntegerField response_code
        TextField error
    }
    SupplierTag {
        CharField name
        SlugField slug
        CharField color
    }
    Supplier {
        ForeignKey products
        ForeignKey expenses
        CharField business_name
        CharField trade_name
        CharField cuit
        CharField tax_condition
        CharField email
        CharField phone
        CharField mobile
        CharField website
        CharField address
        CharField city
        CharField state
        CharField zip_code
        CharField bank_name
        CharField cbu
        CharField bank_alias
        CharField contact_person
        CharField contact_email
        CharField contact_phone
        IntegerField payment_term
        IntegerField payment_day_of_month
        DecimalField early_payment_discount
        IntegerField delivery_days
        TextField notes
        DateField last_price_list_date
        DateField last_purchase_date
        DecimalField last_purchase_amount
        DecimalField total_purchased
        DecimalField current_debt
    }
    ExpenseCategory {
        ForeignKey expenses
        CharField name
        CharField type
        TextField description
    }
    Expense {
        CharField description
        DecimalField amount_neto
        DecimalField amount_iva
        DecimalField amount_total
        DateField expense_date
        DateField payment_date
        BooleanField is_paid
        PositiveSmallIntegerField period_year
        PositiveSmallIntegerField period_month
        BooleanField is_recurring
        CharField recurrence
        TextField notes
    }
    FinancialSnapshot {
        CharField type
        PositiveSmallIntegerField period_year
        PositiveSmallIntegerField period_month
        JSONField data
        DateTimeField generated_at
        BooleanField is_stale
    }
    User }o--o{ Group : "groups"
    User }o--o{ Permission : "user_permissions"
    UserLog }o--|| User : "user"
    RegistrationRequest }o--|| User : "reviewed_by"
    AuditLog }o--|| User : "user"
    AuditLog }o--|| ContentType : "content_type"
    Customer }o--|| CustomerSegment : "customer_segment"
    CustomerNote }o--|| Customer : "customer"
    Quote ||--|| Sale : "converted_sale"
    Quote ||--|| QuoteConversion : "conversion"
    Quote }o--|| Customer : "customer"
    QuoteItem }o--|| Quote : "quote"
    QuoteItem }o--|| Product : "product"
    Sale ||--|| QuoteConversion : "source_quote_conversion"
    Sale }o--|| Customer : "customer"
    Sale ||--|| Quote : "quote"
    Sale }o--|| User : "stock_reserved_by"
    Sale }o--|| CustomerSegment : "customer_segment_discount"
    SaleItem }o--|| Sale : "sale"
    SaleItem }o--|| Product : "product"
    QuoteConversion ||--|| Quote : "quote"
    QuoteConversion ||--|| Sale : "sale"
    QuoteConversion }o--|| User : "converted_by"
    Subcategory }o--o{ Product : "products"
    Subcategory }o--|| Category : "category"
    Product }o--|| Category : "category"
    Product }o--|| Supplier : "supplier"
    Product }o--o{ Subcategory : "subcategories"
    ProductImage }o--|| Product : "product"
    StockMovement }o--|| Product : "product"
    StockCount }o--|| User : "counted_by"
    StockCountItem }o--|| StockCount : "stock_count"
    StockCountItem }o--|| Product : "product"
    Payment }o--|| Customer : "customer"
    PaymentAllocation }o--|| Payment : "payment"
    PaymentAllocation }o--|| Sale : "sale"
    PaymentAllocation }o--|| Invoice : "invoice"
    Invoice }o--|| Sale : "sale"
    Invoice ||--|| Comprobante : "comprobante_arca"
    Invoice }o--|| Customer : "customer"
    Invoice }o--|| User : "emitida_por"
    InvoiceItem }o--|| Invoice : "invoice"
    Comprobante ||--|| Invoice : "factura"
    Comprobante }o--|| ConfiguracionARCA : "empresa_cuit"
    Comprobante }o--|| Sale : "sale"
    ComprobRenglon }o--|| Comprobante : "comprobante"
    LogARCA }o--|| Comprobante : "comprobante"
    SupplierTag }o--o{ Supplier : "suppliers"
    Supplier }o--o{ SupplierTag : "tags"
    Expense }o--|| ExpenseCategory : "category"
    Expense }o--|| Supplier : "supplier"
```