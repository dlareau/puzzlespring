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

- `DB_PASSWORD`: The password for the database connection

    *Required: Yes • Type: String • Example: "my_password"*

- `DATABASE_URL`: The database connection URL. If not set, it will be constructed using the DB_PASSWORD

    *Required: No • Type: String • Example: "postgres://puzzlehunt:password@db/puzzlehunt"*

### Security Settings

- `DJANGO_SECRET_KEY`: Django's secret key used for cryptographic signing

    *Required: Yes • Type: String • Example: "mysecretkey"*

- `DJANGO_ENABLE_DEBUG`: Enables Django's debug mode

    *Required: No • Default: False • Type: Boolean*

- `ENABLE_DEBUG_TOOLBAR`: Enables Django Debug Toolbar for development

    *Required: No • Default: False • Type: Boolean*

- `ENFORCE_SSL`: Forces HTTPS connections when enabled

    *Required: No • Default: False • Type: Boolean*

{: .warning }
> Never enable debug mode in production

### Server Configuration

- `DOMAIN`: The domain name where the application will be hosted

    *Required: Yes • Type: String • Example: "localhost"*

- `HTTP_PORT`: The port number for HTTP traffic

    *Required: No • Default: 80 • Type: Integer • Example: 8000*

- `HTTPS_PORT`: The port number for HTTPS traffic

    *Required: No • Default: 443 • Type: Integer • Example: 8443*

### Performance and Caching

- `ENABLE_REDIS_CACHE`: Enables Redis caching functionality

    *Required: No • Default: True • Type: Boolean*

- `ENABLE_MIGRATION_MANAGEMENT`: Controls whether database migrations are managed automatically

    *Required: No • Default: True • Type: Boolean*

### Monitoring

- `SENTRY_DSN`: The Data Source Name for Sentry error tracking

    *Required: No • Type: String • Example: "https://some_long_hex_string@sentry.io/some_number"*