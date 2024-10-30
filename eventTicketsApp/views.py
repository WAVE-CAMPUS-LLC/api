from django.shortcuts import render, redirect
from django.http import JsonResponse
import json

# Create your views here.
def checkoutView(request):
    cart = request.session.get('cart', {})
    
    total_amount = sum(ticket['price'] * ticket['quantity'] for ticket in cart.values())

    # if request.method == 'POST':
    #     # Handle the form submission for payment
    #     payment_info = request.POST
    #     if process_payment(payment_info):  # Implement your payment processing logic
    #         return redirect('payment_success')  # Change this to your success page URL
    #     return render(request, "eventTicketsApp/checkout.html", {'error': 'Payment processing failed.', 'cart': cart, 'total_amount': total_amount})
    return render(request, "eventTicketsApp/checkout.html", {'cart': cart, 'total_amount': total_amount})

def updateCartView(request):
    if request.method == 'POST':
        
        # Get the cart data from the request
        cart_data = json.loads(request.body)
        
        # Save the cart data to the session
        request.session['cart'] = cart_data
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)