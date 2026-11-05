
import re
from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from store.models import Cart
from products.models import ProductVariant
from accounts.models import Profile

from .models import Order, OrderItem
from .forms import CheckoutForm


# =============================================================
# CHECKOUT
# =============================================================

@login_required
def checkout(request):

    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(
            user=request.user,
            real_name=request.user.get_full_name() or request.user.username,
            mobile="",
            age=18,
            gender="Others",
            location="",
            address="",
            city="",
            state="",
            pincode=""
        )

    buy_now_variant_id = request.session.get("buy_now_variant_id")
    buy_now_quantity = request.session.get("buy_now_quantity")

    buy_now_variant = None
    cart = None
    items = None

    # BUY NOW FLOW
    if buy_now_variant_id:

        buy_now_variant = (
            ProductVariant.objects.filter(
                id=buy_now_variant_id,
                is_active=True
            )
            .select_related("product", "size", "color")
            .prefetch_related("product__images")
            .first()
        )

        if not buy_now_variant:
            request.session.pop("buy_now_variant_id", None)
            request.session.pop("buy_now_quantity", None)
            return redirect("cart")

        try:
            buy_now_quantity = int(buy_now_quantity)
        except (TypeError, ValueError):
            buy_now_quantity = 1

        if buy_now_quantity < 1:
            buy_now_quantity = 1

        if buy_now_variant.stock_quantity <= 0:
            messages.error(request, "This product is currently out of stock.")
            return redirect(
                "product_detail",
                slug=buy_now_variant.product.slug
            )

        if buy_now_quantity > buy_now_variant.stock_quantity:
            buy_now_quantity = buy_now_variant.stock_quantity

        total = buy_now_variant.price * buy_now_quantity

    # NORMAL CART FLOW
    else:

        cart_id = request.session.get("cart_id")

        if not cart_id:
            return redirect("cart")

        cart = (
            Cart.objects.filter(id=cart_id)
            .prefetch_related(
                "items__variant__product__images",
                "items__variant__size",
                "items__variant__color"
            )
            .first()
        )

        if not cart:
            return redirect("cart")

        items = cart.items.all()

        if not items.exists():
            return redirect("cart")

        total = sum(
            item.variant.price * item.quantity
            for item in items
        )

    # CHECKOUT FORM SUBMISSION
    if request.method == "POST":

        form = CheckoutForm(request.POST)

        if form.is_valid():

            try:
                with transaction.atomic():

                    order = Order.objects.create(
                        user=request.user,
                        customer_name=form.cleaned_data["full_name"],
                        email=form.cleaned_data["email"],
                        phone=form.cleaned_data["phone"],
                        address=form.cleaned_data["address"],
                        city=form.cleaned_data["city"],
                        state=form.cleaned_data["state"],
                        pincode=form.cleaned_data["pincode"],
                        total_amount=total,
                        delivery_date=timezone.localdate() + timedelta(days=5)
                    )

                    profile.real_name = form.cleaned_data["full_name"]
                    profile.mobile = form.cleaned_data["phone"]
                    profile.address = form.cleaned_data["address"]
                    profile.city = form.cleaned_data["city"]
                    profile.state = form.cleaned_data["state"]
                    profile.pincode = form.cleaned_data["pincode"]
                    profile.save()

                    if buy_now_variant:

                        variant = buy_now_variant

                        if buy_now_quantity > variant.stock_quantity:
                            raise ValueError("Not enough stock available.")

                        subtotal = variant.price * buy_now_quantity

                        OrderItem.objects.create(
                            order=order,
                            variant=variant,
                            product_name=variant.product.name,
                            size=variant.size.name if variant.size else "",
                            color=variant.color.name if variant.color else "",
                            price=variant.price,
                            quantity=buy_now_quantity,
                            subtotal=subtotal
                        )

                        order_source = "buy_now"

                    else:

                        order_source = "cart"

                        for item in items:

                            variant = item.variant

                            if item.quantity > variant.stock_quantity:
                                raise ValueError(
                                    f"Not enough stock available for "
                                    f"{variant.product.name}."
                                )

                            subtotal = variant.price * item.quantity

                            OrderItem.objects.create(
                                order=order,
                                variant=variant,
                                product_name=variant.product.name,
                                size=variant.size.name if variant.size else "",
                                color=variant.color.name if variant.color else "",
                                price=variant.price,
                                quantity=item.quantity,
                                subtotal=subtotal
                            )

                request.session[f"order_{order.id}_source"] = order_source

                return redirect(
                    "demo_payment",
                    order_id=order.id
                )

            except ValueError as error:
                form.add_error(None, str(error))

    else:

        form = CheckoutForm(
            initial={
                "full_name": profile.real_name,
                "email": request.user.email,
                "phone": profile.mobile,
                "address": profile.address,
                "city": profile.city,
                "state": profile.state,
                "pincode": profile.pincode
            }
        )

    return render(
        request,
        "orders/checkout.html",
        {
            "form": form,
            "cart": cart,
            "items": items,
            "total": total,
            "buy_now_variant": buy_now_variant,
            "buy_now_quantity": buy_now_quantity
        }
    )


# =============================================================
# PAYMENT RECOMMENDATION
# =============================================================

def get_recommended_payment_method(user):

    previous_orders = (
        Order.objects.filter(
            user=user,
            status__in=[
                "confirmed",
                "processing",
                "shipped",
                "out_for_delivery",
                "delivered"
            ]
        )
        .exclude(payment_method="")
        .values("payment_method")
        .annotate(total=Count("id"))
        .order_by("-total", "payment_method")
    )

    preferred = previous_orders.first()

    if preferred:
        return preferred["payment_method"]

    return "upi"


# =============================================================
# CLEAR CART AFTER SUCCESSFUL PAYMENT
# =============================================================

def clear_order_source(request, order):

    source_key = f"order_{order.id}_source"
    order_source = request.session.get(source_key)

    if order_source == "buy_now":

        request.session.pop("buy_now_variant_id", None)
        request.session.pop("buy_now_quantity", None)

    elif order_source == "cart":

        cart_id = request.session.get("cart_id")

        if cart_id:
            cart = Cart.objects.filter(id=cart_id).first()

            if cart:
                cart.items.all().delete()

            request.session.pop("cart_id", None)

    request.session.pop(source_key, None)
    request.session.modified = True


# =============================================================
# DEMO PAYMENT
# =============================================================

@login_required
def demo_payment(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    if order.status != "pending" or order.payment_method:

        if order.status == "cancelled":
            messages.info(request, "This order has been cancelled.")
            return redirect("my_orders")

        return redirect("order_success", order_id=order.id)

    recommended_method = get_recommended_payment_method(request.user)
    payment_methods = dict(Order.PAYMENT_METHOD_CHOICES)

    if request.method == "POST":

        action = request.POST.get("action")

        # CANCEL PENDING PAYMENT
        if action == "cancel":

            with transaction.atomic():

                locked_order = get_object_or_404(
                    Order.objects.select_for_update(),
                    id=order_id,
                    user=request.user
                )

                if (
                    locked_order.status == "pending"
                    and not locked_order.payment_method
                ):
                    locked_order.status = "cancelled"
                    locked_order.save(
                        update_fields=["status", "updated_at"]
                    )

            source_key = f"order_{order_id}_source"
            order_source = request.session.get(source_key)

            if order_source == "buy_now":
                request.session.pop("buy_now_variant_id", None)
                request.session.pop("buy_now_quantity", None)

            request.session.pop(source_key, None)
            request.session.modified = True

            messages.info(
                request,
                "Your order has been cancelled. You can continue shopping."
            )
            return redirect("home")

        if action != "pay":
            messages.error(request, "Invalid request.")
            return redirect("demo_payment", order_id=order.id)

        payment_method = request.POST.get(
            "payment_method", ""
        ).lower()

        if payment_method not in payment_methods:
            messages.error(request, "Please select a valid payment method.")
            return redirect("demo_payment", order_id=order.id)

        # DEMO UPI VALIDATION
        if payment_method == "upi":

            upi_id = request.POST.get("upi_id", "").strip()

            if not re.fullmatch(
                r"[A-Za-z0-9._-]+@[A-Za-z]{2,}",
                upi_id
            ):
                messages.error(
                    request,
                    "Enter a valid fictional demo UPI ID, for example demo@bank."
                )
                return redirect("demo_payment", order_id=order.id)

        # DEMO CARD VALIDATION
        elif payment_method == "card":

            card_name = request.POST.get("card_name", "").strip()
            card_number = re.sub(
                r"\s+", "",
                request.POST.get("card_number", "")
            )
            expiry = request.POST.get("expiry", "").strip()
            cvv = request.POST.get("cvv", "").strip()

            if not card_name or len(card_name) > 80:
                messages.error(
                    request,
                    "Enter a demo cardholder name."
                )
                return redirect("demo_payment", order_id=order.id)

            if not re.fullmatch(r"\d{16}", card_number):
                messages.error(
                    request,
                    "Enter a 16-digit fictional demo card number."
                )
                return redirect("demo_payment", order_id=order.id)

            if not re.fullmatch(r"(0[1-9]|1[0-2])/\d{2}", expiry):
                messages.error(
                    request,
                    "Enter expiry in MM/YY format."
                )
                return redirect("demo_payment", order_id=order.id)

            if not re.fullmatch(r"\d{3,4}", cvv):
                messages.error(
                    request,
                    "Enter a 3 or 4 digit fictional demo security code."
                )
                return redirect("demo_payment", order_id=order.id)

        try:

            with transaction.atomic():

                locked_order = get_object_or_404(
                    Order.objects.select_for_update(),
                    id=order_id,
                    user=request.user
                )

                if (
                    locked_order.status != "pending"
                    or locked_order.payment_method
                ):
                    return redirect(
                        "order_success",
                        order_id=locked_order.id
                    )

                order_items = list(
                    locked_order.items.select_related(
                        "variant__product"
                    ).all()
                )

                if not order_items:
                    raise ValueError("This order has no products.")

                variant_ids = sorted({
                    item.variant_id for item in order_items
                })

                locked_variants = {
                    variant.id: variant
                    for variant in (
                        ProductVariant.objects.select_for_update()
                        .filter(id__in=variant_ids)
                        .order_by("id")
                    )
                }

                for item in order_items:

                    variant = locked_variants.get(item.variant_id)

                    if not variant or not variant.is_active:
                        raise ValueError(
                            f"{item.product_name} is no longer available."
                        )

                    if variant.stock_quantity < item.quantity:
                        raise ValueError(
                            f"Insufficient stock for {item.product_name}."
                        )

                for item in order_items:

                    variant = locked_variants[item.variant_id]
                    variant.stock_quantity -= item.quantity

                    variant.save(
                        update_fields=["stock_quantity"]
                    )

                locked_order.payment_method = payment_method
                locked_order.status = "confirmed"

                locked_order.save(
                    update_fields=[
                        "payment_method",
                        "status",
                        "updated_at"
                    ]
                )

            clear_order_source(request, order)

            messages.success(
                request,
                "Demo order confirmed successfully. No real money was charged."
            )

            return redirect(
                "order_success",
                order_id=order.id
            )

        except ValueError as error:

            messages.error(request, str(error))
            return redirect("demo_payment", order_id=order.id)

    return render(
        request,
        "orders/demo_payment.html",
        {
            "order": order,
            "recommended_method": recommended_method
        }
    )


# =============================================================
# ORDER SUCCESS + TRACKING + CUSTOMER HELP
# =============================================================

@login_required
def order_success(request, order_id):

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items__variant__product__images"
        ),
        id=order_id,
        user=request.user
    )

    # RESCHEDULE DELIVERY
    if request.method == "POST":

        action = request.POST.get("action")

        if action == "reschedule":

            if order.status not in ["confirmed", "processing"]:
                messages.error(
                    request,
                    "Delivery can no longer be rescheduled for this order."
                )

            else:

                delivery_date_value = request.POST.get(
                    "delivery_date", ""
                ).strip()

                try:
                    new_delivery_date = date.fromisoformat(
                        delivery_date_value
                    )

                    if new_delivery_date < timezone.localdate():
                        raise ValueError

                    order.delivery_date = new_delivery_date
                    order.save(
                        update_fields=["delivery_date", "updated_at"]
                    )

                    messages.success(
                        request,
                        "Your delivery date has been updated successfully."
                    )

                except (ValueError, TypeError):
                    messages.error(
                        request,
                        "Please select a valid delivery date."
                    )

            return redirect("order_success", order_id=order.id)

        # CANCEL CONFIRMED ORDER AND RESTORE STOCK
        elif action == "cancel_order":

            with transaction.atomic():

                locked_order = get_object_or_404(
                    Order.objects.select_for_update(),
                    id=order_id,
                    user=request.user
                )

                if locked_order.status not in [
                    "confirmed",
                    "processing"
                ]:
                    messages.error(
                        request,
                        "This order can no longer be cancelled."
                    )

                else:

                    order_items = list(
                        locked_order.items.all()
                    )

                    variant_ids = sorted({
                        item.variant_id for item in order_items
                    })

                    locked_variants = {
                        variant.id: variant
                        for variant in (
                            ProductVariant.objects.select_for_update()
                            .filter(id__in=variant_ids)
                            .order_by("id")
                        )
                    }

                    # Restore the purchased stock exactly once.
                    for item in order_items:

                        variant = locked_variants.get(
                            item.variant_id
                        )

                        if variant:
                            variant.stock_quantity += item.quantity

                            variant.save(
                                update_fields=["stock_quantity"]
                            )

                    locked_order.status = "cancelled"

                    locked_order.save(
                        update_fields=["status", "updated_at"]
                    )

                    messages.success(
                        request,
                        "Your order has been cancelled successfully."
                    )

            return redirect("order_success", order_id=order.id)

        else:
            messages.error(request, "Invalid request.")
            return redirect("order_success", order_id=order.id)

    # DELIVERY DATE FALLBACK FOR OLDER ORDERS
    delivery_date = (
        order.delivery_date
        or timezone.localdate() + timedelta(days=5)
    )

    return render(
        request,
        "orders/order_success.html",
        {
            "order": order,
            "delivery_date": delivery_date,
            "today": timezone.localdate().isoformat(),
            "can_manage_order": order.status in [
                "confirmed",
                "processing"
            ]
        }
    )


# =============================================================
# MY ORDERS
# =============================================================

@login_required
def my_orders(request):

    orders = (
        Order.objects.filter(user=request.user)
        .order_by("-created_at")
    )

    return render(
        request,
        "orders/my_orders.html",
        {
            "orders": orders
        }
    )
