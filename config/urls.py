from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect
from django.urls import include, path, reverse


def home(request):
    return HttpResponseRedirect(reverse('livechat:index'))


urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='livechat/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='livechat:index'), name='logout'),
    path('', include('livechat.urls')),
]
