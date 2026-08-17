"""
Servicios de lógica de negocio para Gastos (OPEX).

Toda la lógica reside aquí. Las vistas solo enrutan.
"""
from django.db import transaction
from django.db.models import Sum, F, DecimalField
from decimal import Decimal
from django.utils import timezone
from .models import Expense, ExpenseCategory
from suppliers.models import Supplier


class ExpenseService:
    """Servicio centralizado para operaciones de Gastos."""

    @staticmethod
    @transaction.atomic
    def create_expense(data: dict, user) -> Expense:
        """
        Crea un gasto validando montos y asignando período.

        Args:
            data: {
                category_id, description, amount_neto, amount_iva,
                expense_date, payment_date?, is_paid, supplier_id?,
                is_recurring, recurrence, notes
            }
            user: Usuario que registra

        Returns:
            Expense: Gasto creado

        Raises:
            ExpenseCategory.DoesNotExist: Si categoría no existe
            ValueError: Si hay error de validación
        """
        # 1. Validar que category existe y está activa
        try:
            category = ExpenseCategory.objects.get(id=data['category_id'], is_active=True)
        except ExpenseCategory.DoesNotExist:
            raise ValueError(f"Categoría con ID {data['category_id']} no existe o está inactiva")

        # 2. Calcular amount_total = amount_neto + amount_iva
        amount_neto = Decimal(str(data['amount_neto']))
        amount_iva = Decimal(str(data.get('amount_iva', 0)))
        amount_total = amount_neto + amount_iva

        # 3. Si is_paid=True, validar que payment_date esté presente
        is_paid = data.get('is_paid', False)
        payment_date = data.get('payment_date')
        if is_paid and not payment_date:
            raise ValueError("Si es_pagado=True, debe especificar payment_date")

        # 4. Crear el Expense
        expense = Expense(
            category=category,
            description=data['description'],
            amount_neto=amount_neto,
            amount_iva=amount_iva,
            amount_total=amount_total,
            expense_date=data['expense_date'],
            payment_date=payment_date,
            is_paid=is_paid,
            supplier_id=data.get('supplier_id'),
            is_recurring=data.get('is_recurring', False),
            recurrence=data.get('recurrence', ''),
            notes=data.get('notes', ''),
            created_by=user,
        )

        # 5. Guardar (ejecuta clean() automáticamente)
        expense.save()

        return expense

    @staticmethod
    @transaction.atomic
    def update_expense(expense_id: int, data: dict, user) -> Expense:
        """
        Actualiza un gasto existente con bloqueo pesimista.
        """
        expense = Expense.objects.select_for_update().get(id=expense_id)

        # Actualizar campos
        if 'category_id' in data:
            try:
                expense.category = ExpenseCategory.objects.get(id=data['category_id'], is_active=True)
            except ExpenseCategory.DoesNotExist:
                raise ValueError(f"Categoría con ID {data['category_id']} no existe")

        if 'description' in data:
            expense.description = data['description']

        if 'amount_neto' in data:
            expense.amount_neto = Decimal(str(data['amount_neto']))
        if 'amount_iva' in data:
            expense.amount_iva = Decimal(str(data['amount_iva']))
        if 'amount_neto' in data or 'amount_iva' in data:
            expense.amount_total = expense.amount_neto + expense.amount_iva

        if 'expense_date' in data:
            expense.expense_date = data['expense_date']
        if 'payment_date' in data:
            expense.payment_date = data['payment_date']
        if 'is_paid' in data:
            expense.is_paid = data['is_paid']
        if 'supplier_id' in data:
            expense.supplier_id = data['supplier_id']
        if 'is_recurring' in data:
            expense.is_recurring = data['is_recurring']
        if 'recurrence' in data:
            expense.recurrence = data['recurrence']
        if 'notes' in data:
            expense.notes = data['notes']

        expense.updated_by = user
        expense.save()

        return expense

    @staticmethod
    @transaction.atomic
    def delete_expense(expense_id: int, user) -> None:
        """
        Soft-delete de un gasto con bloqueo pesimista.
        Impide eliminar gastos ya pagados.
        """
        expense = Expense.objects.select_for_update().get(id=expense_id)
        if expense.is_paid:
            raise ValueError(
                "No se puede eliminar un gasto ya pagado. "
                "Primero revierta el estado de pago."
            )
        expense.delete(user=user)

    @staticmethod
    @transaction.atomic
    def mark_as_paid(expense_id: int, payment_date, user) -> Expense:
        """
        Marca un gasto como pagado (para Cash Flow) con bloqueo pesimista.
        Acepta objeto date/datetime o string 'YYYY-MM-DD'.
        """
        from datetime import datetime, date

        if isinstance(payment_date, str):
            try:
                parsed_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError("Formato de fecha de pago inválido. Use YYYY-MM-DD")
        elif isinstance(payment_date, (datetime, date)):
            parsed_date = payment_date.date() if isinstance(payment_date, datetime) else payment_date
        else:
            raise ValueError("payment_date es requerido")

        expense = Expense.objects.select_for_update().get(id=expense_id)
        expense.is_paid = True
        expense.payment_date = parsed_date
        expense.updated_by = user
        expense.save()

        return expense

    @staticmethod
    def get_opex_summary(date_from, date_to) -> dict:
        """
        Agrega gastos por categoría para el P&L (usando monto neto sin IVA).

        Returns:
            {
                'total': Decimal,
                'by_category': {
                    'salary': Decimal,
                    'rent': Decimal,
                    ...
                }
            }
        """
        expenses = Expense.objects.filter(
            expense_date__range=[date_from, date_to],
            is_active=True,
        )

        total = expenses.aggregate(t=Sum('amount_neto'))['t'] or Decimal('0')

        by_category = {}
        for cat_type, cat_label in ExpenseCategory.CATEGORY_TYPES:
            cat_total = (
                expenses.filter(category__type=cat_type)
                .aggregate(t=Sum('amount_neto'))['t']
                or Decimal('0')
            )
            by_category[cat_type] = float(cat_total)

        return {
            'total': float(total),
            'by_category': by_category,
        }

    @staticmethod
    def get_unpaid_expenses():
        """Gastos devengados pero no pagados (cuentas a pagar)."""
        return Expense.objects.filter(is_paid=False, is_active=True).select_related('category', 'supplier')
