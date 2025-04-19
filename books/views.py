from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.http import JsonResponse
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth.mixins import LoginRequiredMixin
import json
from .models import Book, Order, Genre, CartItem, Profile, Comment, CompletedOrder
from .forms import ProfileForm
from .models import Book, Language
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.timezone import now
import pdfkit


def books_by_language(request, language_name):
    language = get_object_or_404(Language, name=language_name)
    books = Book.objects.filter(language=language)
    return render(request, 'books_by_language.html', {
        'language': language,
        'books': books
    })

def profile_view(request):
    # your view logic here
    return render(request, 'profile.html')



from .models import Order

@login_required
def user_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'user_orders.html', {'orders': orders})




@csrf_exempt
@login_required
def cart_payment_complete(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("🔔 Received data from Razorpay:", data)

            user = request.user
            cart_items = CartItem.objects.filter(user=user)

            if not cart_items.exists():
                return JsonResponse({'status': 'failed', 'message': 'Cart is empty'}, status=400)

            # Build order summary and calculate total
            items_summary = ""
            total = 0
            for item in cart_items:
                line = f"{item.book.title} (x{item.quantity}) - ₹{item.book.price * item.quantity}\n"
                items_summary += line
                total += item.book.price * item.quantity

            # Create Order (basic record for payment info)
            order = Order.objects.create(
                user=user,
                items=items_summary,
                total_amount=total,
                payment_id=data.get("paymentID", "N/A")
            )

            # Create CompletedOrder (for admin/revenue tracking)
            completed_order = CompletedOrder.objects.create(
                user=user,
                total_price=total
            )
            for item in cart_items:
                completed_order.books.add(item.book)

            completed_order.save()

            # Clear the cart
            cart_items.delete()

            print(f"✅ Order #{order.id} and CompletedOrder #{completed_order.id} created for {user.username}")

            return JsonResponse({'status': 'success', 'order_id': order.id})

        except Exception as e:
            print("❌ Error in cart_payment_complete:", e)
            return JsonResponse({'status': 'failed', 'message': 'Something went wrong'}, status=500)

    return JsonResponse({'status': 'failed', 'message': 'Invalid request'}, status=400)

def checkout_view(request, book_id):
    book = Book.objects.get(pk=book_id)

    if request.method == 'POST':
        order = CompletedOrder.objects.create(
            user=request.user,
            total_price=book.price
        )
        order.books.add(book)
        order.save()
        book.book_available = False
        book.save()

        return redirect('order_success', order_id=order.order_id)

    return render(request, 'checkout.html', {'book': book})


class BooksListView(ListView):
    model = Book
    template_name = 'list.html'
    context_object_name = 'books'

    def get_queryset(self):
        genre = self.request.GET.get('genre')
        if genre:
            return Book.objects.filter(genres__name=genre).order_by('?')  # Order by latest added books
        return Book.objects.all().order_by('?')  # Default to ordering by latest books



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
                parent = None

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
    if request.user == comment.user:
        comment.delete()
    return redirect('book_detail', pk=comment.book.id)


@login_required
def order_history(request):
    orders = CompletedOrder.objects.filter(user=request.user).order_by('-ordered_at')
    return render(request, 'order_history.html', {'orders': orders})

@login_required
def download_invoice(request):
    latest_order = Order.objects.filter(user=request.user).order_by('-created_at').first()
    
    if not latest_order:
        return HttpResponse("No order found.", status=404)

    user_profile = request.user.profile
    rendered = render_to_string("invoice_template.html", {
        "order": latest_order,
        "profile": user_profile,
        "date_time": now().strftime("%d-%m-%Y %I:%M %p")
    })

    path_to_wkhtmltopdf = r'C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)

    pdf = pdfkit.from_string(rendered, False, configuration=config)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{latest_order.id}.pdf"'
    return response

