"""Run with ``python manage.py test livechat`` after installing Django."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from livechat.context_processors import current_livechat
from livechat.forms import LiveChatQuestionForm
from livechat.models import LiveChat, LiveChatQuestion, LiveChatResponse


@override_settings(LIVECHAT_QUESTION_COOLDOWN_SECONDS=0)
class LiveChatTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.chat = LiveChat.objects.create(
            title='Ask the Expert',
            slug='ask-the-expert',
            description='Helpful session details.',
            expert='Test Expert',
            chat_starts_at=self.now - timedelta(minutes=30),
            chat_ends_at=self.now + timedelta(minutes=30),
        )
        self.detail_url = reverse('livechat:show_livechat', kwargs={'slug': self.chat.slug})
        self.ask_url = reverse('livechat:ask_question', kwargs={'slug': self.chat.slug})
        self.staff = get_user_model().objects.create_superuser(
            username='moderator', email='moderator@example.com', password='local-test-password'
        )

    def question(self, **kwargs):
        attrs = {'livechat': self.chat, 'name': 'Visitor', 'body': 'A sample question'}
        attrs.update(kwargs)
        return LiveChatQuestion.objects.create(**attrs)

    def test_index_detail_archive_and_home_are_routable(self):
        self.assertEqual(self.client.get('/').status_code, 302)
        self.assertContains(self.client.get(reverse('livechat:index')), self.chat.title)
        self.assertContains(self.client.get(self.detail_url), self.chat.title)
        self.assertEqual(self.client.get(reverse('livechat:show_archived_livechat')).status_code, 200)
        self.assertEqual(self.client.get('/livechat/does-not-exist/').status_code, 404)

    def test_date_validation_and_generic_link(self):
        self.chat.chat_ends_at = self.chat.chat_starts_at
        with self.assertRaises(ValidationError):
            self.chat.full_clean()
        self.chat.chat_ends_at = self.now + timedelta(minutes=30)
        self.chat.object_id = 12
        with self.assertRaises(ValidationError):
            self.chat.full_clean()

    def test_session_checks_both_start_and_end(self):
        self.assertTrue(self.chat.is_in_progress())
        self.assertEqual(self.chat.can_comment(), (True, 'open'))
        self.chat.chat_starts_at = self.now + timedelta(hours=1)
        self.chat.chat_ends_at = self.now + timedelta(hours=2)
        self.assertFalse(self.chat.is_in_progress())
        self.assertEqual(self.chat.can_comment()[1], 'not_started')
        self.chat.chat_starts_at = self.now - timedelta(hours=2)
        self.chat.chat_ends_at = self.now - timedelta(hours=1)
        self.assertFalse(self.chat.is_in_progress())
        self.assertEqual(self.chat.can_comment()[1], 'ended')
        self.chat.is_cancelled = True
        self.assertEqual(self.chat.can_comment()[1], 'cancelled')

    def test_max_questions_none_zero_and_one(self):
        self.assertEqual(self.chat.can_comment()[0], True)
        self.chat.maximum_questions = 0
        self.assertEqual(self.chat.can_comment()[1], 'limit_reached')
        self.chat.maximum_questions = 1
        self.client.post(self.ask_url, {'name': 'Jo', 'body': 'Will it work?'})
        self.assertEqual(self.chat.questions.count(), 1)
        self.chat.refresh_from_db()
        self.assertTrue(self.chat.comments_closed)
        self.assertFalse(self.chat.can_comment()[0])
        self.client.post(self.ask_url, {'name': 'Jo', 'body': 'A second question'})
        self.assertEqual(self.chat.questions.count(), 1)

    def test_login_page_is_available(self):
        self.assertContains(self.client.get(reverse('login')), 'Sign in')
        with override_settings(LIVECHAT_ALLOW_ANONYMOUS=False):
            self.assertContains(self.client.get(self.detail_url), 'Sign in')

    def test_get_never_creates_question(self):
        self.assertEqual(self.client.get(self.ask_url).status_code, 405)
        self.assertFalse(self.chat.questions.exists())

    def test_question_form_validation_and_honeypot(self):
        self.assertFalse(LiveChatQuestionForm(data={'name': 'Name', 'body': ''}).is_valid())
        self.assertFalse(LiveChatQuestionForm(data={'name': 'Name', 'body': 'Text', 'website': 'spam'}).is_valid())
        self.assertEqual(self.client.post(self.ask_url, {'name': '', 'body': 'Question'}).status_code, 400)
        self.assertEqual(self.chat.questions.count(), 0)

    def test_post_creates_unapproved_question_and_shows_confirmation(self):
        response = self.client.post(self.ask_url, {'name': 'Guest', 'body': 'What is new?'})
        self.assertRedirects(response, f'{self.detail_url}?submitted=1')
        question = self.chat.questions.get()
        self.assertFalse(question.is_approved)
        self.assertContains(self.client.get(response.url), 'awaiting moderation')
        self.assertNotContains(self.client.get(self.detail_url), 'What is new?')
        question.is_approved = True
        question.save()
        self.assertContains(self.client.get(self.detail_url), 'What is new?')

    def test_question_requires_active_session_and_not_cancelled(self):
        self.chat.is_cancelled = True
        self.chat.save()
        self.assertRedirects(self.client.post(self.ask_url, {'name': 'G', 'body': 'Hello'}), self.detail_url)
        self.chat.is_cancelled = False
        self.chat.is_archived = True
        self.chat.save()
        self.assertRedirects(self.client.post(self.ask_url, {'name': 'G', 'body': 'Hello'}), self.detail_url)
        self.assertFalse(self.chat.questions.exists())

    def test_auth_optional(self):
        with override_settings(LIVECHAT_ALLOW_ANONYMOUS=False):
            self.assertEqual(self.chat.can_comment()[1], 'auth_required')
            self.client.post(self.ask_url, {'name': 'Guest', 'body': 'Hello'})
            self.assertEqual(self.chat.questions.count(), 0)
            self.client.force_login(self.staff)
            response = self.client.post(self.ask_url, {'name': 'Member', 'body': 'Hello'})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(self.chat.questions.get().user, self.staff)

    def test_removed_questions_not_public_and_html_is_escaped(self):
        self.chat.description = '<script>alert("xss")</script>'
        self.chat.save()
        approved = self.question(name='<img src=x>', body='<script>bad()</script>', is_approved=True)
        hidden = self.question(body='Secret question', is_approved=True, is_removed=True)
        page = self.client.get(self.detail_url)
        self.assertContains(page, '&lt;script&gt;bad()&lt;/script&gt;')
        self.assertContains(page, '&lt;img src=x&gt;')
        self.assertNotContains(page, '<script>alert(', html=False)
        self.assertNotContains(page, 'Secret question')
        self.assertEqual(self.chat.comment_set().count(), 1)

    def test_reply_appears_only_for_published_question(self):
        question = self.question(is_approved=True)
        LiveChatResponse.objects.create(
            livechat=self.chat, question=question, author=self.staff, response='Here is the answer'
        )
        self.assertContains(self.client.get(self.detail_url), 'Here is the answer')
        question.is_approved = False
        question.save()
        self.assertNotContains(self.client.get(self.detail_url), 'Here is the answer')

    def test_reply_cannot_link_to_another_chat(self):
        q = self.question()
        other = LiveChat.objects.create(
            title='Another', slug='another',
            chat_starts_at=self.now, chat_ends_at=self.now + timedelta(hours=1)
        )
        response = LiveChatResponse(question=q, livechat=other, author=self.staff, response='Hello')
        with self.assertRaises(ValidationError):
            response.full_clean()

    def test_upcoming_prefers_current_then_nearest_and_only_five_days(self):
        self.assertEqual(LiveChat.chat_finder.get_current_live_chat(), self.chat)
        self.assertEqual(LiveChat.chat_finder.upcoming_live_chat(), self.chat)
        self.chat.is_archived = True
        self.chat.save()
        soon = LiveChat.objects.create(
            title='Soon', slug='soon',
            chat_starts_at=self.now + timedelta(days=2),
            chat_ends_at=self.now + timedelta(days=2, hours=1),
        )
        LiveChat.objects.create(
            title='Later', slug='later',
            chat_starts_at=self.now + timedelta(days=8),
            chat_ends_at=self.now + timedelta(days=8, hours=1),
        )
        self.assertEqual(LiveChat.chat_finder.upcoming_live_chat(), soon)
        soon.is_cancelled = True
        soon.save()
        self.assertIsNone(LiveChat.chat_finder.upcoming_live_chat())

    def test_last_chat_only_within_three_days(self):
        self.chat.chat_starts_at = self.now - timedelta(days=2)
        self.chat.chat_ends_at = self.now - timedelta(days=1)
        self.chat.save()
        self.assertEqual(LiveChat.chat_finder.get_last_live_chat(), self.chat)
        self.assertContains(self.client.get(reverse('livechat:show_archived_livechat')), self.chat.title)
        self.chat.chat_ends_at = self.now - timedelta(days=4)
        self.chat.save()
        self.assertIsNone(LiveChat.chat_finder.get_last_live_chat())

    def test_context_processor_with_active_and_no_active_chat(self):
        from django.test import RequestFactory
        request = RequestFactory().get('/')
        request.user = self.staff
        active = current_livechat(request)
        self.assertEqual(active['live_chat']['current_live_chat'], self.chat)
        self.chat.is_archived = True
        self.chat.save()
        self.assertEqual(current_livechat(request), {})

    def test_admin_change_and_participate_require_authentication(self):
        url = reverse('admin:livechat_livechat_participate', args=[self.chat.pk])
        anonymous = self.client.get(url)
        self.assertEqual(anonymous.status_code, 302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get(reverse('admin:livechat_livechat_change', args=[self.chat.pk])), 'Moderate questions / reply')

    def test_admin_archive_requires_post_and_mod_actions_work(self):
        question = self.question()
        url = reverse('admin:livechat_livechat_participate', args=[self.chat.pk])
        self.client.force_login(self.staff)
        self.client.get(url + '?archive=1')
        self.chat.refresh_from_db()
        self.assertFalse(self.chat.is_archived)
        self.client.post(url, {'action': 'respond', 'question_id': question.pk, 'response': 'Answer from staff'})
        question.refresh_from_db()
        self.assertTrue(question.is_approved)
        self.assertEqual(question.responses.get().response, 'Answer from staff')
        self.client.post(url, {'action': 'hide', 'question_id': question.pk})
        question.refresh_from_db()
        self.assertTrue(question.is_removed)
        self.client.post(url, {'action': 'approve', 'question_id': question.pk})
        question.refresh_from_db()
        self.assertFalse(question.is_removed)
        self.client.post(url, {'action': 'archive'})
        self.chat.refresh_from_db()
        self.assertTrue(self.chat.is_archived)
        self.assertTrue(self.chat.comments_closed)

    def test_admin_cannot_respond_to_question_in_another_chat(self):
        other = LiveChat.objects.create(
            title='Other', slug='other',
            chat_starts_at=self.now, chat_ends_at=self.now + timedelta(hours=1)
        )
        question = LiveChatQuestion.objects.create(livechat=other, name='User', body='Question')
        self.client.force_login(self.staff)
        url = reverse('admin:livechat_livechat_participate', args=[self.chat.pk])
        result = self.client.post(url, {'action': 'respond', 'question_id': question.pk, 'response': 'Nope'})
        self.assertEqual(result.status_code, 404)
        self.assertFalse(LiveChatResponse.objects.exists())

    def test_demo_command_creates_valid_session_idempotently(self):
        call_command('create_demo_chat', verbosity=0)
        demo = LiveChat.objects.get(slug='demo-live-chat')
        self.assertTrue(demo.is_in_progress())
        call_command('create_demo_chat', verbosity=0)
        self.assertEqual(LiveChat.objects.filter(slug='demo-live-chat').count(), 1)

    @override_settings(LIVECHAT_QUESTION_COOLDOWN_SECONDS=60)
    def test_cooldown_rejects_second_question(self):
        from django.core.cache import cache
        cache.clear()
        self.assertEqual(self.client.post(self.ask_url, {'name': 'A', 'body': 'First'}).status_code, 302)
        self.assertEqual(self.client.post(self.ask_url, {'name': 'B', 'body': 'Second'}).status_code, 429)
        self.assertEqual(self.chat.questions.count(), 1)
