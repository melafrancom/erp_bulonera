from django.db import models
from common.models import BaseModel

class Invoice(BaseModel):
    number = models.CharField(max_length=50)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return self.number
