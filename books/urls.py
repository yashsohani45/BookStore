
from django.urls import path
from . import views
from .views import post_comment
from .views import BooksListView, BooksDetailView, BookCheckoutView, paymentComplete, SearchResultsListView, books_by_genre, GenreBooksListView, UsedBooksListView
from django.views.generic import TemplateView


urlpatterns = [
    path('', BooksListView.as_view(), name = 'list'),
    path('comment/delete/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    path('profile/', views.profile_view, name='profile'),
    path('book/<int:book_id>/comment/', views.post_comment, name='post_comment'),
    path('book/<int:book_id>/comment/', post_comment, name='post_comment'),
    path('book/<int:pk>/', views.BooksDetailView.as_view(), name='book_detail'),
    path('<int:pk>/', BooksDetailView.as_view(), name = 'detail'),
    path('<int:pk>/checkout/', BookCheckoutView.as_view(), name = 'checkout'),
    path('complete/', paymentComplete, name = 'complete'),
    path('search/', SearchResultsListView.as_view(), name = 'search_results'),
    path("genre/<int:genre_id>/", books_by_genre, name="books_by_genre"),
    path('genre/<str:genre_name>/', GenreBooksListView.as_view(), name='genre_books'),
    path('used-books/', UsedBooksListView.as_view(), name='used_books'),
    path('add-to-cart/<int:book_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('cart-checkout/', views.cart_checkout, name='cart_checkout'),
    path('cart-payment-complete/', views.cart_payment_complete, name='cart_payment_complete'),
    # path('profile/', views.profile_view, name='profile'),
    path('confirmation/', views.order_confirmation, name='order_confirmation'),
    path('order-history/', views.order_history, name='order_history'),
    path('my-orders/', views.user_orders, name='user_orders'),
    path('confirmation/', TemplateView.as_view(template_name='confirmation.html'), name='confirmation'),
    path('language/<str:language_name>/', views.books_by_language, name='books_by_language')
    


    
]