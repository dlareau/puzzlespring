---
layout: default
title: Quick Start Guide
parent: Getting Started
nav_order: 1
---

# Quick Start Guide

This guide will help you get PuzzleSpring up and running quickly to see the app in action.

## Basic Setup

1. Install Docker and Docker Compose.

2. Clone the repository:

    ```bash
    git clone https://github.com/puzzlespring/puzzlespring.git
    ```

3. Setup your environment file:

    ```bash
    cp sample.env .env
    ```

    You can then edit the `.env` file to set your environment variables.

4. Run the development server:

    ```bash
    docker compose up -d
    ```

5. Run the initial setup command:

    ```bash
    docker compose exec web python manage.py initial_setup
    ```

6. Open your browser and navigate to `http://localhost:8000`.
