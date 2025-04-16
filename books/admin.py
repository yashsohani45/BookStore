from django.contrib import admin
from .models import Book, Order, Genre, CartItem



admin.site.register(Book)
admin.site.register(Order)
admin.site.register(Genre)
admin.site.register(CartItem)

from .models import Comment

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'content', 'created_at', 'parent')
    list_filter = ('created_at',)
    search_fields = ('content', 'user__username', 'book__title')
