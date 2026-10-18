from .models import LiveChat


def current_livechat(request):
    """Expose a current session for host-project navigation templates."""
    chat = LiveChat.chat_finder.get_current_live_chat()
    if chat is None:
        return {}
    allowed, reason = chat.can_comment(request)
    return {'live_chat': {
        'current_live_chat': chat,
        'can_render_comment_form': allowed,
        'can_comment_code': reason,
    }}
