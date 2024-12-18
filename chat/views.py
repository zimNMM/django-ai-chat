# chat/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.files.base import ContentFile
from django.db.models import Q
from django.core.cache import cache
from django.conf import settings
from django.urls import reverse

from .models import Conversation, Message, Credits, Prompt, MessageReaction
from .forms import CustomPasswordChangeForm, OTPEnableForm, CustomAuthenticationForm, BackendAPIChoiceForm

import os
from openai import OpenAI
import requests
import json
import pyotp
import qrcode
from io import BytesIO
import base64
import uuid
import socket
from urllib.parse import urlparse
from functools import wraps
import time


ooba_url =  settings.OOBA_URL
img_url = settings.SD_URL
ollama_url = settings.OLLAMA_URL

# ==============================================================================
# Section 1: Utility Functions
# ==============================================================================


def rate_limit(key, limit, period):
    """
    Decorator to implement rate limiting for views.

    Args:
        key (str): A unique identifier for the rate limit.
        limit (int): The maximum number of requests allowed within the period.
        period (int): The time period in seconds for the rate limit.

    Returns:
        function: The decorated view function.

    This decorator checks if the number of requests from a user exceeds
    the specified limit within the given time period. If the limit is
    exceeded, it returns an HTTP 429 Too Many Requests response.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            cache_key = f"rate_limit:{key}:{request.user.id}"
            now = time.time()
            request_history = cache.get(cache_key, [])
            
            request_history = [t for t in request_history if now - t < period]
            
            if len(request_history) >= limit:
                return HttpResponse("Rate limit exceeded", status=429)
            
            request_history.append(now)
            cache.set(cache_key, request_history, period)
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator

def check_api_status(url):
    """
    Checks the status of a given API by attempting a socket connection.

    Args:
        url (str): The URL of the API to check.

    Returns:
        str: 'Online' if the API is reachable, 'Offline' otherwise.
    """
    parsed_url = urlparse(url)
    host = parsed_url.hostname
    port = parsed_url.port
    try:
        conn = socket.create_connection((host, port), timeout=2)
        conn.close()
        return 'Online'
    except Exception:
        return 'Offline'

def check_ooba_api_status():
    """Checks the status of the Oobabooga API."""
    return check_api_status(ooba_url)
def check_ollama_api_status():
    """Checks the status of the Ollama API."""
    return check_api_status(ollama_url)
def check_img_api_status():
    """Checks the status of the StableDiffusion API."""
    return check_api_status(img_url)



# ==============================================================================
# Section 2: External API Integrations
# ==============================================================================
    
def send_to_openai(conversation, credits_object, backend_api):
    """
    Sends conversation to the routed backend using the OpenAI library.

    Args:
        conversation (Conversation): The conversation object.
        credits_object (Credits): The user's credits object.
        backend_api (str): The chosen backend API openAI,Nebius or Ollama.

    Returns:
        str: Assistant's response or an error message.
    """
    profile = conversation.user.profile

    if backend_api == 'openai':
        api_key = os.getenv("OPENAI_API_KEY")
        url = "https://api.openai.com/v1/"
        selected_model = profile.selected_openai_model.name if profile.selected_openai_model else None
        if not selected_model:
            return 'Error: No OpenAI model selected.'
    elif backend_api == 'ollama':
        api_key = "ollama"
        url = "http://localhost:11434/v1"
        selected_model = profile.selected_ollama_model.name if profile.selected_ollama_model else None
        if not selected_model:
            return 'Error: No Ollama model selected.'
    elif backend_api == 'nebius':
        api_key = os.getenv("NEBIUS_API_KEY")
        url = "https://api.studio.nebius.ai/v1/"
        selected_model = profile.selected_model.name if profile.selected_model else None
        if not selected_model:
            return 'Error: No Nebius model selected.'

    openai_client = OpenAI(base_url = url, api_key = api_key)
    messages = conversation.messages.order_by('timestamp')
    history = []

    for msg in messages:
        role = 'user' if msg.sender == 'user' else 'assistant'
        history.append({'role': role, 'content': msg.text})
    print(history)
    try:
        response = openai_client.chat.completions.create(
            model=selected_model,
            messages=history,
        )
        assistant_message = response.choices[0].message.content.strip()
        credits_object.credits -= 1
        credits_object.save()
        return assistant_message
    except Exception as e:
        return f'Error: {str(e)}'
    
def send_to_oobabooga(conversation, credits_object):
    """
    Sends conversation to the Oobabooga API and retrieves the assistant's response.

    Args:
        conversation (Conversation): The conversation object.
        credits_object (Credits): The user's credits object.

    Returns:
        str: Assistant's response or an error message.
    """
    headers = {'Content-Type': 'application/json',}
    messages = conversation.messages.order_by('timestamp')
    history = []

    for msg in messages:
        role = 'user' if msg.sender == 'user' else 'assistant'
        history.append({'role': role, 'content': msg.text})
    profile = conversation.user.profile
    selected_character = profile.selected_character.name if profile.selected_character else None
    if not selected_character:
        return 'Error: No Oobabooga character selected.'
    data = {
        'messages': history,
        'mode': 'chat',
        'character': selected_character,
        "temperature": 0.7,
        "max_tokens": 250,
        "top_p": 0.85,
        "frequency_penalty": 0.35,
    }
    try:
        response = requests.post(ooba_url, headers=headers, json=data)
        if response.status_code == 200:
            response_json = response.json()
            assistant_message = response_json['choices'][0]['message']['content']
            credits_object.credits -= 1
            credits_object.save()
            return assistant_message
        else:
            return 'Error: Could not get response from AI.'
    except Exception as e:
        return f'Error: {str(e)}'
    
def generate_summary(user_message, assistant_message):
    """
    Generates a summary of the conversation using OpenAI API.

    Args:
        user_message (str): The user's message.
        assistant_message (str): The assistant's response.

    Returns:
        str: Summary of the conversation.
    """
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = f"Summarize the following conversation between a user and an assistant in 10 words maximum:\n\nUser: {user_message}\nAssistant: {assistant_message}\n\nSummary:"
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes conversations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=25,
        )
        summary = completion.choices[0].message.content.strip()
        return summary
    except Exception as e:
        print(f"Error generating summary: {e}")
        return "No summary available."

def generate_image_from_prompt(prompt):
    """
    Generates an image based on the provided prompt using the StableDiffusion API.

    Args:
        prompt (str): The text prompt for image generation.

    Returns:
        bytes or None: The generated image in bytes or None if failed.
    """
    payload = {
        "prompt": prompt,
        "steps": 20,
        "cfg_scale": 5,
        "width": 512,
        "height": 512,
        "send_images": True,
        "save_images": False,
    }

    try:
        response = requests.post(img_url, json=payload)
        if response.status_code == 200:
            response_data = response.json()
            images = response_data.get('images', [])
            if images:
                image_data = images[0]
                if "," in image_data:
                    base64_data = image_data.split(",", 1)[1]
                else:
                    base64_data = image_data
                image = base64.b64decode(base64_data)
                return image
        else:
            print("API error:", response.text)
            return None
    except Exception as e:
        print(f"Error generating image: {e}")
        return None
    
def send_to_backend(conversation, credits_object, backend_api):
    """
    Routes the conversation to the selected backend API.

    Args:
        conversation (Conversation): The conversation object.
        credits_object (Credits): The user's credits object.
        backend_api (str): The chosen backend API.

    Returns:
        str: Assistant's response or an error message.
    """
    if backend_api == 'oobabooga':
        return send_to_oobabooga(conversation, credits_object)
    elif backend_api == 'nebius':
        return send_to_openai(conversation, credits_object, backend_api)
    elif backend_api == 'ollama':
        return send_to_openai(conversation, credits_object, backend_api)
    elif backend_api == 'openai':
        return send_to_openai(conversation, credits_object, backend_api)
    else:
        return 'Error: Unsupported backend API.'
# ==============================================================================
# Section 3: View Functions
# ==============================================================================
@login_required
def chat_view(request):
    """
    Renders the main chat interface with user's conversations and credit status.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: Rendered chat page.
    """
    user = request.user
    conversations = Conversation.objects.filter(user=request.user).order_by('-created_at')
    if not Credits.objects.filter(user=user).exists():
        Credits.objects.create(user=user, credits=500)
    credits = Credits.objects.get(user=request.user).credits
    initials = user.username[:2].upper()
    ooba_api_status = check_ooba_api_status()
    img_api_status = check_img_api_status()
    ollama_api_status = check_ollama_api_status
    return render(request, 'chat.html', {'conversations': conversations,'credits': credits,'initials': initials,'ooba_api_status': ooba_api_status,'ollama_api_status':ollama_api_status,'img_api_status': img_api_status})

@login_required
def send_message(request):
    """
    Handles sending a user message, interacting with the backend AI, and saving the response.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: Contains the assistant's response, conversation ID, and summary.
    """
    credits = Credits.objects.get(user=request.user)
    if credits.credits <= 0:
        return JsonResponse({'error': 'You have no credits left. Please buy more credits to continue.'}, status=400)
    else:
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                user_message = data.get('message')
                conversation_id = data.get('conversation_id')

                if not user_message:
                    return JsonResponse({'error': 'Message cannot be empty'}, status=400)

                if conversation_id and conversation_id != 'null':
                    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
                else:
                    conversation = Conversation.objects.create(user=request.user)

                Message.objects.create(conversation=conversation, sender='user', text=user_message)
                backend_api = request.user.profile.backend_api_choice
                response_text = send_to_backend(conversation, credits, backend_api)

                bot_message = Message.objects.create(conversation=conversation, sender='bot', text=response_text)

                if conversation.messages.count() == 2:
                    summary = generate_summary(user_message, response_text)
                    conversation.summary = summary
                    conversation.save()
                else:
                    summary = conversation.summary or ''

                return JsonResponse({
                    'response': response_text, 
                    'conversation_id': conversation.id, 
                    'summary': summary,
                    'message_id': bot_message.id,
                    'reaction_counts': bot_message.reaction_counts,
                    'user_reaction': None
                })
            except Exception as e:
                return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def get_messages(request):
    """
    Retrieves all messages for a given conversation.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: Contains messages and conversation summary.
    """
    conversation_id = request.GET.get('conversation_id')
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    messages = conversation.messages.order_by('timestamp')
    messages_data = [{
        'id': msg.id,
        'sender': msg.sender,
        'text': msg.text,
        'image_url': msg.image.url if msg.image else None,
        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'reaction_counts': msg.reaction_counts,
        'user_reaction': msg.reactions.filter(user=request.user).values_list('reaction', flat=True).first()
    } for msg in messages]
    return JsonResponse({'messages': messages_data, 'summary': conversation.summary})

@login_required
def get_conversations(request):
    """
    Retrieves all conversations for the logged-in user.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: Contains a list of conversations.
    """
    conversations = Conversation.objects.filter(user=request.user).order_by('-created_at')
    conversations_data = [
        {
            'id': conv.id,
            'uuid': str(conv.uuid),
            'created_at': conv.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': conv.summary,
        } for conv in conversations
    ]
    return JsonResponse({'conversations': conversations_data})

@login_required
def delete_conversation(request):
    """
    Deletes a specific conversation.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: Status of the deletion.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            conversation_id = data.get('conversation_id')
            conversation = Conversation.objects.get(id=conversation_id, user=request.user)
            conversation.delete()
            return JsonResponse({'status': 'success'})
        except Conversation.DoesNotExist:
            return JsonResponse({'error': 'Conversation not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@rate_limit("delete_all_conversations", limit=1, period=1800)
@login_required
def delete_all_conversations(request):
    """
    Deletes all conversations for the logged-in user.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: Status of the deletion.
    """
    if request.method == 'POST':
        try:
            Conversation.objects.filter(user=request.user).delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def delete_user_account(request):
    """
    Deletes the user's account along with all associated conversations.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponseRedirect or JsonResponse: Redirects to login on success.
    """
    if request.method == "POST":
        try:
            Conversation.objects.filter(user=request.user).delete()
            request.user.delete()
            return redirect('login')           
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@rate_limit("export_all_conversations", limit=1, period=3600)
def export_all_conversations(request):
    """
    Exports all conversations of the user in JSON format.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: JSON file containing all conversations.
    """
    conversations = Conversation.objects.filter(user=request.user).order_by('-created_at')
    if conversations.count() == 0:
        return JsonResponse({'error': 'No conversations found'}, status=404)
    data = []
    for conv in conversations:
        messages = conv.messages.order_by('timestamp')
        messages_data = [{'sender': msg.sender, 'text': msg.text, 'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')} for msg in messages]
        data.append({
            'conversation_id': conv.id,
            'created_at': conv.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'messages': messages_data
        })
    response = JsonResponse({'conversations': data})
    response['Content-Disposition'] = 'attachment; filename="conversations.json"'
    return response

@login_required
def generate_image(request):
    """
    Generates an image based on a user-provided prompt.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: URL of the generated image or error message.
    """
    credits = Credits.objects.get(user=request.user)
    if credits.credits < 5:
        return JsonResponse({'error': 'You need to have atleast 5 credits.'}, status=400)
    else:
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                prompt = data.get('prompt')
                conversation_id = data.get('conversation_id')

                if not prompt:
                    return JsonResponse({'error': 'Prompt cannot be empty'}, status=400)

                if conversation_id and conversation_id != 'null':
                    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
                else:
                    conversation = Conversation.objects.create(user=request.user)

                Message.objects.create(conversation=conversation, sender='user', text=prompt)
                image = generate_image_from_prompt(prompt)

                if image:
                    unique_filename = f"generated_{uuid.uuid4().hex}.png"
                    image_content = ContentFile(image, unique_filename)
                    bot_message = Message.objects.create(conversation=conversation, sender='bot')
                    bot_message.image.save(unique_filename, image_content)
                    credits.credits -= 5
                    credits.save()
                    return JsonResponse({'image_url': bot_message.image.url, 'conversation_id': conversation.id})
                else:
                    return JsonResponse({'error': 'Failed to generate image.'}, status=500)

            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        return JsonResponse({'error': 'Invalid request'}, status=400)

def public_conversation_view(request, uuid):
    """
    Displays a public view of a conversation based on its UUID.

    Args:
        request (HttpRequest): The HTTP request object.
        uuid (str): The UUID of the conversation.

    Returns:
        HttpResponse: Rendered public conversation page.
    """
    conversation = get_object_or_404(Conversation, uuid=uuid)
    messages = conversation.messages.order_by('timestamp')
    messages_data = [
        {
            'sender': msg.sender,
            'text': msg.text,
            'image_url': msg.image.url if msg.image else None,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        } for msg in messages
    ]
    return render(request, 'public_conversation.html', {'messages': messages_data})

def register(request):
    """
    Handles user registration.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: Redirects to chat on success or renders registration form.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'redirect_url': reverse('chat')})
            return redirect('chat')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = form.errors.as_json()
                return JsonResponse({'status': 'error', 'message': 'Registration failed. Please check your input.', 'errors': errors})
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

def custom_login(request):
    """
    Handles user login with a custom authentication form.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: Redirects to chat on success or renders login form.
    """
    if request.user.is_authenticated:
        return redirect('chat')

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'redirect_url': reverse('chat')})
            return redirect('chat')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Invalid username or password.'})
    else:
        form = CustomAuthenticationForm(request)

    return render(request, 'login.html', {'form': form})

@require_GET
@login_required
def get_prompts(request):
    """
    Retrieve all useful prompts from the database and return them as a JSON response.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: A JSON object containing a list of prompts with their id, name, content, and explanation.
    """
    prompts = Prompt.objects.all().values('id', 'name', 'content', 'explanation')
    prompts_list = list(prompts)
    return JsonResponse({'prompts': prompts_list})



@login_required
def profile_view(request):
    """
    Handles user profile actions such as changing password, managing 2FA, and updating backend API choice.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse or JsonResponse: Renders profile page or returns JSON responses for AJAX requests.
    """
    profile = request.user.profile
    qr_code_base64 = None
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        otp_form = OTPEnableForm()
        backend_api_form = BackendAPIChoiceForm(instance=profile)
        if 'change_password' in request.POST:
            form = CustomPasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password was successfully updated!')
                return redirect('profile')
            else:
                messages.error(request, 'Please correct the errors below.')
            otp_form = OTPEnableForm()
        elif 'update_backend_api' in request.POST:


            backend_api_form = BackendAPIChoiceForm(request.POST, instance=profile)
            if backend_api_form.is_valid():
                backend_api_form.save()
                messages.success(request, 'Backend API updated successfully.')
                return redirect('profile')
                 
        elif 'enable_2fa' in request.POST:
            profile.generate_otp_secret_key()
            totp = pyotp.TOTP(profile.otp_secret_key)
            otp_auth_url = totp.provisioning_uri(name=request.user.username, issuer_name="DjangoAI")
            qr = qrcode.make(otp_auth_url)
            buffered = BytesIO()
            qr.save(buffered, format="PNG")
            qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            return JsonResponse({'status': 'qr_generated', 'qr_code_base64': qr_code_base64})
        elif 'confirm_enable_2fa' in request.POST:
            otp_form = OTPEnableForm(request.POST)
            if otp_form.is_valid():
                otp_token = otp_form.cleaned_data.get('otp_token')
                totp = pyotp.TOTP(profile.otp_secret_key)
                if totp.verify(otp_token):
                    profile.otp_enabled = True
                    profile.save()
                    messages.success(request, 'Two-Factor Authentication has been enabled.')
                    return JsonResponse({'status': 'success'})
                else:
                    return JsonResponse({'status': 'error', 'message': 'Invalid OTP code.'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid form data.'})
        elif 'disable_2fa' in request.POST:
            return JsonResponse({'status': 'disable_2fa_prompt'})
        elif 'confirm_disable_2fa' in request.POST:
            otp_form = OTPEnableForm(request.POST)
            if otp_form.is_valid():
                otp_token = otp_form.cleaned_data.get('otp_token')
                totp = pyotp.TOTP(profile.otp_secret_key)
                if totp.verify(otp_token):
                    profile.otp_enabled = False
                    profile.otp_secret_key = ''
                    profile.save()
                    messages.success(request, 'Two-Factor Authentication has been disabled.')
                    return JsonResponse({'status': 'success'})
                else:
                    return JsonResponse({'status': 'error', 'message': 'Invalid OTP code.'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid form data.'})
    else:
        form = CustomPasswordChangeForm(request.user)
        otp_form = OTPEnableForm()
        backend_api_form = BackendAPIChoiceForm(instance=profile)
    return render(request, 'profile.html', {'form': form,'otp_form': otp_form,'profile': profile,'backend_api_form': backend_api_form,})

@rate_limit("export_all_conversations", limit=2, period=15)
@login_required
def regenerate_response(request):
    """
    Regenerates the last assistant response in a conversation.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: Contains the new assistant's response.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            conversation_id = data.get('conversation_id')
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
            last_bot_message = conversation.messages.filter(sender='bot').last()
            if last_bot_message:
                last_bot_message.delete()
            last_user_message = conversation.messages.filter(sender='user').last()
            if not last_user_message:
                return JsonResponse({'error': 'No user message found to regenerate from'}, status=400)
            credits = Credits.objects.get(user=request.user)
            if credits.credits <= 0:
                return JsonResponse({'error': 'You have no credits left. Please buy more credits to continue.'}, status=400)

            backend_api = request.user.profile.backend_api_choice
            response_text = send_to_backend(conversation, credits, backend_api)
            new_bot_message = Message.objects.create(conversation=conversation, sender='bot', text=response_text)
            return JsonResponse({
                'response': response_text,
                'message_id': new_bot_message.id,
                'reaction_counts': new_bot_message.reaction_counts,
                'user_reaction': None
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@rate_limit("toggle_reaction", limit=10, period=15)
@login_required
def toggle_reaction(request):
    """
    Toggle a reaction (thumbs up/down) on an assistant message

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: Contains the updated reaction counts.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message_id = data.get('message_id')
            reaction_type = data.get('reaction')
            if reaction_type not in ['up', 'down']:
                return JsonResponse({'error': 'Invalid reaction type'}, status=400)
            message = get_object_or_404(Message, id=message_id)
            
            if message.sender != 'bot':
                return JsonResponse({'error': 'Can only react to assistant messages'}, status=400)       
            existing_reaction = MessageReaction.objects.filter(
                message=message,
                user=request.user
            ).first()
            
            if existing_reaction:
                if existing_reaction.reaction == reaction_type:
                    existing_reaction.delete()
                else:
                    existing_reaction.reaction = reaction_type
                    existing_reaction.save()
            else:
                MessageReaction.objects.create(
                    message=message,
                    user=request.user,
                    reaction=reaction_type
                )
            return JsonResponse({
                'reaction_counts': message.reaction_counts,
                'status': 'success'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def search_conversations(request):
    """
    Search through user's conversations and messages.
    Returns conversations that match the search query in messages or summary.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: Contains the search result conversations.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})
    
    conversations = Conversation.objects.filter(
        user=request.user
    ).filter(
        Q(messages__text__icontains=query) | Q(summary__icontains=query)      
    ).distinct()
    
    results = []
    for conv in conversations:
        matching_messages = conv.messages.filter(
            text__icontains=query
        ).order_by('timestamp')[:3]
        
        results.append({
            'id': conv.id,
            'summary': conv.summary or 'No summary available',
            'created_at': conv.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'matching_messages': [
                {
                    'text': msg.text,
                    'sender': msg.sender,
                    'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
                for msg in matching_messages
            ]
        })
    
    return JsonResponse({'results': results})

@login_required
def get_message_id(request):
    """
    Get the ID of the last assistant message in a conversation.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: Contains the message ID or an error message.
    """
    conversation_id = request.GET.get('conversation_id')
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    last_bot_message = conversation.messages.filter(sender='bot').last()
    if last_bot_message:
        return JsonResponse({'message_id': last_bot_message.id})
    else:
        return JsonResponse({'error': 'No bot message found'}, status=404)