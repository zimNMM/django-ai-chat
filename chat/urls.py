# chat/urls.py

from . import views

from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('login/', views.custom_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', views.chat_view, name='chat'),
    path('profile/', views.profile_view, name='profile'),
    path('ajax/send_message/', views.send_message, name='send_message'),
    path('ajax/get_messages/', views.get_messages, name='get_messages'),
    path('ajax/get_conversations/', views.get_conversations, name='get_conversations'),
    path('ajax/delete_conversation/', views.delete_conversation, name='delete_conversation'),
    path('ajax/delete_all_conversations/', views.delete_all_conversations, name='delete_all_conversations'),
    path('ajax/delete_user_account/', views.delete_user_account, name='delete_user_account'),
    path('ajax/export/', views.export_all_conversations, name='export_all_conversations'),
    path('ajax/generate_image/', views.generate_image, name='generate_image'),
    path('ajax/get_prompts/', views.get_prompts, name='get_prompts'),
    path('conversations/<uuid:uuid>/', views.public_conversation_view, name='public_conversation'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
