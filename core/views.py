from django.shortcuts import render, get_object_or_404
from .models import Item, OrderItem, Order
from django.views.generic import ListView, DetailView
from django.shortcuts import redirect
from django.utils import timezone
from django.contrib import messages

# in our template we say {% for item in objects_list %}
class HomeView(ListView):
    model = Item
    template_name = "core/home-page.html"

class ProductDetailView(DetailView):
    model = Item
    template_name = "core/product-page.html"


def check_out(request):
    return render(request, 'core/checkout-page.html', context={})


def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item = item, 
        user=request.user, 
        ordered=False
        )
    order_qs = Order.objects.filter(user=request.user, ordered=False)

    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, f"You have {order_item.quantity} from this item in your cart!")
            return redirect("core:product", slug=slug) 
    
        else:
            order.items.add(order_item)
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item was added to your cart!")
            return redirect("core:product", slug=slug) 

                
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart!")
        return redirect("core:product", slug=slug) 

def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                            item = item, 
                            user=request.user, 
                            ordered=False
                            )[0]      
            if order_item.quantity != 0:     
                order_item.quantity -= 1
                if order_item.quantity == 0:
                    order.items.remove(order_item)    
                order_item.save()
                messages.success(request, f"Item successfully deleted from your cart\nYou have {order_item.quantity} of this in your cart!")
                return redirect("core:product", slug=slug)               
        else:
            # add a message saying user doesn't have an order
            messages.error(request, f"Item isn't in your cart")
            return redirect("core:product", slug=slug)

    else:
        # add a message saying user doesn't have an order
        messages.info(request, f"You don't have active order")
        return redirect("core:product", slug=slug)

    