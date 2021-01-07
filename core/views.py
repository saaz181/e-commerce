from django.shortcuts import render
from .models import Item


def item_list(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "core/home-page.html", context)


def product(request):
    return render(request, 'core/product-page.html', context={})


def check_out(request):
    return render(request, 'core/checkout-page.html', context={})



