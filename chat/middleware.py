# chat/middleware.py

from django.core.cache import cache
import threading
import time
from openai import OpenAI
import requests
import os
from .models import OllamaModel, OpenAIModel, NebiusModel
from dotenv import load_dotenv

__all__ = ['ModelSyncMiddleware']

load_dotenv()

class ModelSyncThread(threading.Thread):
    """Background thread for model synchronization."""
    
    def __init__(self):
        super().__init__(daemon=True)
        self.stop_flag = threading.Event()
        
    def run(self):
        while not self.stop_flag.is_set():
            try:
                self.sync_all_models()
            except Exception as e:
                print(f"Error syncing models: {e}")
            self.stop_flag.wait(3600)
    
    def sync_all_models(self):
        """Synchronize all models from different APIs."""
        self.sync_openai_nebius_models()
        self.sync_ollama_models()
        cache.set('last_sync_time', time.time())
        
    def sync_openai_nebius_models(self):
        """Sync OpenAI and Nebius models."""
        try:
            client_openai = OpenAI(
                base_url="https://api.openai.com/v1/",
                api_key=os.getenv("OPENAI_API_KEY")
            )
            client_nebius = OpenAI(
                base_url="https://api.studio.nebius.ai/v1/",
                api_key=os.getenv("NEBIUS_API_KEY")
            )
            
            openai_models = client_openai.models.list()
            current_openai_models = set(OpenAIModel.objects.values_list('name', flat=True))
            api_openai_models = set(model.id for model in openai_models)
            
            for model_name in api_openai_models - current_openai_models:
                OpenAIModel.objects.create(name=model_name)
            
            OpenAIModel.objects.filter(name__in=current_openai_models - api_openai_models).delete()
            
            nebius_models = client_nebius.models.list()
            current_nebius_models = set(NebiusModel.objects.values_list('name', flat=True))
            api_nebius_models = set(model.id for model in nebius_models)
            
            for model_name in api_nebius_models - current_nebius_models:
                NebiusModel.objects.create(name=model_name)
            
            NebiusModel.objects.filter(name__in=current_nebius_models - api_nebius_models).delete()
            print("Successfully synced OpenAI and Nebius models")
            
        except Exception as e:
            print(f"Error syncing OpenAI and Nebius models: {e}")

    def sync_ollama_models(self):
        """Sync Ollama models."""
        try:
            ollama_url = os.getenv("OLLAMA_URL")
            response = requests.get(f"{ollama_url}/api/tags")
            
            if response.status_code == 200:
                data = response.json()
                api_models = {model['name'] for model in data.get('models', [])}
                current_models = set(OllamaModel.objects.values_list('name', flat=True))
                
                for model_name in api_models - current_models:
                    OllamaModel.objects.create(name=model_name)
                
                OllamaModel.objects.filter(name__in=current_models - api_models).delete()
                
                print("Successfully synced Ollama models")
            else:
                print(f"Error syncing Ollama models")
                
        except Exception as e:
            print(f"Error syncing Ollama models: {e}")

class ModelSyncMiddleware:
    """Middleware to handle model synchronization on application startup."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.sync_thread = None
        self.initialize_sync_thread()
    
    def initialize_sync_thread(self):
        """Initialize and start the model sync thread if not already running."""
        if not self.sync_thread or not self.sync_thread.is_alive():
            self.sync_thread = ModelSyncThread()
            self.sync_thread.start()
    
    def __call__(self, request):
        return self.get_response(request)
    
    def __del__(self):
        """Clean up the sync thread when the middleware is destroyed."""
        if self.sync_thread:
            self.sync_thread.stop_flag.set()
            self.sync_thread.join(timeout=1)