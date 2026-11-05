
from django.urls import path
from . import views
from orders import views as order_views


urlpatterns = [

    # Home
    path(
        '',
        views.home,
        name='home'
    ),

    # Product Details
    path(
        'product/<slug:slug>/',
        views.product_detail,
        name='product_detail'
    ),

    # Search
    path(
        'search/',
        views.search_products,
        name='search_products'
    ),

    # Cart
    path(
        'cart/',
        views.cart,
        name='cart'
    ),

    # Add To Cart
    path(
        'cart/add/<int:variant_id>/',
        views.add_to_cart,
        name='add_to_cart'
    ),

    # Buy Now
    path(
        'buy-now/<int:variant_id>/',
        views.buy_now,
        name='buy_now'
    ),

    # Men
    path(
        'men/',
        views.men_products,
        name='men_products'
    ),

    # Increase Cart Quantity
    path(
        'cart/increase/<int:item_id>/',
        views.increase_cart_quantity,
        name='increase_cart_quantity'
    ),

    # Decrease Cart Quantity
    path(
        'cart/decrease/<int:item_id>/',
        views.decrease_cart_quantity,
        name='decrease_cart_quantity'
    ),

    # Remove From Cart
    path(
        'cart/remove/<int:item_id>/',
        views.remove_from_cart,
        name='remove_from_cart'
    ),

    # Checkout
    path(
        'checkout/',
        order_views.checkout,
        name='checkout'
    ),

    # Place Order
    path(
        'checkout/place-order/',
        views.place_order,
        name='place_order'
    ),

    # Demo Payment
    path(
        'demo-payment/<int:order_id>/',
        order_views.demo_payment,
        name='demo_payment'
    ),

    # Order Success
    path(
        'order-success/<int:order_id>/',
        order_views.order_success,
        name='order_success'
    ),

    # My Orders
    path(
        'my-orders/',
        order_views.my_orders,
        name='my_orders'
    ),
]
