FROM python:3.10

ENV PYTHONUNBUFFERED 1
ENV DJANGO_ENABLE_DEBUG False
ENV DJANGO_USE_SHIBBOLETH False
ENV DJANGO_SETTINGS_MODULE server.settings.env_settings

RUN mkdir /code
WORKDIR /code

RUN mkdir -p /app/static /app/media /app/custom_static /app/custom_templates

# Install redis-cli for lock management
RUN apt-get update && apt-get install -y redis-tools && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

# Make entrypoint executable
RUN chmod +x /code/scripts/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/code/scripts/entrypoint.sh"]
CMD ["gunicorn", "--workers=5", "--bind=0.0.0.0:8000", "server.wsgi:application", "--reload"]
