from django.contrib import admin
from .models import Book, Order, Genre, CartItem, CompletedOrder
from django.db.models import Sum, Count

@admin.register(CompletedOrder)
class CompletedOrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_id',
        'user',
        'total_price',
        'ordered_at',
        'status',
        'get_total_revenue',
        'get_genre_revenue',  # Add this to the list_display
    )
    list_filter = (
        'status',
        'ordered_at',
        'user',
    )
    search_fields = ('order_id', 'user__username')

    def get_total_revenue(self, obj):
        total_revenue = CompletedOrder.objects.aggregate(Sum('total_price'))['total_price__sum']
        return total_revenue or 0

    get_total_revenue.short_description = 'Total Revenue'

    def get_genre_revenue(self, obj):
        genre_revenue = {}
        for book in obj.books.all():
          for genre in book.genres.all():
            genre_revenue[genre.name] = genre_revenue.get(genre.name, 0) + book.price
        return ', '.join([f"{genre}: ₹{amount}" for genre, amount in genre_revenue.items()])






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
