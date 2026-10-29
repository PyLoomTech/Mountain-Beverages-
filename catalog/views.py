from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Product


def product_list(request):
    products = Product.objects.select_related("category")
    categories = Category.objects.all()

    selected = request.GET.get("category", "")
    query = request.GET.get("q", "").strip()

    if selected:
        products = products.filter(category__slug=selected)
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    return render(request, "catalog/product_list.html", {
        "products": products,
        "categories": categories,
        "selected": selected,
        "query": query,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related("category"), slug=slug)
    related = (
        Product.objects.filter(category=product.category, is_available=True)
        .exclude(pk=product.pk)[:4]
    )
    return render(request, "catalog/product_detail.html", {
        "product": product,
        "related": related,
    })
