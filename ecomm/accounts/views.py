from cmath import log
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from .models import Profile, Cart, CartItems
from products.models import *
import razorpay

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
from base.helpers import save_pdf  # Import the save_pdf function from your utils


def login_page(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_obj = User.objects.filter(username=email)

        if not user_obj.exists():
            messages.warning(request, "Account not found")
            return HttpResponseRedirect(request.path_info)
        
        if not user_obj[0].profile.is_email_verified:
            messages.warning(request, 'Your account is not verified.')
            return HttpResponseRedirect(request.path_info)
        
        user_obj = authenticate(username = email, password = password)
        if user_obj:
            login(request, user_obj)
            return redirect('/')

        messages.warning(request, "Invalid credentials")
        return HttpResponseRedirect(request.path_info)

    return render(request, 'accounts/login.html')

def register_page(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        user_obj = User.objects.filter(username=email)

        if user_obj.exists():
            messages.warning(request, "Email is already taken")
            return HttpResponseRedirect(request.path_info)
        
        user_obj = User.objects.create(first_name=first_name, last_name=last_name, email=email, username=email)
        user_obj.set_password(password)
        user_obj.save()

        messages.success(request, "An email has been sent on your mail.")
        return HttpResponseRedirect(request.path_info)
  
    return render(request, 'accounts/register.html')

def activate_email(request, email_token):
    try:
        user = Profile.objects.get(email_token = email_token)
        user.is_email_verified = True
        user.save()
        return redirect('/')
    except Exception as e:
        return HttpResponse('Invalid Email token')

def add_to_cart(request, uid):
    variant = request.GET.get('variant')
    product = Product.objects.get(uid = uid)
    user = request.user
    
    cart, _ = Cart.objects.get_or_create(user = user, is_paid = False)

    cart_item = CartItems.objects.create(cart=cart, product=product)

    if variant:
        variant = request.GET.get('variant')
        size_variant = SizeVariant.objects.get(size_name = variant)
        cart_item.size_variant = size_variant
        cart_item.save()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def remove_cart(request, cart_item_uid):
    try:
        cart_item = CartItems.objects.get(uid = cart_item_uid)
        cart_item.delete()
    except Exception as e:
        print(e)
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


from django.conf import settings

def cart(request):
    cart_obj = None
    try:
        cart_obj = Cart.objects.get(is_paid = False, user = request.user)
    except Exception as e:
        print(e)

    if request.method == 'POST':
        coupon = request.POST.get('coupon')
        coupon_obj = Coupon.objects.filter(coupon_code__icontains = coupon)

        if not coupon_obj.exists():
            messages.warning(request, 'Invalid coupon.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        if cart_obj.coupon:
            messages.warning(request, 'Coupon already exists.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        
        if cart_obj.get_cart_total() < coupon_obj[0].minimum_amount:
            messages.success(request, f'Amount must be greater than{coupon_obj[0].minimum_amount}.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        
        if coupon_obj[0].is_expired:
            messages.warning(request, f'Coupon expired.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        
        cart_obj.coupon = coupon_obj[0]
        cart_obj.save()

        messages.success(request, 'Coupon applied.')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    
    payment = None
    if cart_obj:
        client = razorpay.Client(auth=(settings.KEY, settings.SECRET))
        payment = client.order.create({'amount':cart_obj.get_cart_total()*100, 'currency':'INR', 'payment_capture':1})
        
        cart_obj.razor_pay_order_id = payment['id']
        cart_obj.save()

        print('******')
        print(payment)
        print('******')

    context = {'cart':cart_obj, 'payment': payment}
    return render(request,'accounts/cart.html', context)

def remove_coupon(request, cart_id):
    cart = Cart.objects.get(uid = cart_id)
    cart.coupon = None
    cart.save()
    messages.success(request, 'Coupon Removed.')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def success(request):
    order_id = request.GET.get('order_id')
    order_date = request.GET.get('created_at')
    cart = Cart.objects.get(razor_pay_order_id = order_id)
    cart.is_paid = True
    cart.save()
    # Generate context for the invoice
    context = {
        'order_num':order_id,
        'order_date':order_date,
        'order': cart,  # Pass the cart object as the order
        'customer': cart.user,  # Pass the user as the customer
        'items': cart.cart_items.all(),  # Pass the cart items
        'total_amount': cart.get_cart_total(),  # Pass the total amount
    }

    # Generate the PDF and save it
    file_name, success = save_pdf(context)

    if success:
        # Provide a link to download the generated invoice
        pdf_path = f"{settings.MEDIA_URL}{file_name}"
        return render(request, 'accounts/invoice_success.html', {'pdf_path': pdf_path})
    else:
        return HttpResponse("Failed to generate PDF", status=500)