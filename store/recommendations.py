
from django.db.models import Q

from products.models import Product
from orders.models import OrderItem


def get_recommended_products(request, limit=8):
    """
    Personalized product recommendations based on:
    1. Recently viewed products
    2. Previous confirmed purchases
    3. Similar categories and brands
    4. Available stock
    """

    user = request.user

    # Recently viewed product IDs from session
    recently_viewed = request.session.get(
        "recently_viewed_products",
        []
    )

    # Keep only valid, unique IDs
    recently_viewed = list(
        dict.fromkeys(
            int(pid)
            for pid in recently_viewed
            if str(pid).isdigit()
        )
    )[:10]

    # Purchased product IDs from completed/active orders
    purchased_ids = []

    if user.is_authenticated:
        purchased_ids = list(
            OrderItem.objects.filter(
                order__user=user,
                order__status__in=[
                    "confirmed",
                    "processing",
                    "shipped",
                    "delivered",
                ],
            ).values_list(
                "variant__product_id",
                flat=True,
            ).distinct()
        )

    seed_ids = list(
        dict.fromkeys(
            recently_viewed + purchased_ids
        )
    )

    # Only active products with available stock
    available_products = (
        Product.objects.filter(
            is_active=True,
            variants__is_active=True,
            variants__stock_quantity__gt=0,
        )
        .select_related(
            "category",
            "brand",
        )
        .prefetch_related(
            "images",
            "variants",
        )
        .distinct()
    )

    # No customer history: show newest available products
    if not seed_ids:
        return list(
            available_products.order_by(
                "-created_at"
            )[:limit]
        )

    seed_products = list(
        Product.objects.filter(
            id__in=seed_ids,
            is_active=True,
        ).select_related(
            "category",
            "brand",
        )
    )

    category_ids = {
        product.category_id
        for product in seed_products
        if product.category_id
    }

    brand_ids = {
        product.brand_id
        for product in seed_products
        if product.brand_id
    }

    # Find similar products
    similar_query = Q()

    if category_ids:
        similar_query |= Q(
            category_id__in=category_ids
        )

    if brand_ids:
        similar_query |= Q(
            brand_id__in=brand_ids
        )

    if not similar_query:
        return list(
            available_products.order_by(
                "-created_at"
            )[:limit]
        )

    candidates = list(
        available_products.filter(
            similar_query
        ).exclude(
            id__in=seed_ids
        ).distinct()
    )

    scored_products = []

    for candidate in candidates:
        score = 0
        reasons = []

        for seed in seed_products:

            if candidate.category_id == seed.category_id:
                score += 5
                reasons.append("Similar category")

            if (
                candidate.brand_id
                and candidate.brand_id == seed.brand_id
            ):
                score += 3
                reasons.append("Preferred brand")

            # Give a small score to products in a similar price range
            if seed.base_price and candidate.base_price:
                difference = abs(
                    float(candidate.base_price)
                    - float(seed.base_price)
                )

                if difference <= float(seed.base_price) * 0.30:
                    score += 2

        candidate.recommendation_score = score

        candidate.recommendation_reason = (
            reasons[0]
            if reasons
            else "Recommended for you"
        )

        scored_products.append(candidate)

    scored_products.sort(
        key=lambda product: (
            product.recommendation_score,
            product.created_at,
        ),
        reverse=True,
    )

    recommendations = scored_products[:limit]

    # Fill remaining slots with newest in-stock products
    if len(recommendations) < limit:
        selected_ids = {
            product.id
            for product in recommendations
        }

        fallback_products = available_products.exclude(
            id__in=selected_ids
        ).exclude(
            id__in=seed_ids
        ).order_by(
            "-created_at"
        )

        for product in fallback_products:
            product.recommendation_reason = (
                "Explore more styles"
            )

            recommendations.append(product)

            if len(recommendations) >= limit:
                break

    return recommendations
