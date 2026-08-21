
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.db.models import Q, Min

from products.models import Product, ProductVariant
from .models import Cart, CartItem, Order, OrderItem


# ==========================================
# HOME
# ==========================================

def home(request):

    products = Product.objects.filter(
        is_active=True
    ).prefetch_related(
        'images',
        'variants__size',
        'variants__color'
    )

    return render(
        request,
        'store/home.html',
        {
            'products': products
        }
    )


# ==========================================
# PRODUCT DETAIL
# ==========================================

def product_detail(request, slug):

    product = get_object_or_404(
        Product.objects.prefetch_related(
            'images',
            'variants__size',
            'variants__color'
        ),
        slug=slug,
        is_active=True
    )

    variants = product.variants.filter(
        is_active=True
    ).select_related(
        'size',
        'color'
    )

    return render(
        request,
        'store/product_detail.html',
        {
            'product': product,
            'variants': variants
        }
    )


# ==========================================
# SEARCH PRODUCTS
# ==========================================

def search_products(request):

    query = request.GET.get(
        'q',
        ''
    ).strip()

    sort = request.GET.get(
        'sort',
        'newest'
    )

    in_stock = request.GET.get(
        'in_stock'
    )

    categories = request.GET.getlist(
        'category'
    )

    price_range = request.GET.get(
        'price'
    )

    # ------------------------------------------
    # Base Product Query
    # ------------------------------------------

    products = Product.objects.filter(
        is_active=True
    ).prefetch_related(
        'images',
        'variants__size',
        'variants__color'
    )

    # ------------------------------------------
    # Search
    # ------------------------------------------

    if query:

        products = products.filter(
            Q(name__icontains=query) |
            Q(brand__name__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()

    # ------------------------------------------
    # Category Filter
    # ------------------------------------------

    if categories:

        products = products.filter(
            category__name__in=categories
        ).distinct()

    # ------------------------------------------
    # Availability Filter
    # ------------------------------------------

    if in_stock:

        products = products.filter(
            variants__is_active=True,
            variants__stock_quantity__gt=0
        ).distinct()

    # ------------------------------------------
    # Price Filters
    # ------------------------------------------

    if price_range == 'under_1000':

        products = products.filter(
            variants__is_active=True,
            variants__price__lt=1000
        ).distinct()

    elif price_range == '1000_2000':

        products = products.filter(
            variants__is_active=True,
            variants__price__gte=1000,
            variants__price__lte=2000
        ).distinct()

    elif price_range == 'above_2000':

        products = products.filter(
            variants__is_active=True,
            variants__price__gt=2000
        ).distinct()

    # ------------------------------------------
    # Sorting
    # ------------------------------------------

    if sort == 'price_low':

        products = products.annotate(
            lowest_price=Min(
                'variants__price'
            )
        ).order_by(
            'lowest_price',
            '-id'
        )

    elif sort == 'price_high':

        products = products.annotate(
            lowest_price=Min(
                'variants__price'
            )
        ).order_by(
            '-lowest_price',
            '-id'
        )

    else:

        # Newest First
        products = products.order_by(
            '-id'
        )

    # ------------------------------------------
    # Available Categories
    # ------------------------------------------

    available_categories = (
        Product.objects
        .filter(
            is_active=True
        )
        .values_list(
            'category__name',
            flat=True
        )
        .distinct()
    )

    # ------------------------------------------
    # Result Count
    # ------------------------------------------

    product_count = products.count()

    return render(
        request,
        'store/search_results.html',
        {
            'products': products,
            'query': query,
            'sort': sort,
            'in_stock': in_stock,
            'selected_categories': categories,
            'price_range': price_range,
            'available_categories': available_categories,
            'product_count': product_count,
        }
    )


# ==========================================
# ADD TO CART
# ==========================================

def add_to_cart(request, variant_id):

    variant = get_object_or_404(
        ProductVariant.objects.select_related(
            'product',
            'size',
            'color'
        ),
        id=variant_id,
        is_active=True
    )

    product_slug = variant.product.slug

    if request.method != 'POST':

        return redirect(
            'product_detail',
            slug=product_slug
        )

    if variant.stock_quantity <= 0:

        return redirect(
            'product_detail',
            slug=product_slug
        )

    try:

        quantity = int(
            request.POST.get(
                'quantity',
                1
            )
        )

    except (TypeError, ValueError):

        quantity = 1

    if quantity < 1:

        quantity = 1

    cart_id = request.session.get(
        'cart_id'
    )

    if cart_id:

        cart = Cart.objects.filter(
            id=cart_id
        ).first()

    else:

        cart = None

    if not cart:

        cart = Cart.objects.create()

        request.session['cart_id'] = cart.id

    cart_item = CartItem.objects.filter(
        cart=cart,
        variant=variant
    ).first()

    if cart_item:

        new_quantity = (
            cart_item.quantity + quantity
        )

        if new_quantity > variant.stock_quantity:

            new_quantity = variant.stock_quantity

        cart_item.quantity = new_quantity

        cart_item.save()

    else:

        if quantity > variant.stock_quantity:

            quantity = variant.stock_quantity

        CartItem.objects.create(
            cart=cart,
            variant=variant,
            quantity=quantity
        )

    return redirect(
        'cart'
    )


# ==========================================
# CART
# ==========================================

def cart(request):

    cart_id = request.session.get(
        'cart_id'
    )

    if not cart_id:

        return render(
            request,
            'store/cart.html',
            {
                'cart': None,
                'items': [],
                'total': 0
            }
        )

    cart = Cart.objects.filter(
        id=cart_id
    ).prefetch_related(
        'items__variant__product',
        'items__variant__size',
        'items__variant__color'
    ).first()

    if not cart:

        return render(
            request,
            'store/cart.html',
            {
                'cart': None,
                'items': [],
                'total': 0
            }
        )

    items = cart.items.all()

    total = sum(
        item.variant.price * item.quantity
        for item in items
    )

    return render(
        request,
        'store/cart.html',
        {
            'cart': cart,
            'items': items,
            'total': total
        }
    )


# ==========================================
# INCREASE CART QUANTITY
# ==========================================

def increase_cart_quantity(request, item_id):

    if request.method != 'POST':

        return redirect(
            'cart'
        )

    cart_id = request.session.get(
        'cart_id'
    )

    if not cart_id:

        return redirect(
            'cart'
        )

    cart_item = get_object_or_404(
        CartItem.objects.select_related(
            'variant'
        ),
        id=item_id,
        cart_id=cart_id
    )

    variant = cart_item.variant

    if cart_item.quantity < variant.stock_quantity:

        cart_item.quantity += 1

        cart_item.save()

    return redirect(
        'cart'
    )


# ==========================================
# DECREASE CART QUANTITY
# ==========================================

def decrease_cart_quantity(request, item_id):

    if request.method != 'POST':

        return redirect(
            'cart'
        )

    cart_id = request.session.get(
        'cart_id'
    )

    if not cart_id:

        return redirect(
            'cart'
        )

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart_id=cart_id
    )

    if cart_item.quantity > 1:

        cart_item.quantity -= 1

        cart_item.save()

    else:

        cart_item.delete()

    return redirect(
        'cart'
    )


# ==========================================
# REMOVE FROM CART
# ==========================================

def remove_from_cart(request, item_id):

    if request.method != 'POST':

        return redirect(
            'cart'
        )

    cart_id = request.session.get(
        'cart_id'
    )

    if not cart_id:

        return redirect(
            'cart'
        )

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart_id=cart_id
    )

    cart_item.delete()

    return redirect(
        'cart'
    )


# ==========================================
# CHECKOUT
# ==========================================

def checkout(request):

    cart_id = request.session.get(
        'cart_id'
    )

    if not cart_id:

        return redirect(
            'cart'
        )

    cart = Cart.objects.filter(
        id=cart_id
    ).prefetch_related(
        'items__variant__product',
        'items__variant__size',
        'items__variant__color'
    ).first()

    if not cart:

        return redirect(
            'cart'
        )

    items = cart.items.all()

    if not items.exists():

        return redirect(
            'cart'
        )

    total = sum(
        item.variant.price * item.quantity
        for item in items
    )

    return render(
        request,
        'store/checkout.html',
        {
            'cart': cart,
            'items': items,
            'total': total
        }
    )


# ==========================================
# PLACE ORDER
# ==========================================

@transaction.atomic
def place_order(request):

    if request.method != 'POST':

        return redirect(
            'checkout'
        )

    cart_id = request.session.get(
        'cart_id'
    )

    if not cart_id:

        return redirect(
            'cart'
        )

    cart = Cart.objects.filter(
        id=cart_id
    ).prefetch_related(
        'items__variant__product',
        'items__variant__size',
        'items__variant__color'
    ).first()

    if not cart:

        return redirect(
            'cart'
        )

    items = list(
        cart.items.all()
    )

    if not items:

        return redirect(
            'cart'
        )

    customer_name = request.POST.get(
        'customer_name',
        ''
    ).strip()

    phone = request.POST.get(
        'phone',
        ''
    ).strip()

    address = request.POST.get(
        'address',
        ''
    ).strip()

    # ------------------------------------------
    # Basic Validation
    # ------------------------------------------

    if not customer_name or not phone or not address:

        return render(
            request,
            'store/checkout.html',
            {
                'cart': cart,
                'items': items,
                'total': sum(
                    item.variant.price * item.quantity
                    for item in items
                ),
                'error': (
                    'Please fill in all customer details.'
                )
            }
        )

    # ------------------------------------------
    # Check Stock
    # ------------------------------------------

    for item in items:

        variant = ProductVariant.objects.select_for_update().get(
            id=item.variant.id
        )

        if not variant.is_active:

            return render(
                request,
                'store/checkout.html',
                {
                    'cart': cart,
                    'items': items,
                    'total': sum(
                        cart_item.variant.price *
                        cart_item.quantity
                        for cart_item in items
                    ),
                    'error': (
                        f'{variant.product.name} '
                        f'is currently unavailable.'
                    )
                }
            )

        if variant.stock_quantity < item.quantity:

            return render(
                request,
                'store/checkout.html',
                {
                    'cart': cart,
                    'items': items,
                    'total': sum(
                        cart_item.variant.price *
                        cart_item.quantity
                        for cart_item in items
                    ),
                    'error': (
                        f'Not enough stock for '
                        f'{variant.product.name}.'
                    )
                }
            )

    # ------------------------------------------
    # Calculate Total
    # ------------------------------------------

    total = sum(
        item.variant.price * item.quantity
        for item in items
    )

    # ------------------------------------------
    # Create Order
    # ------------------------------------------

    order = Order.objects.create(
        customer_name=customer_name,
        phone=phone,
        address=address,
        total_amount=total,
        status='confirmed'
    )

    # ------------------------------------------
    # Create Order Items
    # ------------------------------------------

    for item in items:

        variant = ProductVariant.objects.select_for_update().get(
            id=item.variant.id
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
            subtotal=(
                variant.price * item.quantity
            )
        )

        # Reduce Stock

        variant.stock_quantity -= item.quantity

        variant.save(
            update_fields=[
                'stock_quantity',
                'updated_at'
            ]
        )

    # ------------------------------------------
    # Clear Cart
    # ------------------------------------------

    cart.items.all().delete()

    request.session.pop(
        'cart_id',
        None
    )

    request.session['last_order_id'] = order.id

    return redirect(
        'order_success',
        order_id=order.id
    )


# ==========================================
# ORDER SUCCESS
# ==========================================

def order_success(request, order_id):

    order = get_object_or_404(
        Order.objects.prefetch_related(
            'items'
        ),
        id=order_id
    )

    return render(
        request,
        'store/order_success.html',
        {
            'order': order
        }
    )

def men_products(request):
    products = Product.objects.filter(
        category__name__iexact="Men"
    ).prefetch_related("images")

    return render(
        request,
        "store/men.html",
        {
            "products": products,
        }
    )




