"""Create or reset a chat window so a fresh install can be tried immediately."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from livechat.models import LiveChat


class Command(BaseCommand):
    help = 'Create or refresh a demo chat that accepts questions for the next 2 hours.'

    def handle(self, *args, **options):
        now = timezone.now()
        chat, created = LiveChat.objects.update_or_create(
            slug='demo-live-chat',
            defaults={
                'title': 'Welcome to Live Chat',
                'description': 'Ask a question and a moderator can respond in the Django admin.',
                'expert': 'Demo Expert',
                'chat_starts_at': now - timedelta(minutes=5),
                'chat_ends_at': now + timedelta(hours=2),
                'comments_closed': False,
                'is_cancelled': False,
                'is_archived': False,
                'maximum_questions': None,
            },
        )
        label = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{label} demo chat at {chat.get_absolute_url()}'))
