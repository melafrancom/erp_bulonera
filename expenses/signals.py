"""
Signals para la aplicación de Gastos.

Nota de arquitectura:
La invalidación de reportes financieros (P&L, Cash Flow) al crear, modificar
o eliminar un Expense es gestionada de manera centralizada por `reports/signals.py`,
la cual marca `FinancialSnapshot.is_stale = True` para los períodos correspondientes.
"""

# Espacio reservado para futuros signals específicos del módulo expenses
