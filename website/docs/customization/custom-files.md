---
layout: default
title: Custom Files
parent: Customization
nav_order: 2
---

# Custom Files

PuzzleSpring is designed to be highly customizable without modifying the core codebase. This section explains how to use the custom directories to override default behavior and add your own functionality.

{: .warning }
> Extensive customizations may make it harder to upgrade to newer versions of PuzzleSpring. Try to keep changes modular and well-documented.

## Custom Directory Structure

PuzzleSpring provides three main directories for customization:

```
custom/
├── config/      # Custom Django settings
├── static/      # Custom static files (CSS, JS, images)
└── templates/   # Custom template overrides
```

These directories are mounted as volumes in the Docker setup, making them persistent and easily accessible.

## Custom Settings

The `custom/config/` directory allows you to override Django settings without modifying the core codebase.

### Creating Custom Settings

1. Create a file at `custom/config/settings.py`
2. Add your custom Django settings
3. Set the `DJANGO_SETTINGS_MODULE` environment variable in your `.env` file to `server.settings.custom_settings`

Example `settings.py`:
```python
# Override email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.example.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@example.com'
EMAIL_HOST_PASSWORD = 'your-password'

# Add additional installed apps
INSTALLED_APPS += [
    'my_custom_app',
]

# Override authentication settings
AUTHENTICATION_BACKENDS = [
    'my_custom_auth_backend',
    'django.contrib.auth.backends.ModelBackend',
]
```

The settings in this file will be loaded after the base settings, allowing you to override any default configuration.

## Custom Templates

The `custom/templates/` directory allows you to override any template in the application without modifying the original files.

### Overriding Templates

1. Identify the template you want to override
2. Create a file with the same path in the `custom/templates/` directory

For example, to override the login page:
```
custom/templates/account/login.html
```

PuzzleSpring will check the custom templates directory first, so your version will take precedence.

### Template Inheritance

You can extend the original templates instead of completely replacing them:

{% raw %}
```html
{% extends "original_template_name.html" %}

{% block content %}
  <!-- Your custom content here -->
  {{ block.super }}  <!-- Include the original block content -->
{% endblock %}
```
{% endraw %}

{: .note }
> The custom templates directory is mounted as a volume, so changes will be reflected without rebuilding the container.

{: .warning }
> When overriding templates, ensure you maintain the expected blocks and context variables. Refer to the [Templates](templates.html) documentation for details.

## Custom Static Files

The `custom/static/` directory allows you to add custom CSS, JavaScript, and images.

### Adding Custom Static Files

1. Place your files in the `custom/static/` directory
2. Reference them in templates using the static template tag

Example:
{% raw %}
```html
{% load static %}
<link rel="stylesheet" href="{% static 'css/custom.css' %}">
<script src="{% static 'js/custom.js' %}"></script>
```
{% endraw %}

### Overriding Default Static Files

To override a default static file, create a file with the same path in the custom static directory.

For example, to override the main CSS file:
```
custom/static/css/main.css
```

{: .note }
> The custom static directory is mounted as a volume, so changes will be reflected without rebuilding the container.

## Common Use Cases

### Custom CSS

Add custom styles by creating `custom/static/css/custom.css` and including it in your templates.

### Logo and Branding

Replace default images by placing your custom images in `custom/static/images/`.

### Template Modifications

Override specific templates to change layout, add features, or modify behavior without changing core files.
