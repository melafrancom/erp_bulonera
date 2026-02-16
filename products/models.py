from django.db import models
from common.models import BaseModel

class Category(BaseModel):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class Product(BaseModel):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return self.name
        
    @property
    def current_cost(self):
        return self.cost
