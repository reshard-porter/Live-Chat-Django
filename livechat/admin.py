"""Modern admin UI for scheduling, moderation, and staff replies."""

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse

from .models import LiveChat, LiveChatQuestion, LiveChatResponse


class ResponseInline(admin.StackedInline):
    model = LiveChatResponse
    extra = 0
    fields = ('response',)
    readonly_fields = ()
    # livechat and author are populated by the parent admin when saved.
    exclude = ('livechat', 'author')


@admin.register(LiveChat)
class LiveChatAdmin(admin.ModelAdmin):
    change_form_template = 'admin/livechat/livechat/change_form.html'
    list_display = ('title', 'expert', 'chat_starts_at', 'chat_ends_at', 'is_cancelled', 'is_archived')
    list_filter = ('is_cancelled', 'is_archived', 'comments_closed')
    search_fields = ('title', 'expert', 'description')
    prepopulated_fields = {'slug': ('title',)}
    actions = ('cancel_live_chat', 'archive_live_chat')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'expert', 'description')}),
        ('Schedule', {'fields': ('chat_starts_at', 'chat_ends_at', 'maximum_questions')}),
        ('Status', {'fields': ('comments_closed', 'is_cancelled', 'is_archived')}),
        ('Optional linked content', {'fields': ('content_type', 'object_id'), 'classes': ('collapse',)}),
    )

    @admin.action(description='Cancel selected live chats')
    def cancel_live_chat(self, request, queryset):
        count = queryset.update(is_cancelled=True)
        self.message_user(request, f'Cancelled {count} live chat(s).')

    @admin.action(description='Archive selected live chats')
    def archive_live_chat(self, request, queryset):
        count = queryset.update(is_archived=True, comments_closed=True)
        self.message_user(request, f'Archived {count} live chat(s).')

    def get_urls(self):
        extra = [
            path(
                '<int:chat_id>/participate/',
                self.admin_site.admin_view(self.participate_view),
                name='livechat_livechat_participate',
            ),
        ]
        return extra + super().get_urls()

    def participate_view(self, request, chat_id):
        chat = get_object_or_404(LiveChat, pk=chat_id)
        if not self.has_change_permission(request, chat):
            raise PermissionDenied
        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'archive':
                chat.is_archived = True
                chat.comments_closed = True
                chat.save(update_fields=['is_archived', 'comments_closed', 'updated'])
                messages.success(request, 'Chat archived and questions closed.')
            elif action in ('approve', 'hide', 'respond'):
                question = get_object_or_404(chat.questions, pk=request.POST.get('question_id'))
                if action == 'approve':
                    question.is_approved = True
                    question.is_removed = False
                    question.save(update_fields=['is_approved', 'is_removed'])
                    messages.success(request, 'Question approved.')
                elif action == 'hide':
                    question.is_removed = True
                    question.save(update_fields=['is_removed'])
                    messages.success(request, 'Question hidden.')
                elif action == 'respond':
                    response_text = request.POST.get('response', '').strip()
                    if response_text and len(response_text) <= 10000:
                        LiveChatResponse.objects.create(
                            livechat=chat, question=question, author=request.user, response=response_text
                        )
                        # A reply approves the question, unless it was deliberately removed.
                        if not question.is_removed and not question.is_approved:
                            question.is_approved = True
                            question.save(update_fields=['is_approved'])
                        messages.success(request, 'Response saved.')
                    else:
                        messages.error(request, 'Reply must contain 1 to 10,000 characters.')
            else:
                messages.error(request, 'Unknown action.')
            return HttpResponseRedirect(request.path)

        questions = chat.questions.select_related('user').prefetch_related('responses__author')
        answered = request.GET.get('answered')
        if answered == 'true':
            questions = questions.filter(responses__isnull=False).distinct()
        elif answered == 'false':
            questions = questions.filter(responses__isnull=True)

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'original': chat,
            'livechat': chat,
            'title': f'Participate in {chat.title}',
            'questions': Paginator(questions, 20).get_page(request.GET.get('p')),
            'answered_filter': answered or '',
            'unanswered_count': chat.questions.filter(responses__isnull=True).count(),
        }
        return TemplateResponse(request, 'admin/livechat/livechat/participate.html', context)


@admin.register(LiveChatQuestion)
class LiveChatQuestionAdmin(admin.ModelAdmin):
    list_display = ('name', 'livechat', 'created_at', 'is_approved', 'is_removed', 'response_count')
    list_filter = ('livechat', 'is_approved', 'is_removed')
    search_fields = ('name', 'body', 'livechat__title')
    readonly_fields = ('created_at',)
    actions = ('approve_questions', 'hide_questions')
    inlines = (ResponseInline,)

    @admin.display(description='Replies')
    def response_count(self, obj):
        return obj.responses.count()

    @admin.action(description='Approve selected questions')
    def approve_questions(self, request, queryset):
        queryset.update(is_approved=True, is_removed=False)

    @admin.action(description='Hide selected questions')
    def hide_questions(self, request, queryset):
        queryset.update(is_removed=True)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for removed in formset.deleted_objects:
            removed.delete()
        for obj in instances:
            if isinstance(obj, LiveChatResponse):
                obj.author = obj.author_id and obj.author or request.user
                obj.livechat = form.instance.livechat
            obj.save()
        formset.save_m2m()


@admin.register(LiveChatResponse)
class LiveChatResponseAdmin(admin.ModelAdmin):
    list_display = ('question', 'author', 'livechat', 'created_at')
    list_filter = ('livechat',)
    search_fields = ('response', 'question__body')
    exclude = ('author',)

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)
