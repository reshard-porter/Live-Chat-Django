"""Scheduled, moderated Q&A chats on supported versions of Django."""

from datetime import timedelta

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class LiveChatManager(models.Manager):
    """Finding current, forthcoming and recently finished chats."""

    def upcoming_live_chat(self):
        now = timezone.now()
        chats = self.get_queryset().filter(
            is_cancelled=False,
            is_archived=False,
            chat_ends_at__gt=now,
            chat_starts_at__lte=now + timedelta(days=5),
        )
        current = chats.filter(chat_starts_at__lte=now).order_by('-chat_starts_at').first()
        return current or chats.filter(chat_starts_at__gt=now).order_by('chat_starts_at').first()

    def get_current_live_chat(self):
        now = timezone.now()
        return self.get_queryset().filter(
            is_cancelled=False,
            is_archived=False,
            chat_starts_at__lte=now,
            chat_ends_at__gt=now,
        ).order_by('-chat_starts_at').first()

    def get_last_live_chat(self):
        now = timezone.now()
        return self.get_queryset().filter(
            is_cancelled=False,
            chat_ends_at__lte=now,
            chat_ends_at__gt=now - timedelta(days=3),
        ).order_by('-chat_ends_at').first()


class LiveChat(models.Model):
    """A timed question-and-answer session, not a WebSocket chat room."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    expert = models.CharField(max_length=100, blank=True)
    chat_starts_at = models.DateTimeField(db_index=True)
    chat_ends_at = models.DateTimeField(db_index=True)
    maximum_questions = models.PositiveIntegerField(
        null=True, blank=True, help_text='Leave blank for no question limit; 0 closes submissions.'
    )
    comments_closed = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    # Optional attachment to a model in the host Django site.
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True, related_name='livechat_sessions'
    )
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    objects = LiveChatManager()
    chat_finder = LiveChatManager()  # Keeps the old public manager name.

    class Meta:
        ordering = ('-chat_starts_at',)
        verbose_name = 'Live chat'
        verbose_name_plural = 'Live chats'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("livechat:show_livechat", kwargs={"slug": self.slug})

    def clean(self):
        super().clean()
        if self.chat_starts_at and self.chat_ends_at and self.chat_ends_at <= self.chat_starts_at:
            raise ValidationError({'chat_ends_at': 'The end time must be after the start time.'})
        if (self.content_type_id is None) != (self.object_id is None):
            raise ValidationError('Both content type and object ID must be set, or neither.')

    def is_in_progress(self):
        now = timezone.now()
        return (
            not self.is_cancelled and not self.is_archived
            and self.chat_starts_at <= now < self.chat_ends_at
        )

    def comment_set(self):
        """Compatibility helper for code that previously used Django comments."""
        return self.questions.filter(is_removed=False).order_by('-created_at')

    def can_comment(self, request=None):
        if self.is_cancelled:
            return False, 'cancelled'
        if self.is_archived or timezone.now() >= self.chat_ends_at:
            return False, 'ended'
        if timezone.now() < self.chat_starts_at:
            return False, 'not_started'
        if self.comments_closed:
            return False, 'closed'
        if self.maximum_questions is not None and self.comment_set().count() >= self.maximum_questions:
            return False, 'limit_reached'
        if (not getattr(settings, 'LIVECHAT_ALLOW_ANONYMOUS', True)
                and (request is None or not request.user.is_authenticated)):
            return False, 'auth_required'
        return True, 'open'

    def check_max_comments(self):
        """Close when the question limit is reached (including pending questions)."""
        if (self.maximum_questions is not None
                and self.comment_set().count() >= self.maximum_questions
                and not self.comments_closed):
            self.comments_closed = True
            self.save(update_fields=['comments_closed', 'updated'])
        return self.comments_closed


class LiveChatQuestion(models.Model):
    livechat = models.ForeignKey(LiveChat, on_delete=models.CASCADE, related_name='questions')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    name = models.CharField(max_length=80)
    body = models.TextField(max_length=3000)
    is_approved = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.name}: {self.body[:60]}'


class LiveChatResponse(models.Model):
    livechat = models.ForeignKey(LiveChat, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(
        LiveChatQuestion, on_delete=models.CASCADE, related_name='responses'
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    response = models.TextField(max_length=10000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('created_at',)

    def clean(self):
        super().clean()
        if self.question_id and self.livechat_id and self.question.livechat_id != self.livechat_id:
            raise ValidationError('The response and question must belong to the same chat.')

    def __str__(self):
        return f'Reply from {self.author}: {self.response[:50]}'
