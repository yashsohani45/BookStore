from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Book, Order, Genre, CartItem
from django.urls import reverse_lazy
from django.db.models import Q  # for search method
from django.http import JsonResponse
import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from .models import Profile
from .forms import ProfileForm
from django.core.mail import send_mail
from .models import Order



class BooksListView(ListView):
    model = Book
    template_name = 'list.html'
    context_object_name = 'books'

    def get_queryset(self):
        genre = self.request.GET.get('genre')
        if genre:
            return Book.objects.filter(genres__name=genre)  # Filter books by selected genre
        return Book.objects.all()  # Show all books if no genre is selected


class BooksDetailView(DetailView):
    model = Book
    template_name = 'detail.html'

    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from_used = self.request.GET.get('from_used') == 'true'
        context['show_condition'] = from_used
        return context


from django.db.models import Q

class SearchResultsListView(ListView):
    model = Book
    template_name = 'search_results.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        return Book.objects.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(genres__name__icontains=query)
        ).distinct()



class BookCheckoutView(LoginRequiredMixin, DetailView):
    model = Book
    template_name = 'checkout.html'
    login_url = 'login'


def paymentComplete(request):
    body = json.loads(request.body)
    print('BODY:', body)
    product = Book.objects.get(id=body['productId'])
    Order.objects.create(
        product=product
    )
    return JsonResponse('Payment completed!', safe=False)


# View to list all books of a selected genre
class GenreBooksListView(ListView):
    model = Book
    template_name = 'books_by_genre.html'
    context_object_name = 'books'

    def get_queryset(self):
        self.genre = get_object_or_404(Genre, name=self.kwargs['genre_name'])
        return Book.objects.filter(genres=self.genre)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genre'] = self.genre  # Pass genre object to template
        return context


def books_by_genre(request, genre_id):
    genre = get_object_or_404(Genre, id=genre_id)
    books = Book.objects.filter(genres=genre)
    return render(request, 'books_by_genre.html', {'books': books, 'genre': genre})

class UsedBooksListView(ListView):
    model = Book
    template_name = 'used_books.html'
    context_object_name = 'books'

    def get_queryset(self):
        return Book.objects.filter(secondhand=True)  # Filter only used books

@login_required
def add_to_cart(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    cart_item, created = CartItem.objects.get_or_create(user=request.user, book=book)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    return redirect('cart')

@login_required
def cart(request):
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(item.book.price * item.quantity for item in cart_items)
    
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        profile.address = request.POST.get('address')
        profile.city = request.POST.get('city')
        profile.postal_code = request.POST.get('postal_code')
        profile.save()
        messages.success(request, 'Shipping address updated!')

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total': total,
        'profile': profile
    })

@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    item.delete()
    return redirect('cart')


@csrf_exempt
@login_required
def paymentComplete(request):
    body = json.loads(request.body)
    CartItem.objects.filter(user=request.user).delete()
    messages.success(request, 'Payment completed successfully!')
    return JsonResponse('Payment completed!', safe=False)


@login_required
def checkout(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    return render(request, 'checkout.html', {'profile': profile})


@login_required
def cart_checkout(request):
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(item.book.price * item.quantity for item in cart_items)

    profile, created = Profile.objects.get_or_create(user=request.user)
    shipping_address = profile.address  # Optional: pass separately if needed

    return render(request, 'cart_checkout.html', {
        'cart_items': cart_items,
        'total': total,
        'profile': profile,
        'shipping_address': shipping_address
    })

@csrf_exempt
@login_required
def cart_payment_complete(request):
    body = json.loads(request.body)
    print('Cart Order BODY:', body)
    
    # You can store a record of this order
    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        Order.objects.create(product=item.book)
    
    cart_items.delete()
    return JsonResponse('Cart Payment completed!', safe=False)

@login_required
def profile_view(request):
    # Ensure profile exists
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        profile.address = request.POST.get('address')
        profile.phone_number = request.POST.get('phone_number')
        profile.city = request.POST.get('city')
        profile.postal_code = request.POST.get('postal_code')
        profile.save()
        return redirect('profile')

    return render(request, 'profile.html', {'profile': profile})

@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'profile.html', {'form': form})

def cart_payment_complete(request):
    body = json.loads(request.body)
    payment_id = body['paymentID']
    cart = request.session.get('cart', {})
    user = request.user

    # Collect cart data as plain text (or serialize better)
    items_summary = ""
    total = 0
    for book_id, item in cart.items():
        items_summary += f"{item['title']} (x{item['quantity']}) - ₹{item['price']}\n"
        total += item['price'] * item['quantity']

    # Save order
    order = Order.objects.create(
        user=user,
        items=items_summary,
        total_amount=total,
        payment_id=payment_id
    )

    # Send email confirmation
    send_mail(
        subject='Your Bookstore Order Confirmation',
        message=f"Thanks for your purchase, {user.username}!\n\n"
                f"Order Summary:\n{items_summary}\nTotal: ₹{total}\n\n"
                f"Payment ID: {payment_id}",
        from_email='noreply@yourbookstore.com',
        recipient_list=[user.email],
        fail_silently=False,
    )

    # Clear cart
    request.session['cart'] = {}

    return JsonResponse({'message': 'Payment completed!'})

def order_confirmation(request):
    return render(request, 'confirmation.html')