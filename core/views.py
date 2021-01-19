from django.shortcuts import render, get_object_or_404
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund
from django.views.generic import ListView, DetailView, View
from django.shortcuts import redirect
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import CheckoutForm, CouponForm, RefundForm
from django.conf import settings
import stripe
import random
import string

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_ref_code():
    return ''.join(random.choice(string.ascii_lowercase + string.digits, k=20))


# in our template we say {% for item in objects_list %}
class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "core/home-page.html"


class OrderSummary(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order

            }
        except ObjectDoesNotExist:
            messages.error(self.request, "You don't have an active order!")
            return redirect("/")
        return render(self.request, 'core/order_summary.html', context)
    

class ProductDetailView(DetailView):
    model = Item
    template_name = "core/product-page.html"


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            # form
            form = CheckoutForm()

            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FROM': True,

             }
            return render(self.request, 'core/checkout-page.html', context)
        
        except ObjectDoesNotExist:
            messages.info(self.request, "You don't have active order")
            return redirect("core:checkout")    
        
    
    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                street_address = form.cleaned_data.get("street_address")
                apartment_address = form.cleaned_data.get("apartment_address")
                country = form.cleaned_data.get("country")
                zip = form.cleaned_data.get("zip")
                
                # TODO: add functionality to these fields
                # same_Shipping_address = form.cleaned_data("same_billing_address")
                # save_info = form.cleaned_data("save_info")
                
                payment_option = form.cleaned_data.get("payment_option")
                billing_address = Address(
                    user=self.request.user,
                    street_address=street_address,
                    apartment_address=apartment_address,
                    country=country,
                    zip=zip,
                    address_type="B"
                    )
                billing_address.save()
                order.billing_address = billing_address
                order.save()
                if payment_option == 'S':
                    return redirect("core:payment", payment_option='stripe')
                elif payment_option == 'P':
                    return redirect("core:payment", payment_option='paypal')
                else:
                    messages.warning(self.request, "Invalid Payment option selected")
                    return redirect("core:checkout")
        
        except ObjectDoesNotExist:
            messages.error(self.request, "You don't have an active order!")
            return redirect("core:order-summary")

class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'STRIPE_PUBLIC_KEY' : settings.STRIPE_PUBLIC_KEY,
                'DISPLAY_COUPON_FROM': False,
                
            }
            return render(self.request, "core/payment.html", context)
        else:
            messages.warning(self.request, "You haven't added a billing address")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        token = self.request.POST.get('stripeToken')
        amount=int(order.get_total() * 100) #cents
        
        try:
            charge = stripe.Charge.create(
            amount=int(order.get_total() * 100), #cents
            currency="usd",
            source=token,
            )
            # Create the Payment
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            # assign payment to the order
            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()

            order.ordered = True
            order.payment = payment
            order.ref_code = create_ref_code()
            order.save()

            messages.success(self.request, "Your order was successful")
            return redirect("/")

        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            body = e.json_body
            err = body.get("error", {})
            messages.error(self.request, f"{err.get('message')}")
            return redirect("/")


        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.error(self.request, "Rate Limit Error")
            return redirect("/")
            
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.error(self.request, "Invalid Parameters")
            return redirect("/")

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.error(self.request, "Not Authenticated")
            return redirect("/")

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.error(self.request, "Network Error")
            return redirect("/")

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.error(self.request, "Something went wrong. You were not charged. Please Try Again")
            return redirect("/")

        except Exception as e:
            # send email to ourselves
            messages.error(self.request, "A serious error occurred. We have been notified")
            return redirect("/")

        


@login_required
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
            return redirect("core:order-summary") 
    
        else:
            order.items.add(order_item)
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item was added to your cart!")
            return redirect("core:order-summary") 

                
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart!")
        return redirect("core:order-summary") 

@login_required
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
            
            order.items.remove(order_item)    
            order_item.save()
            messages.success(request, f"Item successfully deleted from your cart")
            return redirect("core:order-summary")               
        else:
            # add a message saying user doesn't have an order
            messages.error(request, f"Item isn't in your cart")
            return redirect("core:product", slug=slug)

    else:
        # add a message saying user doesn't have an order
        messages.info(request, f"You don't have active order")
        return redirect("core:product", slug=slug)

def remove_single_item_from_cart(request, slug):
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
            if order_item.quantity > 1:        
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item) 
        
            messages.success(request, f"Item quantity updated")
            return redirect("core:order-summary")               
        else:
            # add a message saying user doesn't have an order
            messages.error(request, "Item isn't in your cart")
            return redirect("core:product", slug=slug)

    else:
        # add a message saying user doesn't have an order
        messages.info(request, f"You don't have active order")
        return redirect("core:product", slug=slug)    

def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.error(request, "This Coupon does not exist!")
        return redirect("core:checkout")    
    

class AddCouponView(View):
    def post(self, *args, **kwargs):
            form = CouponForm(self.request.POST or None)
            if form.is_valid():
                try:
                    code = form.cleaned_data.get('code')
                    order = Order.objects.get(user=self.request.user, ordered=False)
                    order.coupon = get_coupon(self.request, code)
                    order.save()
                    messages.success(self.request, "Successfuly added coupon")
                    return redirect("core:checkout")
                
                except ObjectDoesNotExist:
                    messages.info(self.request, "You don't have active order")
                    return redirect("core:checkout")    

class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            "form": form
        }
        return render(self.request, "core/request_refund.html", context)
    
    
    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')            
            # edit the order    
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()
                
                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()
              
                messages.info(self.request, "Your request was received")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order doesn't exist")
                return redirect("core:request-refund")




