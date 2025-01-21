---
layout: default
title: In App Settings
parent: Configuration
nav_order: 1
---

# In App Settings

Information about the settings available in the app.

## Modifying Settings

PuzzleSpring uses Django Constance for managing in-app settings. Constance settings are configuration options that can be modified directly through the Django admin interface without requiring code changes or server restarts. These settings allow administrators to customize various aspects of the puzzle hunt's behavior.

To access and modify these settings:

1. Log in to the Django admin interface
2. Navigate to "Constance » Config"
3. Modify the desired settings
4. Click "Save" to apply changes

## Available Settings

### Site Settings

- `SITE_TITLE`: The title of the site

    *Default: "PuzzleSpring" • Type: String*

### Team Settings

- `NO_TEAMS_MODE`: If enabled, each user will be their own team

    *Default: False • Type: Boolean*

- `TEAM_MEMBERS_CAN_SEE_NAMES`: If enabled, team members will be able to see users names on the team page

    *Default: True • Type: Boolean*

### Hunt Display Settings

- `SINGLE_HUNT_MODE`: If enabled, only one hunt will be visible and accessible

    *Default: False • Type: Boolean*

### Puzzle Display Settings

- `PROGRESS_FULL_PUZZLE_NAMES`: If enabled, the progress page will show full puzzle names

    *Default: False • Type: Boolean*

- `SHOW_SOLVE_COUNT_ON_PUZZLE`: If enabled, the puzzle page will show the current number of solves

    *Default: True • Type: Boolean*

- `SHOW_UPDATE_FOR_LOCKED_PUZZLES`: If enabled, updates will be shown even when the puzzle is locked

    *Default: True • Type: Boolean*

### Communication Settings

- `CONTACT_EMAIL`: The contact email for help links

    *Default: "test@test.com" • Type: String*

### Submission and Hint Settings

- `SHOW_SUBMISSION_USER`: If enabled, the submissions page will display usernames

    *Default: True • Type: Boolean*

- `SHOW_HINT_USER_STAFF`: If enabled, the staff hints page will show the staff responder

    *Default: True • Type: Boolean*

### Image Settings

- `NAVBAR_IMAGE`: The image displayed on the navbar

    *Default: "" • Type: Image Field*

- `EMBED_IMAGE`: The image displayed in embeds

    *Default: "" • Type: Image Field*
