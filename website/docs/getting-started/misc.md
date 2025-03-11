
- Staff and Admin pages

## Staff and Admin Pages

PuzzleSpring provides two different interfaces for managing the application: Staff Pages and the Django Admin interface. Each serves different purposes and offers different levels of control.

### Staff Pages

Staff pages are purpose-built interfaces designed specifically for puzzle hunt management. They're accessible to any user with staff privileges and focus on hunt-specific operations.

#### Accessing Staff Pages

1. Log in with a staff account
2. Navigate to any normal site page
3. Click on the wrench icon in the navigation bar

#### Available Staff Pages

- **Hunts**: Overview of all hunts with creation and management options
- **Search**: Search functionality across teams, users, and puzzles
- **Progress**: Real-time team progress tracking with filtering options
- **Feed**: Activity feed showing submissions, hints, and other events
- **Hints**: Interface for managing and responding to hint requests
- **Charts**: Visual analytics of hunt progress and team performance
- **Hunt Template**: Editor for customizing the hunt's appearance
- **Puzzles**: Interface for managing puzzles and their attributes
- **Hunt Config**: Editor for puzzle unlocking rules and hunt configuration

### Django Admin Interface

The Django Admin interface provides low-level access to the database models and is intended for system administrators and developers. It offers more powerful but less user-friendly controls.

#### Accessing Django Admin

1. Log in with a superuser account
2. Navigate to `/admin/` or click "Django Admin" in the staff sidebar

#### Key Admin Sections

- **Users**: Create, modify, and delete user accounts
- **Teams**: Manage team membership and properties
- **Hunts**: Configure hunt settings and properties
- **Puzzles**: Create and edit puzzles at the database level
- **Submissions**: View and manage all submissions
- **Hints**: Access all hint requests and responses
- **Updates**: Manage hunt announcements and updates
- **Constance Config**: Modify site-wide settings

#### When to Use Django Admin

- Fixing data inconsistencies
- Configuring system-wide settings
- Managing user permissions and roles

{: .warning }
> The Django Admin interface provides direct access to the database. Use with caution, as improper changes can affect system stability.

### Permissions and Access Control

- **Staff Users**: Can access staff pages but not necessarily Django Admin
- **Superusers**: Have full access to both staff pages and Django Admin
- **Regular Users**: Cannot access either interface

To grant staff privileges to a user:
1. Go to Django Admin > Users
2. Select the user
3. Check the "Staff" or "Superuser" status checkbox
4. Save changes

{: .note }
> For day-to-day hunt management, staff pages are recommended over Django Admin due to their specialized interfaces and safety features.






- Using truly custom things like settings, templates, and static files

## Using Custom Settings, Templates, and Static Files

PuzzleSpring is designed to be highly customizable without modifying the core codebase. This section explains how to use the custom directories to override default behavior and add your own functionality.

{: .warning }
> Extensive customizations may make it harder to upgrade to newer versions of PuzzleSpring. Try to keep changes modular and well-documented.

### Custom Directory Structure

PuzzleSpring provides three main directories for customization:

```
custom/
├── config/      # Custom Django settings
├── static/      # Custom static files (CSS, JS, images)
└── templates/   # Custom template overrides
```

These directories are mounted as volumes in the Docker setup, making them persistent and easily accessible.

### Custom Settings

The `custom/config/` directory allows you to override Django settings without modifying the core codebase.

#### Creating Custom Settings

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

### Custom Templates

The `custom/templates/` directory allows you to override any template in the application without modifying the original files.

#### Overriding Templates

1. Identify the template you want to override
2. Create a file with the same path in the `custom/templates/` directory

For example, to override the login page:
```
custom/templates/account/login.html
```

PuzzleSpring will check the custom templates directory first, so your version will take precedence.

#### Template Inheritance

You can extend the original templates instead of completely replacing them:

```html
{% extends "original_template_name.html" %}

{% block content %}
  <!-- Your custom content here -->
  {{ block.super }}  <!-- Include the original block content -->
{% endblock %}
```

### Custom Static Files

The `custom/static/` directory allows you to add custom CSS, JavaScript, and images.

#### Adding Custom Static Files

1. Place your files in the `custom/static/` directory
2. Reference them in templates using the static template tag

Example:
```html
{% load static %}
<link rel="stylesheet" href="{% static 'css/custom.css' %}">
<script src="{% static 'js/custom.js' %}"></script>
```

#### Overriding Default Static Files

To override a default static file, create a file with the same path in the custom static directory.

For example, to override the main CSS file:
```
custom/static/css/main.css
```






-hunt info page

## Hunt Info Page

The Hunt Info Page is a special page that provides information about a specific hunt. It's typically used for hunt rules, FAQ, and other hunt-specific information.

### Setting Up the Hunt Info Page

1. Go to Django Admin > Hunts
2. Select the hunt you want to edit
3. Scroll down to the "Info Page File" field
4. Upload an HTML template file with your hunt information
5. Save the hunt

### Hunt Info Page Template

The Hunt Info Page is a Django template with access to the hunt in the context. This means you can use dynamic content based on the current hunt:

```html
<h1>{{ hunt.name }} - Information</h1>

<h2>Hunt Schedule</h2>
<p>Start: {{ hunt.start_date|date:"F j, Y, g:i a" }}</p>
<p>End: {{ hunt.end_date|date:"F j, Y, g:i a" }}</p>

<h2>Rules</h2>
<ul>
  <li>Teams can have up to {{ hunt.max_team_size }} members</li>
  <li>Each team starts with {{ hunt.initial_hints }} hints</li>
  <!-- More rules here -->
</ul>

<h2>Contact</h2>
<p>If you have questions during the hunt, please email <a href="mailto:{% contact_email %}">{% contact_email %}</a>.</p>
```

### Accessing the Hunt Info Page

The Hunt Info Page is accessible from:
- The main navigation bar ("Hunt Info" link)
- The hunt homepage
- Direct URL: `/hunt/[hunt-id]/info/`

{: .note }
> The Hunt Info Page is often one of the first pages participants will visit. Make sure it provides clear instructions on how to participate in your hunt.