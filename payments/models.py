from django.db import models
from common.models import BaseModel

class Payment(BaseModel):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='pending')
    
    def __str__(self):
        return f"Payment {self.id}: {self.amount}"

class PaymentAllocation(BaseModel):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    sale = models.ForeignKey('sales.Sale', on_delete=models.CASCADE)
    allocated_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"Alloc {self.id}: {self.allocated_amount}"
