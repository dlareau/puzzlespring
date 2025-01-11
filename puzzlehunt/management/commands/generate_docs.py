from django.core.management.base import BaseCommand
from scripts.generate_model_docs import generate_model_docs
from scripts.generate_api_docs import generate_api_docs
from scripts.generate_template_docs import generate_template_docs

class Command(BaseCommand):
    help = 'Generates markdown documentation for models and APIs'

    def handle(self, *args, **options):
        generate_model_docs()
        generate_api_docs()
        generate_template_docs()
        self.stdout.write(self.style.SUCCESS('Successfully generated documentation'))
