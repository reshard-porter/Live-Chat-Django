from django.urls import path

from .views import LiveChatArchiveView, LiveChatDetailView, LiveChatIndexView, ask_question

app_name = 'livechat'

urlpatterns = [
    path('livechat/', LiveChatIndexView.as_view(), name='index'),
    path('livechat/archive/', LiveChatArchiveView.as_view(), name='show_archived_livechat'),
    path('livechat/<slug:slug>/ask/', ask_question, name='ask_question'),
    path('livechat/<slug:slug>/', LiveChatDetailView.as_view(), name='show_livechat'),
]
