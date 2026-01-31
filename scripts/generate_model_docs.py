from django.apps import apps
from django.db.models import fields
import inspect
import os

def get_model_fields(model):
    """Extract field information from a Django model."""
    field_docs = []
    for field in model._meta.get_fields():
        if isinstance(field, (fields.Field, fields.related.RelatedField)):
            field_type = field.get_internal_type()
            field_docs.append(f"- `{field.name}` ({field_type}): {field.help_text or 'No description available'}")
    return field_docs

def generate_model_docs():
    """Generate markdown documentation for all models."""
    output = []
    
    # Header
    output.extend([
        "---",
        "layout: default",
        "title: Data Model",
        "parent: Reference",
        "nav_order: 1",
        "---",
        "",
        "# Data Model",
        "",
        "This document describes the data models used in the PuzzleSpring application.",
        ""
    ])

    # Get all models
    app_models = apps.get_app_config('puzzlehunt').models.items()
    
    for model_name, model in sorted(app_models):
        # Get model docstring
        model_doc = inspect.getdoc(model) or "No description available."
        
        output.extend([
            f"## {model.__name__} Model",
            "",
            model_doc,
            "",
            "Fields:",
        ])
        
        # Add field documentation
        output.extend(get_model_fields(model))
        output.append("")
    
    # Write to file
    docs_path = "website/docs/reference/data-model.md"
    os.makedirs(os.path.dirname(docs_path), exist_ok=True)
    with open(docs_path, "w") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    generate_model_docs() 