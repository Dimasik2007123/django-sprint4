"""Публикации, профили пользователей и комментарии."""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from .forms import CommentForm, PostForm, UserForm
from .models import Category, Comment, Post, User

POSTS_PER_PAGE = 10


def get_published_posts(queryset):
    """Отобрать публикации, доступные всем посетителям."""
    return queryset.filter(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True,
    )


def get_visible_posts(user):
    """Дополнить опубликованные записи скрытыми записями самого автора."""
    queryset = Post.objects.select_related('author', 'category', 'location')
    published_posts = get_published_posts(queryset)
    if user.is_authenticated:
        return published_posts | queryset.filter(author=user)
    return published_posts


class PostListView(ListView):
    model = Post
    template_name = 'blog/index.html'
    paginate_by = POSTS_PER_PAGE

    def get_queryset(self):
        return get_published_posts(
            Post.objects.select_related('author', 'category', 'location')
        ).annotate(
            comment_count=Count('comments'),
        ).order_by('-pub_date', '-pk')


class CategoryPostListView(PostListView):
    template_name = 'blog/category.html'

    def get_queryset(self):
        self.category = get_object_or_404(
            Category, slug=self.kwargs['category_slug'], is_published=True,
        )
        return super().get_queryset().filter(category=self.category)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class ProfileView(PostListView):
    template_name = 'blog/profile.html'

    def get_queryset(self):
        self.profile = get_object_or_404(
            User, username=self.kwargs['username'],
        )
        queryset = self.profile.posts.select_related(
            'author', 'category', 'location',
        )
        if self.request.user != self.profile:
            queryset = get_published_posts(queryset)
        return queryset.annotate(
            comment_count=Count('comments'),
        ).order_by('-pub_date', '-pk')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.profile
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = 'blog/user.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse('blog:profile', args=[self.object.username])


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def get_queryset(self):
        return get_visible_posts(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.select_related('author')
        return context


class OnlyAuthorMixin(UserPassesTestMixin):

    def test_func(self):
        return self.get_object().author == self.request.user

    def handle_no_permission(self):
        return redirect('blog:post_detail', post_id=self.kwargs['post_id'])


class PostFormMixin:
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def get_success_url(self):
        return reverse('blog:post_detail', args=[self.object.pk])


class PostCreateView(LoginRequiredMixin, PostFormMixin, CreateView):

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:profile', args=[self.request.user.username])


class PostUpdateView(
    LoginRequiredMixin, OnlyAuthorMixin, PostFormMixin, UpdateView,
):
    pass


class PostDeleteView(LoginRequiredMixin, OnlyAuthorMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'
    success_url = reverse_lazy('blog:index')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm(instance=self.object)
        return context


@login_required
@require_POST
def add_comment(request, post_id):
    post = get_object_or_404(get_visible_posts(request.user), pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect('blog:post_detail', post_id=post_id)
    context = {
        'post': post,
        'form': form,
        'comments': post.comments.select_related('author'),
    }
    return render(request, 'blog/detail.html', context)


class CommentMixin:
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def get_queryset(self):
        return Comment.objects.filter(post_id=self.kwargs['post_id'])

    def get_success_url(self):
        return reverse('blog:post_detail', args=[self.kwargs['post_id']])


class CommentUpdateView(
    LoginRequiredMixin, OnlyAuthorMixin, CommentMixin, UpdateView,
):
    form_class = CommentForm


class CommentDeleteView(
    LoginRequiredMixin, OnlyAuthorMixin, CommentMixin, DeleteView,
):
    pass
