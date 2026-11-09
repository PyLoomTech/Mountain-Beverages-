from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Post

PAGE_SIZE = 9


def post_list(request):
    page_obj = Paginator(Post.objects.live(), PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "posts/post_list.html", {"page_obj": page_obj})


def post_detail(request, slug):
    # Drafts and scheduled posts give a 404 to visitors
    post = get_object_or_404(Post.objects.live(), slug=slug)
    latest = Post.objects.live().exclude(pk=post.pk)[:3]
    return render(request, "posts/post_detail.html", {"post": post, "latest": latest})
