from django.db import models
from common.models import BaseModel

class Stock(BaseModel):
    product = models.OneToOneField('products.Product', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.product.name}: {self.quantity}"

class StockMovement(BaseModel):
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255)
    
    def __str__(self):
        return f"{self.product.name}: {self.quantity}"
