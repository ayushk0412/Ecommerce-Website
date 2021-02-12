from django.contrib import admin
from .models import Payment, Item, OrderItem, Order, BillingAddress
# Register your models here.

admin.site.register(Item)
admin.site.register(OrderItem)
admin.site.register(Order)
admin.site.register(BillingAddress)
admin.site.register(Payment)
