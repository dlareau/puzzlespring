---
layout: default
title: Production Deployment
parent: Installation
nav_order: 2
---

# Production Deployment

This guide provides detailed instructions for deploying PuzzleSpring in a production environment.

## Prerequisites

- Docker Engine (version 20.10.0 or higher)
- Docker Compose (version 2.0.0 or higher)
- Git
- A domain name pointed to your server

## Basic Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/dlareau/puzzlespring.git
   cd puzzlespring
   ```

2. Copy the sample environment file:
   ```bash
   cp sample.env .env
   ```

3. Configure your environment variables in `.env`. At minimum, you need to set:
   - `DJANGO_SECRET_KEY`: A secure random string
   - `DB_PASSWORD`: Password for the PostgreSQL database
   - `DOMAIN`: Your domain name (use `localhost` for development)

{: .note }
> To generate a secure Django secret key, you can use Python:
>
> ```python
> python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
> ```
>
> Copy the output into your `.env` file as the `DJANGO_SECRET_KEY` value.

## Production Deployment Steps

1. Configure your domain:
   - Set `DOMAIN` in `.env` to your actual domain name (e.g., `puzzles.example.com`)
   - Remove any port number from the domain to enable automatic SSL

{: .warning }
> Ensure you've set secure values for `DJANGO_SECRET_KEY` and `DB_PASSWORD`, and that `DJANGO_ENABLE_DEBUG=False`

2. Start the application:
   ```bash
   docker compose up -d
   ```

3. Run the initial setup:
   ```bash
   docker compose exec app python manage.py initial_setup
   ```

4. Access your site at `https://your-domain.com`

{: .note }
> The Caddy server will automatically obtain and manage SSL certificates for your domain.

## Post-Installation

After installation, you should:

1. Log in to the admin interface at `/admin` using your superuser account

2. Configure [In-App Settings](configuration.html#in-app-settings) through the admin interface

3. Create your first hunt or import an existing hunt template

## Customizing Static Files

To override or add custom static files:

1. Create a `custom/static` directory in your project root
2. Place your custom static files in this directory
3. Restart the containers to apply changes:
   ```bash
   docker compose restart app
   ```

{: .note }
> The custom static directory is mounted as a volume, so changes will be reflected without rebuilding the container.

## Customizing Templates

To override or customize templates:

1. Create a `custom/templates` directory in your project root
2. Mirror the template structure you want to override. For example:
   ```
   custom/templates/
   └── puzzlehunt/
       └── puzzle_base.html
   ```
3. Files in this directory will take precedence over the default templates
4. Restart the containers to apply changes:
   ```bash
   docker compose restart app
   ```

{: .note }
> The custom templates directory is mounted as a volume, so changes will be reflected without rebuilding the container.

{: .warning }
> When overriding templates, ensure you maintain the expected blocks and context variables. Refer to the [Templates](../customization/templates.html) documentation for details.

## Troubleshooting

### Common Issues

1. **SSL Certificate Issues**
   - Ensure your domain is pointed to your server
   - Check that ports 80 and 443 are accessible
   - Verify `DOMAIN` doesn't include a port number

2. **Static Files Missing**
   - Run `docker compose exec app python manage.py collectstatic`

### Checking Logs

To view logs for any service:

```bash
docker compose logs [service_name]
```

Available services:
- `app`: Main application
- `db`: Database
- `caddy`: Web server
- `redis`: Cache
- `pushpin`: Real-time updates
- `huey`: Background tasks

## Reset the Database

There are several methods to reset or reinitialize the database in PuzzleSpring, depending on your specific needs.

### Method 1: Using Django Management Commands

The simplest way to reset the database is using Django's built-in management commands:

```bash
# Connect to the app container
docker compose exec app bash

# Flush all data while preserving tables
python manage.py flush

# Or, to completely reset and recreate all tables
python manage.py migrate --fake zero
python manage.py migrate
```

### Method 2: Hunt-Specific Reset

If you only need to reset a specific hunt without affecting the entire database:

```bash
# Connect to the app container
docker compose exec app bash

# Access the Django shell
python manage.py shell

# Reset a specific hunt
from puzzlehunt.models import Hunt
hunt = Hunt.objects.get(id=<hunt_id>)
hunt.reset()
```

The `hunt.reset()` method will clear all team progress, submissions, hints, and other hunt-related data while preserving the hunt configuration and puzzles.

### Method 3: Database Container Reset

For a complete reset including the database container:

```bash
# Stop all containers
docker compose down

# Remove the database volume
docker volume rm puzzlespring_postgres_data

# Start containers again
docker compose up -d

# Run initial setup
docker compose exec app python manage.py initial_setup
```

{: .warning }
> This method completely erases all data and requires you to set up the application from scratch. Use with caution!
