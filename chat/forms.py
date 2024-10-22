# chat/forms.py

from django import forms
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm
from django.contrib.auth import authenticate

from .models import Profile, NebiusModel, OobaboogaCharacter, OllamaModel

import pyotp


class BackendAPIChoiceForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['backend_api_choice', 'selected_model', 'selected_character', 'selected_ollama_model']
        widgets = {
            'backend_api_choice': forms.Select(attrs={
                'class': 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:ring focus:ring-blue-500',
            }),
            'selected_model': forms.Select(attrs={
                'class': 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:ring focus:ring-blue-500',
            }),
            'selected_character': forms.Select(attrs={
                'class': 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:ring focus:ring-blue-500',
            }),
            'selected_ollama_model': forms.Select(attrs={
                'class': 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:ring focus:ring-blue-500',
            }),
        }

    def __init__(self, *args, **kwargs):
        super(BackendAPIChoiceForm, self).__init__(*args, **kwargs)
        backend_api = self.instance.backend_api_choice or self.initial.get('backend_api_choice')
        if backend_api == 'nebius':
            self.fields['selected_model'].queryset = NebiusModel.objects.all()
            self.fields['selected_model'].required = True
            self.fields['selected_character'].widget = forms.HiddenInput()
            self.fields['selected_ollama_model'].widget = forms.HiddenInput()
        elif backend_api == 'oobabooga':
            self.fields['selected_character'].queryset = OobaboogaCharacter.objects.all()
            self.fields['selected_character'].required = True
            self.fields['selected_model'].widget = forms.HiddenInput()
            self.fields['selected_ollama_model'].widget = forms.HiddenInput()
        elif backend_api == 'ollama':
            self.fields['selected_ollama_model'].queryset = OllamaModel.objects.all()
            self.fields['selected_ollama_model'].required = True
            self.fields['selected_model'].widget = forms.HiddenInput()
            self.fields['selected_character'].widget = forms.HiddenInput()
        else:
            self.fields['selected_model'].widget = forms.HiddenInput()
            self.fields['selected_character'].widget = forms.HiddenInput()
            self.fields['selected_ollama_model'].widget = forms.HiddenInput()

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Old Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:ring focus:ring-blue-500',
            'placeholder': 'Enter your current password',
        })
    )
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:ring focus:ring-blue-500',
            'placeholder': 'Enter your new password',
        })
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:ring focus:ring-blue-500',
            'placeholder': 'Confirm your new password',
        })
    )

class OTPEnableForm(forms.Form):
    otp_token = forms.CharField(
        required=True,
        label="OTP Code",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:ring focus:ring-blue-500',
            'placeholder': 'Enter the OTP code',
        })
    )

class CustomAuthenticationForm(AuthenticationForm):
    otp_token = forms.CharField(
        required=False,
        label="OTP Code",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:ring focus:ring-indigo-500 text-white',
            'placeholder': 'Enter your OTP code',
        })
    )

    def __init__(self, request=None, *args, **kwargs):
        super(CustomAuthenticationForm, self).__init__(request, *args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        otp_token = cleaned_data.get('otp_token')

        if username and password:
            user = authenticate(self.request, username=username, password=password)
            if user is not None:
                profile = user.profile
                if profile.otp_enabled:
                    if not otp_token:
                        raise forms.ValidationError('This account requires an OTP code.')
                    totp = pyotp.TOTP(profile.otp_secret_key)
                    if not totp.verify(otp_token):
                        raise forms.ValidationError('Invalid OTP code.')
            else:
                raise forms.ValidationError('Invalid username or password.')
        return cleaned_data