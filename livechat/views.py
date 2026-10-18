"""Public list, detail, archive and CSRF-protected question submission views."""

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView

from .forms import LiveChatQuestionForm
from .models import LiveChat


class LiveChatIndexView(ListView):
    model = LiveChat
    template_name = 'livechat/index.html'
    context_object_name = 'livechats'
    paginate_by = 12

    def get_queryset(self):
        return LiveChat.objects.filter(is_cancelled=False).order_by('-chat_starts_at')


class LiveChatDetailView(DetailView):
    model = LiveChat
    template_name = 'livechat/show.html'
    context_object_name = 'live_chat'
    slug_field = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        questions = self.object.questions.filter(is_approved=True, is_removed=False).prefetch_related(
            'responses__author'
        )
        context['chat_questions'] = Paginator(questions, 10).get_page(self.request.GET.get('p'))
        allowed, reason = self.object.can_comment(self.request)
        context['can_comment'] = allowed
        context['can_comment_code'] = reason
        context.setdefault('question_form', LiveChatQuestionForm())
        context['just_submitted'] = self.request.GET.get('submitted') == '1'
        return context


class LiveChatArchiveView(ListView):
    template_name = 'livechat/archived_chat.html'
    context_object_name = 'livechats'
    paginate_by = 10

    def get_queryset(self):
        return LiveChat.objects.filter(
            is_cancelled=False, chat_ends_at__lte=timezone.now()
        ).order_by('-chat_ends_at')


@require_POST
def ask_question(request, slug):
    chat = get_object_or_404(LiveChat, slug=slug)
    form = LiveChatQuestionForm(request.POST)
    if not form.is_valid():
        # Render validation errors through the same detail page.
        view = LiveChatDetailView()
        view.setup(request, slug=slug)
        view.object = chat
        context = view.get_context_data(question_form=form)
        return render(request, view.template_name, context, status=400)

    # A local-memory cache works in development; use shared cache + CAPTCHA for production.
    cooldown = int(getattr(settings, 'LIVECHAT_QUESTION_COOLDOWN_SECONDS', 30))
    if cooldown > 0:
        identity = str(request.user.pk) if request.user.is_authenticated else request.META.get('REMOTE_ADDR', 'unknown')
        key = f'livechat:question:{chat.pk}:{identity}'
        if not cache.add(key, '1', timeout=cooldown):
            return HttpResponse('Please wait before sending another question.', status=429)

    with transaction.atomic():
        # Serializes writes on databases that support row locking.
        chat = LiveChat.objects.select_for_update().get(pk=chat.pk)
        allowed, reason = chat.can_comment(request)
        if not allowed:
            messages.error(request, 'Questions cannot be submitted to this chat right now.')
            return redirect('livechat:show_livechat', slug=chat.slug)
        question = form.save(commit=False)
        question.livechat = chat
        if request.user.is_authenticated:
            question.user = request.user
        question.save()
        chat.check_max_comments()

    return redirect(f'{chat.get_absolute_url()}?submitted=1')
