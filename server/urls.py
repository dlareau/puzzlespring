"""server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, reverse_lazy, include
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from allauth.account.decorators import secure_admin_login

admin.site.login = secure_admin_login(admin.site.login)

urlpatterns = [
    # Admin redirections/views
    # path('admin/login/', RedirectView.as_view(url=reverse_lazy(settings.LOGIN_URL), query_string=True)),
    path('admin/', admin.site.urls),

    path('accounts/', include('allauth.urls')),

    # Impersonate URLs
    path('impersonate/', include('impersonate.urls')),

    # Puzzlehunt URLs
    path('', include('puzzlehunt.urls')),

    # Password reset views:
    path('password_reset/', auth_views.PasswordResetView.as_view(),
         name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>', auth_views.PasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(),
         name='password_reset_complete'),
]

# Hack for using development server
if settings.DEBUG:
    urlpatterns.append(path('__debug__/', include('debug_toolbar.urls')))
