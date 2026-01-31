---
layout: default
title: Developer Guide
nav_order: 9
---

# Developer Guide

{: .warning }
> This guide is currently under development. More detailed information will be added once the project is more stable.

## Technology Stack

### Backend
- **Framework**: Django
- **Database**: PostgreSQL
- **Cache & Message Broker**: Redis
- **Task Queue**: Huey
- **Real-time Updates**: Server-Sent Events via Pushpin
- **Web Server**: Caddy

### Frontend
- **CSS Framework**: Bulma
- **JavaScript Libraries**:
  - HTMX for dynamic updates
  - Alpine.js for reactive components
  - Ace Editor for template editing
  - DataTables for enhanced table functionality

### Development & Deployment
- **Containerization**: Docker & Docker Compose
- **Documentation**: Jekyll with Just the Docs theme
- **Version Control**: Git
- **CI/CD**: GitHub Actions
- **Documentation Hosting**: GitHub Pages

## Development Setup

For setup instructions, please refer to:
- [Quickstart](installation/quickstart.html) - Get up and running quickly
- [Production Deployment](installation/production.html) - Detailed deployment guide

## Coming Soon

Detailed documentation covering:
- Development environment setup
- Code organization and architecture
- Testing procedures
