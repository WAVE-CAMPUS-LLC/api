from django.shortcuts import render, redirect
from django.http import JsonResponse
import json

# Create your views here.
def checkoutView(request):
    
    return render(request, "eventTicketsApp/checkout.html")

