from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth.decorators import login_required

from store.models import Cart
from products.models import ProductVariant

from accounts.models import Profile

from .models import Order, OrderItem
from .forms import CheckoutForm


@login_required
def checkout(request):

    # =========================================================
    # GET USER PROFILE
    # =========================================================

    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(
            user=request.user,
            real_name=request.user.get_full_name()
            or request.user.username,
            mobile="",
            age=18,
            gender="Others",
            location="",
            address="",
            city="",
            state="",
            pincode=""
        )

    # =========================================================
    # BUY NOW FLOW
    # =========================================================

    buy_now_variant_id = request.session.get(
        "buy_now_variant_id"
    )

    buy_now_quantity = request.session.get(
        "buy_now_quantity"
    )

    buy_now_variant = None

    if buy_now_variant_id:

        buy_now_variant = (
            ProductVariant.objects.filter(
                id=buy_now_variant_id,
                is_active=True
            )
            .select_related(
                "product",
                "size",
                "color"
            )
            .prefetch_related(
                "product__images"
            )
            .first()
        )

        # Variant no longer exists
        if not buy_now_variant:

            request.session.pop(
                "buy_now_variant_id",
                None
            )

            request.session.pop(
                "buy_now_quantity",
                None
            )

            return redirect("cart")

        # Validate quantity
        try:
            buy_now_quantity = int(
                buy_now_quantity
            )

        except (TypeError, ValueError):
            buy_now_quantity = 1

        if buy_now_quantity < 1:
            buy_now_quantity = 1

        # Out of stock
        if buy_now_variant.stock_quantity <= 0:

            request.session.pop(
                "buy_now_variant_id",
                None
            )

            request.session.pop(
                "buy_now_quantity",
                None
            )

            return redirect(
                "product_detail",
                slug=buy_now_variant.product.slug
            )

        # Prevent quantity exceeding stock
        if (
            buy_now_quantity >
            buy_now_variant.stock_quantity
        ):
            buy_now_quantity = (
                buy_now_variant.stock_quantity
            )

        # Calculate Buy Now total
        total = (
            buy_now_variant.price *
            buy_now_quantity
        )

        # Buy Now does not use cart
        items = None
        cart = None

    else:

        # =====================================================
        # NORMAL CART CHECKOUT
        # =====================================================

        cart_id = request.session.get(
            "cart_id"
        )

        if not cart_id:
            return redirect("cart")

        cart = (
            Cart.objects.filter(
                id=cart_id
            )
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

        # Calculate cart total
        total = sum(
            item.variant.price * item.quantity
            for item in items
        )

    # =========================================================
    # FORM SUBMISSION
    # =========================================================

    if request.method == "POST":

        form = CheckoutForm(
            request.POST
        )

        if form.is_valid():

            try:

                with transaction.atomic():

                    # =================================================
                    # CREATE ORDER
                    # =================================================

                    order = Order.objects.create(

                        user=request.user,

                        customer_name=(
                            form.cleaned_data[
                                "full_name"
                            ]
                        ),

                        email=(
                            form.cleaned_data[
                                "email"
                            ]
                        ),

                        phone=(
                            form.cleaned_data[
                                "phone"
                            ]
                        ),

                        address=(
                            form.cleaned_data[
                                "address"
                            ]
                        ),

                        city=(
                            form.cleaned_data[
                                "city"
                            ]
                        ),

                        state=(
                            form.cleaned_data[
                                "state"
                            ]
                        ),

                        pincode=(
                            form.cleaned_data[
                                "pincode"
                            ]
                        ),

                        total_amount=total
                    )

                    # =================================================
                    # SAVE DELIVERY DETAILS TO USER PROFILE
                    # =================================================

                    profile.real_name = (
                        form.cleaned_data[
                            "full_name"
                        ]
                    )

                    profile.mobile = (
                        form.cleaned_data[
                            "phone"
                        ]
                    )

                    profile.address = (
                        form.cleaned_data[
                            "address"
                        ]
                    )

                    profile.city = (
                        form.cleaned_data[
                            "city"
                        ]
                    )

                    profile.state = (
                        form.cleaned_data[
                            "state"
                        ]
                    )

                    profile.pincode = (
                        form.cleaned_data[
                            "pincode"
                        ]
                    )

                    profile.save()

                    # =================================================
                    # BUY NOW ORDER
                    # =================================================

                    if buy_now_variant:

                        variant = buy_now_variant

                        # Check stock again
                        if (
                            buy_now_quantity >
                            variant.stock_quantity
                        ):

                            raise ValueError(
                                f"Not enough stock available for "
                                f"{variant.product.name}."
                            )

                        subtotal = (
                            variant.price *
                            buy_now_quantity
                        )

                        OrderItem.objects.create(

                            order=order,

                            variant=variant,

                            product_name=(
                                variant.product.name
                            ),

                            size=(
                                variant.size.name
                                if variant.size
                                else ""
                            ),

                            color=(
                                variant.color.name
                                if variant.color
                                else ""
                            ),

                            price=variant.price,

                            quantity=buy_now_quantity,

                            subtotal=subtotal
                        )

                        # Reduce stock
                        variant.stock_quantity -= (
                            buy_now_quantity
                        )

                        variant.save(
                            update_fields=[
                                "stock_quantity"
                            ]
                        )

                    # =================================================
                    # NORMAL CART ORDER
                    # =================================================

                    else:

                        for item in items:

                            variant = item.variant

                            # Check stock again
                            if (
                                item.quantity >
                                variant.stock_quantity
                            ):

                                raise ValueError(
                                    f"Not enough stock available for "
                                    f"{variant.product.name}."
                                )

                            subtotal = (
                                variant.price *
                                item.quantity
                            )

                            OrderItem.objects.create(

                                order=order,

                                variant=variant,

                                product_name=(
                                    variant.product.name
                                ),

                                size=(
                                    variant.size.name
                                    if variant.size
                                    else ""
                                ),

                                color=(
                                    variant.color.name
                                    if variant.color
                                    else ""
                                ),

                                price=variant.price,

                                quantity=item.quantity,

                                subtotal=subtotal
                            )

                            # Reduce stock
                            variant.stock_quantity -= (
                                item.quantity
                            )

                            variant.save(
                                update_fields=[
                                    "stock_quantity"
                                ]
                            )

                        # Clear normal cart
                        items.delete()

                        if "cart_id" in request.session:

                            del request.session[
                                "cart_id"
                            ]

                    # =================================================
                    # CLEAR BUY NOW SESSION
                    # =================================================

                    request.session.pop(
                        "buy_now_variant_id",
                        None
                    )

                    request.session.pop(
                        "buy_now_quantity",
                        None
                    )

                    request.session.modified = True

                    # =================================================
                    # ORDER SUCCESS
                    # =================================================

                    return redirect(
                        "order_success",
                        order_id=order.id
                    )

            except ValueError as e:

                form.add_error(
                    None,
                    str(e)
                )

    else:

        # =========================================================
        # AUTOMATICALLY FILL ACCOUNT DETAILS
        # =========================================================

        form = CheckoutForm(
            initial={
                "full_name": profile.real_name,
                "email": request.user.email,
                "phone": profile.mobile,
                "address": profile.address,
                "city": profile.city,
                "state": profile.state,
                "pincode": profile.pincode,
            }
        )

    # =========================================================
    # TEMPLATE CONTEXT
    # =========================================================

    return render(

        request,

        "orders/checkout.html",

        {
            "form": form,

            "cart": cart,

            "items": items,

            "total": total,

            "buy_now_variant": (
                buy_now_variant
            ),

            "buy_now_quantity": (
                buy_now_quantity
            )
        }
    )


# =============================================================
# ORDER SUCCESS
# =============================================================

def order_success(
    request,
    order_id
):

    order = get_object_or_404(
        Order,
        id=order_id
    )

    return render(

        request,

        "orders/order_success.html",

        {
            "order": order
        }
    )


# =============================================================
# MY ORDERS
# =============================================================

@login_required
def my_orders(request):

    orders = (
        Order.objects.filter(
            user=request.user
        )
        .order_by(
            "-created_at"
        )
    )

    return render(

        request,

        "orders/my_orders.html",

        {
            "orders": orders
        }
    )