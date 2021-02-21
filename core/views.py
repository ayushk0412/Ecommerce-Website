from django.shortcuts import render, get_object_or_404
from .models import Item, OrderItem, Order, BillingAddress, Payment
from .forms import CheckoutForm
from django.views.generic import View, ListView, DetailView, TemplateView
from django.shortcuts import redirect
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


def Items_list(request):
    context = {
        'items': Item.objects.all(),
    }
    return render(request, "home.html", context)


class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home.html"


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'order_summary.html', context)

        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order.")
            return redirect("/")


class CheckoutView(View):
    def get(self, *args, **kwargs):
        # form
        form = CheckoutForm()
        context = {
            'form': form
        }
        return render(self.request, 'checkout.html', context)

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                street_address = form.cleaned_data.get('street_address')
                apartment_address = form.cleaned_data.get('apartment_address')
                country = form.cleaned_data.get('country')
                zip = form.cleaned_data.get('zip')
                # same_shipping_address = form.cleaned_data.get(
                #     'same_shipping_address')
                # save_info = form.cleaned_data.get('save_info')
                payment_option = form.cleaned_data.get('payment_option')
                billing_address = BillingAddress(
                    user=self.request.user,
                    street_address=street_address,
                    apartment_address=apartment_address,
                    country=country,
                    zip=zip,
                )
                billing_address.save()
                order.billing_address = billing_address
                order.save()
                return redirect('core:checkout')
            messages.warning(self.request, "Failed checkout")
            return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order.")
            return redirect("/")


class PaymentView(View):
    def get(self, *args, **kwargs):
        return render(self.request, "payment.html")

    def post(self, *args, **kwargs):
        token = self.request.POST.get('stripeToken')
        order = Order.objects.get(user=self.request.user, ordered=False)
        amount = float(order.get_total() * 100)  # Rupees

        try:
            charge = stripe.Charge.create(
                amount=amount,
                currency="inr",
                source=token,
            )
            # Create Payment
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            # Assign payment to order
            order.ordered = True
            order.payment = payment
            order.save()

            messages.success(self.request, "Your order was Successful.")
            return redirect("/")

        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get('error', {})
            messages.error(self.request, f"{err.get('message')}")
            return redirect("/")

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.error(self.request, "Rate Limit Error")
            return redirect("/")

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.error(self.request, "Invalid Request Error")
            return redirect("/")

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.error(self.request, "Authentication Error")
            return redirect("/")

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.error(self.request, "API Connection Error")
            return redirect("/")

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.error(
                self.request, "Something went wrong, you were not charged. Please try again.")
            return redirect("/")

        except Exception as e:
            # Send an email to ourselves.
            messages.error(
                self.request, "Serious error occured, we have been notified.")
            return redirect("/")

# Testing the latest Stripe API


class PaymentSuccess(TemplateView):
    template_name = "success.html"


class PaymentCancel(TemplateView):
    template_name = "cancel.html"


class PaymentLanding(TemplateView):
    template_name = "payment2.html"

    def get_context_data(self, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)

        context = super(PaymentLanding,
                        self).get_context_data(**kwargs)
        context.update({
            "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
            "object": order,
        })
        return context


class CheckoutSession(View):
    # def get(self, *args, **kwargs):
    #     return render(self.request, "payment2.html")

    def post(self, *args, **kwargs):
        YOUR_DOMAIN = "http://127.0.0.1:8000/"
        order = Order.objects.get(user=self.request.user, ordered=False)
        amount = int(order.get_total() * 100)  # Rupees
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': "inr",
                            'unit_amount': amount,
                            'product_data': {
                                'name': 'Ecommerce',
                                # 'images': ['https://i.imgur.com/EHyR2nP.png'],
                            },
                        },
                        'quantity': 1,
                    },
                ],
                metadata={
                    'user': self.request.user,
                    'user_id': self.request.user.id,
                    'order_id': order.id,
                },
                mode='payment',
                success_url=YOUR_DOMAIN + 'success',
                cancel_url=YOUR_DOMAIN + 'cancel',
            )
            return JsonResponse({
                'id': checkout_session.id
            })
            # # Create Payment
            # payment = Payment()
            # payment.stripe_charge_id = checkout_session.id
            # payment.user = self.request.user
            # payment.amount = order.get_total()
            # payment.save()

            # # Assign payment to order
            # order.ordered = True
            # order.payment = payment
            # order.save()

            messages.success(self.request, "Your order was Successful.")
            return redirect("/")

        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get('error', {})
            messages.error(self.request, f"{err.get('message')}")
            return redirect("/")

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.error(self.request, "Rate Limit Error")
            return redirect("/")

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.error(self.request, "Invalid Request Error")
            return redirect("/")

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.error(self.request, "Authentication Error")
            return redirect("/")

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.error(self.request, "API Connection Error")
            return redirect("/")

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.error(
                self.request, "Something went wrong, you were not charged. Please try again.")
            return redirect("/")

        except Exception as e:
            # Send an email to ourselves.
            messages.error(
                self.request, "Serious error occured, we have been notified.")
            return redirect("/")


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_KEY
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        fulfill_order(request, session)
    # Passed signature verification
    return HttpResponse(status=200)


def fulfill_order(request, session):
    # Fulfill the purchase...
    payment_id = session["id"]
    payment_intent_id = session["payment_intent"]
    user_id = session["metadata"]["user_id"]
    order_id = session["metadata"]["order_id"]
    total_amount_temp = session["amount_total"]
    # Paise to Rupees Conversion
    total_amount_final = int(total_amount_temp) // 100
    user_main = User.objects.get(id=user_id)
    order = Order.objects.get(id=order_id)
    # Create Payment
    payment = Payment()
    payment.stripe_payment_id = payment_id
    payment.stripe_payment_intent_id = payment_intent_id
    payment.user = user_main
    payment.amount = total_amount_final
    payment.save()

    # Assign payment to order
    order.ordered = True
    order.payment = payment
    order.save()

# Testing the latest Stripe API -end


class ItemDetailView(DetailView):
    model = Item
    template_name = "product.html"


@ login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if order item is in order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "Item quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was added to your cart")
            order.items.add(order_item)
            return redirect("core:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart")
        return redirect("core:order-summary")


@ login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if order item is in order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            messages.info(request, "This item was removed from your cart")
            return redirect("core:order-summary")
        else:
            # Add a message saying the user dosent have an order
            messages.info(request, "This item was not in your cart.")
            return redirect("core:product",
                            slug=slug)
    else:
        messages.info(request, "You do not have an active user.")
        return redirect("core:product",
                        slug=slug)


def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if order item is in order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "Item quantity was updated.")
            return redirect("core:order-summary")
        else:
            # Add a message saying the user dosent have an order
            messages.info(request, "This item was not in your cart.")
            return redirect("core:product",
                            slug=slug)
    else:
        messages.info(request, "You do not have an active user.")
        return redirect("core:product",
                        slug=slug)
