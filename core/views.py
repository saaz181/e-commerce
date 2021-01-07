from django.shortcuts import render
from .models import Item
from django.views.generic import ListView, DetailView


# in our template we say {% for item in objects_list %}
class HomeView(ListView):
    model = Item
    template_name = "core/home-page.html"

class ProductDetailView(DetailView):
    model = Item
    template_name = "core/product-page.html"




''' def home(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "core/home-page.html", context)
 '''

''' def product(request):
    return render(request, 'core/product-page.html', context={})
 '''

def check_out(request):
    return render(request, 'core/checkout-page.html', context={})



