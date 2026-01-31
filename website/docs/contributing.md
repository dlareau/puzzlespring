---
layout: default
title: Contributing
nav_order: 7
---

# Contributing

Thank you for your interest in contributing to PuzzleSpring! This document provides guidelines and information for contributors.

## Development Process

### Branching Strategy

- `main` branch represents the latest stable version
- Create feature branches from `main` using the format: `feature/description` or `fix/description`
- Keep branches focused on a single feature or fix

### Making Changes

1. Create a new branch for your changes
2. Make your changes following our coding standards
3. Write or update tests as needed
4. Update documentation if required
5. Commit your changes with clear, descriptive commit messages

## Project Structure

- `config/` - Configuration files
- `puzzlehunt/` - Main Django application
  - `management/` - Management commands
  - `migrations/` - Database migrations
  - `static/` - Static assets
  - `templates/` - Django templates
- `scripts/` - Documentation generation and utility scripts
- `server/` - Django project configuration files
- `website/` - Documentation and landing page
  - `docs/` - Jekyll-based documentation
  - `public/` - Landing page files

## Coding Standards

### Python Code

- Follow PEP 8 style guide
- Use meaningful variable and function names
- Add docstrings for functions and classes
- Keep functions focused and concise

### Templates

- Use Bulma classes for styling
- Prefer HTMX for dynamic interactions
- Follow the established template hierarchy
- Document template blocks and context variables

## Documentation

- Update documentation for new features
- Follow the existing documentation style
- Include examples where appropriate

## License

By contributing to PuzzleSpring, you agree that your contributions will be licensed under the MIT License. 