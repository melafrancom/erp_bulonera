"""
Servicios de negocio para la app Suppliers.

Contiene la lógica de negocio separada de las vistas:
- SupplierService: CRUD y operaciones sobre proveedores
- SupplierImportService: Importación masiva desde Excel/CSV
"""

import os
import logging
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from suppliers.models import Supplier, SupplierTag

logger = logging.getLogger('api')


# =============================================================================
# SupplierService
# =============================================================================

class SupplierService:
    """Lógica de negocio de proveedores."""

    @staticmethod
    @transaction.atomic
    def create_supplier(data: dict, user) -> Supplier:
        """
        Crea un proveedor nuevo.

        Args:
            data: dict con campos del proveedor
            user: usuario que crea

        Returns:
            Supplier creado

        Raises:
            ValidationError si el CUIT ya existe o datos inválidos
        """
        tags = data.pop('tags', [])

        supplier = Supplier(**data)
        supplier.created_by = user
        supplier.full_clean()
        supplier.save()

        if tags:
            supplier.tags.set(tags)

        logger.info(
            f"Proveedor creado: {supplier.business_name} (CUIT: {supplier.cuit})",
            extra={'user_id': user.id, 'supplier_id': supplier.id}
        )
        return supplier

    @staticmethod
    @transaction.atomic
    def update_supplier(supplier: Supplier, data: dict, user) -> Supplier:
        """
        Actualiza un proveedor existente.

        Args:
            supplier: instancia de Supplier
            data: dict con campos a actualizar
            user: usuario que actualiza

        Returns:
            Supplier actualizado
        """
        tags = data.pop('tags', None)

        for field, value in data.items():
            setattr(supplier, field, value)

        supplier.updated_by = user
        supplier.full_clean()
        supplier.save()

        if tags is not None:
            supplier.tags.set(tags)

        logger.info(
            f"Proveedor actualizado: {supplier.business_name}",
            extra={'user_id': user.id, 'supplier_id': supplier.id}
        )
        return supplier

    @staticmethod
    def soft_delete(supplier: Supplier, user) -> Supplier:
        """Soft delete de un proveedor."""
        supplier.delete(user=user)
        logger.info(
            f"Proveedor eliminado (soft): {supplier.business_name}",
            extra={'user_id': user.id, 'supplier_id': supplier.id}
        )
        return supplier

    @staticmethod
    def get_supplier_products(supplier: Supplier):
        """Retorna los productos del proveedor."""
        from products.models import Product
        return Product.objects.filter(supplier=supplier)

    @staticmethod
    def get_supplier_stats(supplier: Supplier) -> dict:
        """
        Retorna estadísticas del proveedor.

        Returns:
            dict con total_purchased, current_debt, products_count, etc.
        """
        from products.models import Product
        products_count = Product.objects.filter(supplier=supplier).count()

        return {
            'products_count': products_count,
            'total_purchased': str(supplier.total_purchased),
            'current_debt': str(supplier.current_debt),
            'last_purchase_date': supplier.last_purchase_date,
            'last_purchase_amount': (
                str(supplier.last_purchase_amount)
                if supplier.last_purchase_amount else None
            ),
            'has_debt': supplier.has_debt,
            'payment_term_display': supplier.payment_term_display,
        }


# =============================================================================
# SupplierImportService
# =============================================================================

class SupplierImportService:
    """Importación masiva de proveedores desde archivos Excel/CSV."""

    REQUIRED_COLUMNS = ['business_name', 'cuit']
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    VALID_EXTENSIONS = ['.xlsx', '.csv']

    # Mapeo de columnas del archivo → campos del modelo
    COLUMN_MAP = {
        'business_name': 'business_name',
        'razon_social': 'business_name',
        'trade_name': 'trade_name',
        'nombre_comercial': 'trade_name',
        'cuit': 'cuit',
        'tax_condition': 'tax_condition',
        'condicion_iva': 'tax_condition',
        'email': 'email',
        'phone': 'phone',
        'telefono': 'phone',
        'mobile': 'mobile',
        'celular': 'mobile',
        'address': 'address',
        'direccion': 'address',
        'city': 'city',
        'ciudad': 'city',
        'state': 'state',
        'provincia': 'state',
        'zip_code': 'zip_code',
        'codigo_postal': 'zip_code',
        'bank_name': 'bank_name',
        'banco': 'bank_name',
        'cbu': 'cbu',
        'bank_alias': 'bank_alias',
        'alias': 'bank_alias',
        'contact_person': 'contact_person',
        'contacto': 'contact_person',
        'payment_term': 'payment_term',
        'plazo_pago': 'payment_term',
        'notes': 'notes',
        'observaciones': 'notes',
    }

    def validate_file(self, file) -> dict:
        """
        Valida el archivo antes de procesarlo.

        Returns:
            dict con 'valid' (bool) y 'error' (str) si hay problema
        """
        if not file:
            return {'valid': False, 'error': 'No se proporcionó archivo.'}

        # Validar extensión
        _, ext = os.path.splitext(file.name)
        if ext.lower() not in self.VALID_EXTENSIONS:
            return {
                'valid': False,
                'error': f'Extensión no soportada: {ext}. Use: {", ".join(self.VALID_EXTENSIONS)}'
            }

        # Validar tamaño
        if file.size > self.MAX_FILE_SIZE:
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            return {
                'valid': False,
                'error': f'Archivo demasiado grande. Máximo: {max_mb}MB'
            }

        return {'valid': True, 'error': None}

    def import_from_file(
        self,
        file_path: str,
        user_id: int,
        update_state_callback=None
    ) -> dict:
        """
        Importa proveedores desde un archivo Excel/CSV.

        Args:
            file_path: ruta absoluta del archivo
            user_id: ID del usuario que importa
            update_state_callback: función para actualizar progreso (Celery)

        Returns:
            dict con reporte de importación
        """
        import pandas as pd
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user = User.objects.get(id=user_id)
        _, ext = os.path.splitext(file_path)

        # Leer archivo
        try:
            if ext.lower() == '.csv':
                df = pd.read_csv(file_path, dtype=str)
            else:
                df = pd.read_excel(file_path, dtype=str)
        except Exception as e:
            logger.error(f"Error leyendo archivo: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': f'Error leyendo archivo: {str(e)}',
                'total': 0, 'created': 0, 'updated': 0, 'errors': 0,
            }

        # Normalizar nombres de columnas
        df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]

        # Verificar columnas requeridas
        mapped_columns = set()
        for col in df.columns:
            if col in self.COLUMN_MAP:
                mapped_columns.add(self.COLUMN_MAP[col])

        missing = set(self.REQUIRED_COLUMNS) - mapped_columns
        if missing:
            return {
                'status': 'error',
                'error': f'Columnas requeridas faltantes: {", ".join(missing)}',
                'total': 0, 'created': 0, 'updated': 0, 'errors': 0,
            }

        total = len(df)
        created = 0
        updated = 0
        errors = 0
        error_details = []

        for idx, row in df.iterrows():
            row_num = idx + 2  # +2 por header y 0-index
            try:
                result = self._process_row(row, user)
                if result == 'created':
                    created += 1
                elif result == 'updated':
                    updated += 1
            except Exception as e:
                errors += 1
                error_details.append({
                    'row': row_num,
                    'error': str(e),
                    'data': {
                        'business_name': row.get('business_name', row.get('razon_social', '')),
                        'cuit': row.get('cuit', ''),
                    }
                })
                logger.warning(
                    f"Error en fila {row_num}: {e}",
                    extra={'user_id': user_id, 'row': row_num}
                )

            # Actualizar progreso si hay callback (Celery)
            if update_state_callback and total > 0:
                progress = int(((idx + 1) / total) * 100)
                update_state_callback(
                    state='PROGRESS',
                    meta={
                        'current': idx + 1,
                        'total': total,
                        'progress': progress,
                        'created': created,
                        'updated': updated,
                        'errors': errors,
                    }
                )

        report = {
            'status': 'completed',
            'total': total,
            'created': created,
            'updated': updated,
            'errors': errors,
            'error_details': error_details[:50],  # Limitar detalles de errores
        }

        logger.info(
            f"Importación completada: {total} filas, "
            f"{created} creados, {updated} actualizados, {errors} errores",
            extra={'user_id': user_id}
        )
        return report

    @transaction.atomic
    def _process_row(self, row, user) -> str:
        """
        Procesa una fila del archivo y crea/actualiza un proveedor.

        Returns:
            'created' o 'updated'
        """
        # Mapear columnas
        data = {}
        for col_name, value in row.items():
            col_key = col_name.strip().lower().replace(' ', '_')
            if col_key in self.COLUMN_MAP:
                field_name = self.COLUMN_MAP[col_key]
                if pd.notna(value) and str(value).strip():
                    data[field_name] = str(value).strip()

        # Validar campos requeridos
        if 'business_name' not in data or not data['business_name']:
            raise ValidationError("business_name es obligatorio.")
        if 'cuit' not in data or not data['cuit']:
            raise ValidationError("cuit es obligatorio.")

        # Normalizar CUIT (agregar guiones si no los tiene)
        cuit = data['cuit'].replace('-', '').replace(' ', '')
        if len(cuit) == 11:
            data['cuit'] = f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"

        # Convertir payment_term a int
        if 'payment_term' in data:
            try:
                data['payment_term'] = int(data['payment_term'])
            except (ValueError, TypeError):
                data['payment_term'] = 0

        # Normalizar tax_condition
        if 'tax_condition' in data:
            tc = data['tax_condition'].upper().strip()
            valid_conditions = {'RI', 'MONO', 'EX'}
            if tc not in valid_conditions:
                # Intentar mapear nombres completos
                tc_map = {
                    'RESPONSABLE INSCRIPTO': 'RI',
                    'MONOTRIBUTISTA': 'MONO',
                    'EXENTO': 'EX',
                }
                data['tax_condition'] = tc_map.get(tc, 'RI')
            else:
                data['tax_condition'] = tc

        # Buscar si ya existe por CUIT
        cuit_value = data['cuit']
        existing = Supplier.objects.filter(cuit=cuit_value).first()

        if existing:
            # Actualizar existente
            for field, value in data.items():
                if field != 'cuit':  # No actualizar CUIT
                    setattr(existing, field, value)
            existing.updated_by = user
            existing.full_clean()
            existing.save()
            return 'updated'
        else:
            # Crear nuevo
            supplier = Supplier(**data)
            supplier.created_by = user
            supplier.full_clean()
            supplier.save()
            return 'created'


# Importar pandas solo cuando se necesite
try:
    import pandas as pd
except ImportError:
    pd = None
