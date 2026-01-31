---
layout: default
title: Configuration
parent: Installation
nav_order: 3
---

# Configuration

PuzzleSpring offers two types of configuration: environment variables that must be set before startup, and in-app settings that can be changed at runtime through the admin interface.

## Environment Variables

Environment variables are configuration options that must be set before starting the application. These settings are typically defined in a `.env` file in the root directory of the project.

Environment variables can be set in multiple ways, including directly in your system environment or in your deployment configuration. The `.env` file is a convenient way to manage these variables, especially when using Docker Compose, as it automatically loads these variables into your containers.

{: .note }
> Any changes to environment variables require an application restart to take effect.

### Setting Environment Variables using `.env`

1. Copy the `sample.env` file to `.env`
2. Modify the values in `.env` according to your needs
3. Restart the application for changes to take effect

{: .warning }
> Never commit your `.env` file to version control - it should remain private and specific to your deployment.

### Available Environment Variables

#### Database Configuration

- `DB_PASSWORD`: The password for the PostgreSQL database connection. Choose a secure password that doesn't contain special characters that might interfere with connection strings. This doesn't need to be an existing password if starting fresh, first time setup will use this password when creating database accounts.

    Required: Yes | Type: String | Example: "my_password"

{: .note }
> Avoid using these characters in your database password: colon (`:`), at symbol (`@`), forward slash (`/`), percent sign (`%`), backslash (`\`), and quotation marks (`"` and `'`). These characters can cause connection string parsing issues.

- `DATABASE_URL`: The complete database connection URL. If not specified, it will be constructed automatically using the `DB_PASSWORD` value in the format `postgres://puzzlehunt:${DB_PASSWORD}@db/puzzlehunt`.

    Required: No | Type: String | Example: "postgres://puzzlehunt:password@db/puzzlehunt"

#### Security Settings

- `DJANGO_SECRET_KEY`: A long, random string used by Django for cryptographic signing. This should be kept secret and unique for each installation.

    Required: Yes | Type: String | Example: "mysecretkey"

{: .note }
> To generate a secure Django secret key, you can use Python:
>
> ```python
> python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
> ```
>
> Copy the output into your `.env` file as the `DJANGO_SECRET_KEY` value.


- `DJANGO_ENABLE_DEBUG`: Enables Django's debug mode. Should be set to `False` in production environments.

    Required: No | Default: False | Type: Boolean

- `ENABLE_DEBUG_TOOLBAR`: Enables Django Debug Toolbar for development.

    Required: No | Default: False | Type: Boolean

- `ENFORCE_SSL`: Forces HTTPS connections when enabled.

    Required: No | Default: False | Type: Boolean

{: .warning }
> Never enable debug mode in production

#### Server Configuration

- `DOMAIN`: The domain name where the application will be hosted. For local development, use `localhost`.

    Required: Yes | Type: String | Example: "localhost"

- `HTTP_PORT`: The port number for HTTP traffic.

    Required: No | Default: 80 | Type: Integer | Example: 8000

- `HTTPS_PORT`: The port number for HTTPS traffic.

    Required: No | Default: 443 | Type: Integer | Example: 8443

#### Performance and Caching

- `ENABLE_REDIS_CACHE`: Enables Redis caching functionality.

    Required: No | Default: True | Type: Boolean

- `ENABLE_MIGRATION_MANAGEMENT`: Controls whether database migrations are managed automatically.

    Required: No | Default: True | Type: Boolean

#### Monitoring

- `SENTRY_DSN`: The Data Source Name for Sentry error tracking.

    Required: No | Type: String | Example: "https://some_long_hex_string@sentry.io/some_number"

---

## In-App Settings

PuzzleSpring uses Django Constance for managing in-app settings. These are configuration options that can be modified directly through the Django admin interface without requiring code changes or server restarts.

### Modifying Settings

To access and modify these settings:

1. Log in to the Django admin interface
2. Navigate to "Constance » Config"
3. Modify the desired settings
4. Click "Save" to apply changes

### Available In-App Settings

#### Site Settings

- `SITE_TITLE`: The title of the site

    Default: "PuzzleSpring" | Type: String

#### Team Settings

- `TEAM_CUSTOM_DATA_NAME`: The name of the team custom data field

    Default: "" | Type: String

- `TEAM_CUSTOM_DATA_DESCRIPTION`: The description of the team custom data field

    Default: "" | Type: String

#### Hunt Display Settings

- `SINGLE_HUNT_MODE`: If enabled, only one hunt will be visible and accessible

    Default: False | Type: Boolean

    Note: This feature is not yet implemented.

#### Puzzle Display Settings

- `PROGRESS_FULL_PUZZLE_NAMES`: If enabled, the progress page will show full puzzle names

    Default: False | Type: Boolean

- `SHOW_SOLVE_COUNT_ON_PUZZLE`: If enabled, the puzzle page will show the current number of solves

    Default: True | Type: Boolean

- `SHOW_UPDATE_FOR_LOCKED_PUZZLES`: If enabled, updates will be shown even when the puzzle is locked

    Default: True | Type: Boolean

#### Communication Settings

- `CONTACT_EMAIL`: The contact email for help links

    Default: "test@test.com" | Type: String

#### Submission and Hint Settings

- `SHOW_SUBMISSION_USER`: If enabled, the submissions page will display usernames

    Default: True | Type: Boolean

- `SHOW_HINT_USER_STAFF`: If enabled, the staff hints page will show the staff responder

    Default: True | Type: Boolean

#### Image Settings

- `NAVBAR_IMAGE`: The image displayed on the navbar

    Default: "" | Type: Image Field

- `EMBED_IMAGE`: The image displayed in embeds

    Default: "" | Type: Image Field

- `FAVICON`: The image displayed in the browser tab

    Default: "" | Type: Image Field

---

## External Authentication

PuzzleSpring supports various external authentication providers through Django Allauth, allowing users to log in using their existing accounts from services like Google, GitHub, or Facebook.

### Enabling External Authentication Providers

1. Navigate to the Django Admin interface at `/admin/`
2. Go to "Social applications" under Social Accounts
3. Click "Add social application"
4. Select the provider you want to enable (e.g., Google, GitHub)
5. Enter the required credentials:
   - **Name**: A name for this authentication provider
   - **Client ID**: The client ID from your provider's developer console
   - **Secret key**: The secret key from your provider's developer console
   - **Key**: Additional key if required by the provider
6. In the "Sites" section, move your site from "Available sites" to "Chosen sites"
7. Click "Save"

### Provider-Specific Setup

Each provider requires specific setup in their developer console:

- **Google**: Create OAuth credentials in the Google Cloud Console
- **GitHub**: Register a new OAuth application in GitHub Developer Settings
- **Facebook**: Create a new app in the Facebook Developer Portal

For all providers, you'll need to configure the redirect URI as:
`https://your-domain.com/accounts/provider/login/callback/`
(Replace "provider" with the specific provider name like "google" or "github")
