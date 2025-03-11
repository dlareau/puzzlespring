---
layout: default
title: Environment Variables
parent: Configuration
nav_order: 2
---

# Environment Variables

Environment variables are configuration options that must be set before starting the application. These settings are typically defined in a `.env` file in the root directory of the project.

Environment variables can be set in multiple ways, including directly in your system environment or in your deployment configuration. The `.env` file is a convenient way to manage these variables, especially when using Docker Compose, as it automatically loads these variables into your containers. However, you're free to use whatever method of setting environment variables works best for your deployment setup.

{: .note }
> Any changes to environment variables require an application restart to take effect.

## Setting Environment Variables using `.env`

1. Copy the `sample.env` file to `.env`
2. Modify the values in `.env` according to your needs
3. Restart the application for changes to take effect

{: .warning }
> Never commit your `.env` file to version control - it should remain private and specific to your deployment.

## Available Variables
### Database Configuration

- `DB_PASSWORD`: The password for the PostgreSQL database connection. Choose a secure password that doesn't contain special characters that might interfere with connection strings. This doesn't need to be an existing password if starting fresh, first time setup will use this password when creating database accounts.

    *Required: Yes • Type: String • Example: "my_password"*

{: .note }
> Avoid using these characters in your database password: colon (`:`), at symbol (`@`), forward slash (`/`), percent sign (`%`), backslash (`\`), and quotation marks (`"` and `'`). These characters can cause connection string parsing issues.

- `DATABASE_URL`: TThe complete database connection URL. If not specified, it will be constructed automatically using the `DB_PASSWORD` value in the format `postgres://puzzlehunt:${DB_PASSWORD}@db/puzzlehunt`.

    *Required: No • Type: String • Example: "postgres://puzzlehunt:password@db/puzzlehunt"*

### Security Settings

- `DJANGO_SECRET_KEY`: A long, random string used by Django for cryptographic signing. This should be kept secret and unique for each installation.

    *Required: Yes • Type: String • Example: "mysecretkey"*

{: .note }
> To generate a secure Django secret key, you can use Python:
>
> ```python
> python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
> ```
>
> Copy the output into your `.env` file as the `DJANGO_SECRET_KEY` value.


- `DJANGO_ENABLE_DEBUG`: Enables Django's debug mode. Should be set to `False` in production environments.

    *Required: No • Default: False • Type: Boolean*

- `ENABLE_DEBUG_TOOLBAR`: Enables Django Debug Toolbar for development.

    *Required: No • Default: False • Type: Boolean*

- `ENFORCE_SSL`: Forces HTTPS connections when enabled.

    *Required: No • Default: False • Type: Boolean*

{: .warning }
> Never enable debug mode in production

### Server Configuration

- `DOMAIN`: The domain name where the application will be hosted. For local development, use `localhost`.

    *Required: Yes • Type: String • Example: "localhost"*

- `HTTP_PORT`: The port number for HTTP traffic.

    *Required: No • Default: 80 • Type: Integer • Example: 8000*

- `HTTPS_PORT`: The port number for HTTPS traffic.

    *Required: No • Default: 443 • Type: Integer • Example: 8443*

### Performance and Caching

- `ENABLE_REDIS_CACHE`: Enables Redis caching functionality.

    *Required: No • Default: True • Type: Boolean*

- `ENABLE_MIGRATION_MANAGEMENT`: Controls whether database migrations are managed automatically.

    *Required: No • Default: True • Type: Boolean*

### Monitoring

- `SENTRY_DSN`: The Data Source Name for Sentry error tracking.

    *Required: No • Type: String • Example: "https://some_long_hex_string@sentry.io/some_number"*