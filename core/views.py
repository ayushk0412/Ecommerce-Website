import stripe
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.utils import timezone
from django.shortcuts import redirect
from django.views.generic import View, ListView, DetailView, TemplateView
from .forms import (CheckoutForm,
                    CouponForm,
                    RefundForm)
from django.shortcuts import render, get_object_or_404
from .models import (Item,
                     OrderItem,
                     Order,
                     Address,
                     Payment,
                     Coupon,
                     Refund,)
import random
import string
stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(
        string.ascii_lowercase + string.digits, k=14))


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


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'object': order,
            }

            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='S',
                default=True
            )
            if shipping_address_qs.exists():
                context.update(
                    {'default_shipping_address': shipping_address_qs[0]})

            billing_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='B',
                default=True
            )
            if billing_address_qs.exists():
                context.update(
                    {'default_billing_address': billing_address_qs[0]})
            return render(self.request, "checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():

                use_default_shipping = form.cleaned_data.get(
                    'use_default_shipping')
                if use_default_shipping:
                    print("Using the defualt shipping address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='S',
                        default=True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request,
                            "No default shipping address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new shipping address")
                    shipping_address1 = form.cleaned_data.get(
                        'shipping_address')
                    shipping_address2 = form.cleaned_data.get(
                        'shipping_address2')
                    shipping_country = form.cleaned_data.get(
                        'shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')

                    if is_valid_form([shipping_address1,
                                      shipping_country,
                                      shipping_zip]):
                        shipping_address = Address(
                            user=self.request.user,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                            address_type='S'
                        )
                        shipping_address.save()

                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get(
                            'set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()

                    else:
                        messages.info(
                            self.request,
                            "Please fill in the required shipping address fields"
                        )

                use_default_billing = form.cleaned_data.get(
                    'use_default_billing')
                same_billing_address = form.cleaned_data.get(
                    'same_billing_address')

                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    print("Using the defualt billing address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='B',
                        default=True
                    )
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(
                            self.request,
                            "No default billing address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new billing address")
                    billing_address1 = form.cleaned_data.get(
                        'billing_address')
                    billing_address2 = form.cleaned_data.get(
                        'billing_address2')
                    billing_country = form.cleaned_data.get(
                        'billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address1,
                                      billing_country,
                                      billing_zip]):
                        billing_address = Address(
                            user=self.request.user,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='B'
                        )
                        billing_address.save()

                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get(
                            'set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()

                    else:
                        messages.info(
                            self.request,
                            "Please fill in the required billing address fields")

                payment_option = form.cleaned_data.get('payment_option')

                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(
                        self.request, "Invalid payment option selected")
                    return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("core:order-summary")


# Latest Stripe API


class PaymentSuccess(TemplateView):
    template_name = "success.html"


class PaymentCancel(TemplateView):
    template_name = "cancel.html"


class PaymentLanding(TemplateView):
    template_name = "payment.html"

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
    def post(self, *args, **kwargs):
        YOUR_DOMAIN = "http://127.0.0.1:8000/"
        order = Order.objects.get(user=self.request.user, ordered=False)
        amount = int(order.get_total() * 100)  # Rupees

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': "inr",
                        'unit_amount': amount,
                        'product_data': {
                            'name': 'Ecommerce',
                            # 'images': [
                            # 'https://i.imgur.com/EHyR2nP.png'
                            # ],
                        },
                    },
                    'quantity': 1,
                },
            ],
            metadata={
                'user': self.request.user,
                'user_id': self.request.user.id,
                'order_id': order.id,
                'coupon': order.coupon,
                'coupon_amount': order.coupon.amount,
            },
            mode='payment',
            success_url=YOUR_DOMAIN + 'success',
            cancel_url=YOUR_DOMAIN + 'cancel',
        )
        return JsonResponse({
            'id': checkout_session.id
        })


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
    coupon = session["metadata"]["coupon"]
    coupon_amount = session["metadata"]["coupon_amount"]
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
    payment.coupon = coupon
    payment.coupon_amount = coupon_amount
    payment.save()

    # Setting ordered is True for all ordered Items
    order_items = order.items.all()
    order_items.update(ordered=True)
    for item in order_items:
        item.save()

    # Assign payment to order
    order.ordered = True
    order.payment = payment
    order.ref_code = create_ref_code()
    order.save()

# Latest Stripe API -end


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


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist.")
        return("core:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon")
                return redirect("core:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("core:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "request_refund.html", context)

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

                messages.info(self.request, "Your request was received.")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("core:request-refund")
