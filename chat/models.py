# chat/models.py

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

import pyotp
import uuid

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    summary = models.TextField(blank=True, null=True)
    def __str__(self):
        return f'Conversation {self.id}'

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10)
    text = models.TextField()
    image = models.ImageField(upload_to='generated_images/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    @property
    def reaction_counts(self):
        return {
            'up': self.reactions.filter(reaction='up').count(),
            'down': self.reactions.filter(reaction='down').count()
        }
class Credits(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    credits = models.IntegerField()

class NebiusModel(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name
    
class OllamaModel(models.Model):
    name = models.CharField(max_length=255, unique=True)
    
    def __str__(self):
        return self.name
class OobaboogaCharacter(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name
    
class OpenAIModel(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name
    
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp_enabled = models.BooleanField(default=False)
    otp_secret_key = models.CharField(max_length=16, blank=True, null=True)
    BACKEND_API_CHOICES = [
        ('oobabooga', 'Oobabooga'),
        ('nebius', 'Nebius'),
        ('ollama', 'Ollama'),
        ('openai', 'OpenAI'),
    ]
    
    backend_api_choice = models.CharField(max_length=20, choices=BACKEND_API_CHOICES, default='oobabooga')
    selected_model = models.ForeignKey(NebiusModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='profiles')
    selected_character = models.ForeignKey(OobaboogaCharacter, on_delete=models.SET_NULL, null=True, blank=True, related_name='profiles')
    selected_ollama_model = models.ForeignKey(OllamaModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='ollama_profiles')
    selected_openai_model = models.ForeignKey(OpenAIModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='openai_profiles')
    
    def __str__(self):
        return f'Profile for {self.user.username}'

    def generate_otp_secret_key(self):
        self.otp_secret_key = pyotp.random_base32()
        self.save()

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()
        
class Prompt(models.Model):
    name = models.CharField(max_length=100, unique=True)
    content = models.TextField()
    explanation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
class MessageReaction(models.Model):
    REACTION_CHOICES = [
        ('up', 'Thumbs Up'),
        ('down', 'Thumbs Down')
    ]
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction = models.CharField(max_length=5, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['message', 'user']
