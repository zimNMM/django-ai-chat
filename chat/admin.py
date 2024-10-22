# chat/admin.py

from django.contrib import admin

from .models import Prompt, Credits, NebiusModel, OobaboogaCharacter, Profile, OllamaModel

@admin.register(Credits)
class CreditsAdmin(admin.ModelAdmin):
    list_display = ('user', 'credits')
    search_fields = ('user__username',)

@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)

@admin.register(NebiusModel)
class NebiusModelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(OobaboogaCharacter)
class OobaboogaCharacterAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(OllamaModel)
class OllamaModelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'backend_api_choice', 'selected_model', 'selected_character', 'selected_ollama_model','otp_enabled')
    list_filter = ('backend_api_choice', 'otp_enabled')
    search_fields = ('user__username',)