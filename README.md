# Django AI Chat Application

A robust and feature-rich Django-based chat application that integrates multiple AI backends, including Nebius AI, Oobabooga (local), and Stable Diffusion for image generation. The application offers user authentication with two-factor authentication (2FA), a comprehensive credit system for managing API usage, conversation management, and secure sharing of public conversations.

## 📋 Table of Contents

- [🌟 Features](#-features)
- [🚀 Installation](#-installation)
- [⚙️ Configuration](#️-configuration)
- [🎮 Initial Setup Through Admin Panel](#-initial-setup-through-admin-panel)
- [🏃‍♂️ Running the Application](#-running-the-application)
- [💰 Credit System](#-credit-system)
- [🔐 Security Features](#-security-features)
- [🔄 API Backend Selection](#-api-backend-selection)
- [📸 Image Generation](#-image-generation)
- [💾 Data Export](#-data-export)
- [⚠️ Important Notes](#-important-notes)
- [🔧 Troubleshooting](#-troubleshooting)
- [📝 Contributing](#-contributing)
- [📄 License](#-license)
- [📞 Contact](#-contact)

## 🌟 Features

- **Multi-Backend AI Chat Support**: Seamlessly switch between Nebius AI (cloud-based) and Oobabooga (local) for text generation.
- **Image Generation**: Create stunning images using Stable Diffusion WebUI integrated within the application.
- **User Authentication**: Secure login and registration with optional Two-Factor Authentication (2FA).
- **Credit System**: Manage API usage with a credit-based system, providing users with initial credits and tracking usage.
- **Conversation Management**: Create, delete, export, and share conversations publicly with unique UUIDs.
- **Public Conversation Sharing**: Share conversations via public links for broader accessibility.
- **Character and Model Selection**: Choose specific characters for Oobabooga and models for Nebius AI to tailor the chat experience.
- **Real-Time API Status Monitoring**: Monitor the status of integrated APIs (Oobabooga and Stable Diffusion) in real-time.
- **Responsive Design**: User-friendly interface based on Tailwind CSS.

## 🚀 Installation

Follow these steps to set up the Django AI Chat Application on your local machine.

### 1. Clone the Repository and Create a Virtual Environment

```bash
git clone https://github.com/zimNMM/django-ai-chat.git
cd django-ai-chat
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

### 2. Install the Required Packages

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

It's crucial to keep your API keys and sensitive information secure. Create a .env with the followings or edit the .env.example and rename it to .env

```env
# API Keys
OPENAI_API_KEY=your_openai_api_key
NEBIUS_API_KEY=your_nebius_api_key

# Local API URLs
OOBABOOGA_URL=http://127.0.0.1:5000/v1/chat/completions
STABLEDIFFUSION_URL=http://127.0.0.1:7860/sdapi/v1/txt2img
```

**Note**: Never commit the `.env` file to version control. Add `.env` to your `.gitignore` file.

### 4. Apply Migrations

```bash
python manage.py makemigrations chat
python manage.py migrate
```

### 5. Create a Superuser Account

```bash
python manage.py createsuperuser
```

Follow the prompts to set up your superuser credentials.

## ⚙️ Configuration

### 1. Configure Settings

Ensure that your `settings.py` is configured to for 127.0.0.1 if you run it through cloudflared tunnel make sure to edit those settings!

```python


CSRF_TRUSTED_ORIGINS = ['https://yoururl.com', 'https://www.yoururl.com']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

ALLOWED_HOSTS = ["127.0.0.1","yoururl.com","www.yoururl.com"]

```

### 2. Static and Media Files

Ensure that static and media directories exist like in the code bellow:

```python
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

## 🎮 Initial Setup Through Admin Panel

After setting up the application, perform the following initial configurations via the Django admin panel.

### 1. Access the Admin Panel

Navigate to `http://127.0.0.1:8000/admin` and log in with your superuser credentials.

### 2. Add Nebius AI Models

- **Navigate**: Click on **Nebius Models**.
- **Action**: Click **Add Nebius Model**.
- **Name**: Enter the model name, e.g., `meta-llama/Meta-Llama-3.1-70B-Instruct`.
- **Save**: Click **Save** to add the model.

### 3. Add Oobabooga Characters

- **Navigate**: Click on **Oobabooga Characters**.
- **Action**: Click **Add Oobabooga Character**.
- **Name**: Enter the name of the character as defined in your OobaboogaUI.
- **Save**: Click **Save** to add the character.

### 4. Add Useful Prompts

- **Navigate**: Click on **Prompts**.
- **Action**: Click **Add Prompt**.
- **Name**: Provide a name for prompt.
- **Content**: Provide the content (the text copied to the clipboard).
- **Explanation**: Brief explanation of what the prompt does.
- **Save**: Click **Save** to add the prompt.

### 5. Manage Users and Credits

- **Credits**: The system automatically assigns 500 credits to new users upon registration. You can manage user credits via the **Credits** section in the admin panel.

## 🏃‍♂️ Running the Application

### 1. Start Local Services

Ensure that the required local services are running before starting the Django application.

- **Oobabooga Text Generation WebUI**:

  ```bash
  ./start_linux.sh --api
  ```

- **Stable Diffusion WebUI**:

  ```bash
  ./webui.sh --api 
  ```

### 2. Run the Django Development Server

Activate your virtual environment if not already active:

```bash
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

Start the server:

```bash
python manage.py runserver
```

### 3. Access the Application

Open your browser and navigate to `http://127.0.0.1:8000` to access the chat application.

## 💰 Credit System

Manage your API usage efficiently with our built-in credit system.

- **Initial Credits**: New users receive **500 credits** upon registration.
- **Usage Costs**:
  - **Text Completions**: **1 credit** per request.
  - **Image Generations**: **5 credits** per image.
- **Admin Management**: Administrators can adjust user credits via the **Credits** section in the admin panel.

## 🔐 Security Features

Ensure the safety and integrity of user data with comprehensive security measures.

- **Two-Factor Authentication (2FA)**: Optional 2FA for enhanced account security.
- **Password Management**: Secure password change functionality.
- **Session Management**: Manage user sessions securely to prevent unauthorized access.
- **Secure Conversation Sharing**: Public conversations are shared via unique UUIDs, ensuring privacy and security.

## 🔄 API Backend Selection

Customize your chat experience by selecting your preferred AI backend.

- **Nebius AI**: Cloud-based AI for robust text generation.
- **Oobabooga**: Local AI text generation for those preferring on-premises solutions.

### Switching Between Backends

Users can switch between Nebius AI and Oobabooga in their profile settings, allowing flexibility based on their needs and preferences.

## 📸 Image Generation

Create visual content effortlessly with integrated image generation capabilities.

- **Stable Diffusion WebUI Integration**: Generate images based on user-provided prompts.
- **Credit-Based Usage**: Image generation consumes credits, ensuring controlled usage.

## 💾 Data Export

Easily export and share your conversations.

- **Export as JSON**: Download all your conversations in JSON format for backup or analysis.
- **Public Links**: Share conversations via unique public links, making them accessible to others without compromising security.

## ⚠️ Important Notes

- **Local Services**: Ensure that all local services (Oobabooga Text Generation WebUI and Stable Diffusion WebUI) are running on the specified ports before starting the Django application.
- **API Keys Security**: Keep your API keys secure. Never commit them to version control.
- **Database Backups**: Regularly back up your database to prevent data loss.

## 🔧 Troubleshooting

Encountering issues? Here are some common problems and their solutions:

- **API Status Shows 'Offline'**:
  - **Cause**: Local services like Oobabooga or Stable Diffusion are not running.
  - **Solution**: Start the respective services and ensure they are running on the correct ports.

- **Credit Issues**:
  - **Cause**: Users might have exhausted their credits or credits aren't updating correctly.
  - **Solution**: Verify the user's credit balance in the admin panel. Adjust if necessary.

- **2FA Problems**:
  - **Cause**: Users unable to authenticate due to 2FA issues.
  - **Solution**: Administrators can disable 2FA for the affected user via the admin panel.

- **Image Generation Errors**:
  - **Cause**: Misconfiguration of the Stable Diffusion WebUI or insufficient credits.
  - **Solution**: Check the configuration of the Stable Diffusion WebUI and ensure the user has enough credits.

- **General Errors**:
  - **Solution**: Check the Django server logs for detailed error messages and address accordingly.

## 📝 Contributing

We welcome contributions to enhance the Django AI Chat Application! Whether it's bug fixes, feature enhancements, or documentation improvements, your input is valuable.

## 📄 License

This project is licensed under the [MIT License](LICENSE). You are free to use, modify, and distribute this software under the terms of the license.

## 📞 Contact

For any questions, suggestions, or support, feel free to reach out:

- **GitHub Issues**: [Open an Issue](https://github.com/zimNMM/django-ai-chat/issues)


---
