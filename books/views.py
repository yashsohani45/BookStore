from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.http import JsonResponse
from django.contrib import messages
import json
from django.contrib.auth.mixins import LoginRequiredMixin  # Add this line


from .models import Book, Order, Genre, CartItem, Profile, Comment
from .forms import ProfileForm


class BooksListView(ListView):
    model = Book
    template_name = 'list.html'
    context_object_name = 'books'

    def get_queryset(self):
        genre = self.request.GET.get('genre')
        if genre:
            return Book.objects.filter(genres__name=genre)
        return Book.objects.all()


class BooksDetailView(DetailView):
    model = Book
    template_name = 'detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from_used = self.request.GET.get('from_used') == 'true'
        context['show_condition'] = from_used
        context['comments'] = Comment.objects.filter(book=self.object, parent=None).order_by('-created_at').prefetch_related('replies')
        return context


@login_required
def post_comment(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        parent_id = request.POST.get('parent_id')

        parent = None
        if parent_id:
            try:
                parent = Comment.objects.get(id=parent_id)
            except Comment.DoesNotExist:
                parent = None  # fallback if parent doesn't exist

        if content:
            Comment.objects.create(user=request.user, book=book, content=content, parent=parent)

    return redirect('book_detail', pk=book.id)


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


@csrf_exempt
@login_required
def paymentComplete(request):
    body = json.loads(request.body)
    CartItem.objects.filter(user=request.user).delete()
    messages.success(request, 'Payment completed successfully!')
    return JsonResponse('Payment completed!', safe=False)


class GenreBooksListView(ListView):
    model = Book
    template_name = 'books_by_genre.html'
    context_object_name = 'books'

    def get_queryset(self):
        self.genre = get_object_or_404(Genre, name=self.kwargs['genre_name'])
        return Book.objects.filter(genres=self.genre)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genre'] = self.genre
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
        return Book.objects.filter(secondhand=True)


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


@login_required
def checkout(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    return render(request, 'checkout.html', {'profile': profile})


@login_required
def cart_checkout(request):
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(item.book.price * item.quantity for item in cart_items)

    profile, created = Profile.objects.get_or_create(user=request.user)

    return render(request, 'cart_checkout.html', {
        'cart_items': cart_items,
        'total': total,
        'profile': profile,
        'shipping_address': profile.address
    })


@csrf_exempt
@login_required
def cart_payment_complete(request):
    body = json.loads(request.body)
    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        Order.objects.create(product=item.book)
    cart_items.delete()
    return JsonResponse('Cart Payment completed!', safe=False)


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


@csrf_exempt
@login_required
def cart_payment_complete_session(request):
    body = json.loads(request.body)
    payment_id = body['paymentID']
    cart = request.session.get('cart', {})
    user = request.user

    items_summary = ""
    total = 0
    for book_id, item in cart.items():
        items_summary += f"{item['title']} (x{item['quantity']}) - ₹{item['price']}\n"
        total += item['price'] * item['quantity']

    order = Order.objects.create(
        user=user,
        items=items_summary,
        total_amount=total,
        payment_id=payment_id
    )

    send_mail(
        subject='Your Bookstore Order Confirmation',
        message=f"Thanks for your purchase, {user.username}!\n\n"
                f"Order Summary:\n{items_summary}\nTotal: ₹{total}\n\n"
                f"Payment ID: {payment_id}",
        from_email='noreply@yourbookstore.com',
        recipient_list=[user.email],
        fail_silently=False,
    )

    request.session['cart'] = {}
    return JsonResponse({'message': 'Payment completed!'})


def order_confirmation(request):
    return render(request, 'confirmation.html')

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Check if the user is the author of the comment
    if request.user == comment.user:
        comment.delete()  # Delete the comment
    
    return redirect('book_detail', pk=comment.book.id)