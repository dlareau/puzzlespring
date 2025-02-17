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
    git clone https://github.com/dlareau/puzzlespring.git
    ```

3. Navigate to the project directory:

    ```bash
    cd puzzlespring
    ```

4. Setup your environment file:

    ```bash
    cp sample.env .env
    ```

    You can then edit the `.env` file to set your environment variables.

5. Run the development server:

    ```bash
    docker compose up -d
    ```

6. Run the initial setup command:

    ```bash
    docker compose exec app python manage.py initial_setup
    ```

7. Open your browser and navigate to `https://localhost:8443`.

{: .note }
> You may see an invalid certificate warning while developing locally. It is safe to click through it.


