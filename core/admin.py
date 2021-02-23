from django.contrib import admin
from .models import (
    Payment,
    Item,
    OrderItem,
    Order,
    BillingAddress,
    Coupon,
)
# Register your models here.


class OrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'ordered']


admin.site.register(Item)
admin.site.register(OrderItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(BillingAddress)
admin.site.register(Payment)
admin.site.register(Coupon)
