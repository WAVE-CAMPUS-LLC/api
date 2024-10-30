from django.shortcuts import render, redirect
from django.http import JsonResponse
import json

# Create your views here.
def checkoutView(request):
    return render(request, "eventTicketsApp/checkout.html")

def updateCart(request):
    if request.method == "POST":
        data = json.loads(request.body)
        ticket_id = data['ticket_id']
        ticket_name = data['ticket_name']
        ticket_price = data['ticket_price']
        action = data['action']

        # Get the current cart from session or create a new one
        cart = request.session.get("cart", {})

        if action == "add":
            if ticket_id in cart:
                cart[ticket_id]["quantity"] += 1
            else:
                cart[ticket_id] = {"name": ticket_name, "price": ticket_price, "quantity": 1}
        elif action == "remove":
            if ticket_id in cart:
                cart[ticket_id]["quantity"] -= 1
                if cart[ticket_id]["quantity"] <= 0:
                    del cart[ticket_id]

        # Update the session cart
        request.session["cart"] = cart

        # Return updated cart data
        return JsonResponse({"cart": cart})