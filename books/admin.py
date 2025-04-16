from django.contrib import admin
from .models import Book, Order, Genre, CartItem



admin.site.register(Book)
admin.site.register(Order)
admin.site.register(Genre)
admin.site.register(CartItem)