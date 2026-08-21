
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth.decorators import login_required

from store.models import Cart
from .models import Order, OrderItem
from .forms import CheckoutForm


@login_required
def checkout(request):

    cart_id = request.session.get('cart_id')

    if not cart_id:
        return redirect('cart')

    cart = Cart.objects.filter(
        id=cart_id
    ).prefetch_related(
        'items__variant__product',
        'items__variant__size',
        'items__variant__color'
    ).first()

    if not cart:
        return redirect('cart')

    items = cart.items.all()

    if not items.exists():
        return redirect('cart')

    total = sum(
        item.variant.price * item.quantity
        for item in items
    )

    if request.method == 'POST':

        form = CheckoutForm(request.POST)

        if form.is_valid():

            try:

                with transaction.atomic():

                    # Create Order
                    order = Order.objects.create(
                        user=request.user,
                        customer_name=form.cleaned_data['full_name'],
                        email=form.cleaned_data['email'],
                        phone=form.cleaned_data['phone'],
                        address=form.cleaned_data['address'],
                        city=form.cleaned_data['city'],
                        state=form.cleaned_data['state'],
                        pincode=form.cleaned_data['pincode'],
                        total_amount=total
                    )

                    # Create Order Items
                    for item in items:

                        variant = item.variant

                        # Check stock again
                        if item.quantity > variant.stock_quantity:
                            raise ValueError(
                                f"Not enough stock available for "
                                f"{variant.product.name}."
                            )

                        subtotal = (
                            variant.price * item.quantity
                        )

                        OrderItem.objects.create(
                            order=order,
                            variant=variant,
                            product_name=variant.product.name,
                            size=(
                                variant.size.name
                                if variant.size
                                else ''
                            ),
                            color=(
                                variant.color.name
                                if variant.color
                                else ''
                            ),
                            price=variant.price,
                            quantity=item.quantity,
                            subtotal=subtotal
                        )

                        # Reduce stock
                        variant.stock_quantity -= item.quantity

                        variant.save(
                            update_fields=['stock_quantity']
                        )

                    # Clear cart
                    items.delete()

                    # Remove cart from session
                    if 'cart_id' in request.session:
                        del request.session['cart_id']

                    return redirect(
                        'order_success',
                        order_id=order.id
                    )

            except ValueError as e:

                form.add_error(
                    None,
                    str(e)
                )

    else:

        form = CheckoutForm()

    return render(
        request,
        'orders/checkout.html',
        {
            'form': form,
            'cart': cart,
            'items': items,
            'total': total
        }
    )


def order_success(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id
    )

    return render(
        request,
        'orders/order_success.html',
        {
            'order': order
        }
    )


@login_required
def my_orders(request):

    orders = Order.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(
        request,
        'orders/my_orders.html',
        {
            'orders': orders
        }
    )

