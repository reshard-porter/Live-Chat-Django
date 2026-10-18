"""Optional live-chat banner and inclusion tags for other site templates."""

from django import template
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.urls import reverse

from livechat.models import LiveChat

register = template.Library()


@register.inclusion_tag('livechat/inclusion_tags/live_chat_banner.html', takes_context=True)
def live_chat_banner(context):
    return {
        'last_live_chat': LiveChat.chat_finder.get_last_live_chat(),
        'live_chat_advert': LiveChat.chat_finder.upcoming_live_chat(),
    }


@register.inclusion_tag('livechat/inclusion_tags/live_chat.html', takes_context=True)
def show_live_chat(context):
    request = context.get('request')
    chat = context.get('live_chat')
    if not isinstance(chat, LiveChat):
        chat = LiveChat.chat_finder.upcoming_live_chat()
    result = {'live_chat': chat, 'request': request}
    if chat is not None:
        allowed, reason = chat.can_comment(request)
        result['can_comment'] = allowed
        result['can_comment_code'] = reason
        questions = chat.questions.filter(is_approved=True, is_removed=False).prefetch_related('responses__author')
        page = request.GET.get('p') if request else None
        result['chat_questions'] = Paginator(questions, 10).get_page(page)
        from livechat.forms import LiveChatQuestionForm
        result['question_form'] = LiveChatQuestionForm()
    return result


@register.simple_tag(takes_context=True)
def get_livechat_for_article(context, post, var_name):
    content_type = ContentType.objects.get_for_model(post)
    chat = LiveChat.objects.filter(content_type=content_type, object_id=post.pk).first()
    context[var_name] = chat
    return ''


@register.inclusion_tag('livechat/inclusion_tags/last_live_chat_banner.html')
def archive_live_chat():
    return {'url': reverse('livechat:show_archived_livechat')}
