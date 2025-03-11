---
layout: default
title: Staff Actions
parent: Usage
grand_parent: Usage
nav_order: 2
---

# Staff Actions

## Add pre-puzzlespring hunts to archive

PuzzleSpring allows you to add information about hunts that were run before you started using PuzzleSpring. These display-only hunts appear in the archive but don't have playable puzzles.

### Adding a Display-Only Hunt

1. Navigate to the Django Admin interface at `/admin/`
2. Go to the "Display only hunts" section under Puzzlehunt
3. Click "Add Display Only Hunt"
4. Fill in the following information:
   - **Name**: The name of the hunt
   - **Display start date**: When the hunt started
   - **Display end date**: When the hunt ended
   - **Num teams**: The number of teams that participated
   - **Num puzzles**: The number of puzzles the hunt had
5. Click "Save"

The hunt will now appear in the archive alongside your regular PuzzleSpring hunts, but without playable content.

## Set up external authentication

PuzzleSpring supports various external authentication providers through Django Allauth, allowing users to log in using their existing accounts from services like Google, GitHub, or Facebook.

### Enabling External Authentication Providers

1. Navigate to the Django Admin interface at `/admin/`
2. Go to "Social applications" under Social Accounts
3. Click "Add social application"
4. Select the provider you want to enable (e.g., Google, GitHub)
5. Enter the required credentials:
   - **Name**: A name for this authentication provider
   - **Client ID**: The client ID from your provider's developer console
   - **Secret key**: The secret key from your provider's developer console
   - **Key**: Additional key if required by the provider
6. In the "Sites" section, move your site from "Available sites" to "Chosen sites"
7. Click "Save"

### Provider-Specific Setup

Each provider requires specific setup in their developer console:

- **Google**: Create OAuth credentials in the Google Cloud Console
- **GitHub**: Register a new OAuth application in GitHub Developer Settings
- **Facebook**: Create a new app in the Facebook Developer Portal

For all providers, you'll need to configure the redirect URI as:
`https://your-domain.com/accounts/provider/login/callback/`
(Replace "provider" with the specific provider name like "google" or "github")

## Manually unlock a puzzle

Sometimes you may need to manually unlock puzzles for teams, such as when bypassing normal unlock rules for testing or helping teams that encounter issues.

### Unlocking a Puzzle for a Team

1. Navigate to the Django Admin interface at `/admin/`
2. Go to the "Puzzle statuses" section under Puzzlehunt
3. Click "Add Puzzle Status"
4. Fill in the required information:
   - **Puzzle**: Select the puzzle to unlock
   - **Team**: Select the team to unlock it for
   - **Unlock time**: Set to the current time (or when you want it to unlock)
   - Leave "Solve time" blank
5. Click "Save"

## Make a new info page

Info pages are static content pages that appear in the navigation bar and provide additional information to users, such as rules, resources, or FAQs.

### Creating a New Info Page

1. Navigate to the Django Admin interface at `/admin/`
2. Go to the "Info pages" section under Puzzlehunt
3. Click "Add info page"
4. Fill in the page details:
   - **URL**: The path for the page (e.g., `/rules/` will be accessible at `/info/rules/`)
   - **Title**: The page title shown in the navigation bar
   - **Content**: The HTML content of the page (can include Django template tags)
   - **Registration required**: Check if the page should only be visible to logged-in users
5. Click "Save"

The new info page will immediately appear in the navigation bar and be accessible to users.

## Reset a user's password

As an administrator, you may need to help users who have forgotten their passwords or are having trouble accessing their accounts.

### Resetting a Password from the Admin Interface

1. Navigate to the Django Admin interface at `/admin/`
2. Go to the "Users" section under Puzzlehunt
3. Find and select the user whose password you want to reset
4. In the user detail page, click on the password field
5. Enter a new password
6. Click "Save"

### Considerations for Password Resets

- Always verify the user's identity before resetting their password
- Encourage users to use the "Forgot Password" link on the login page when possible
- For security reasons, consider having users change their password again after they log in with an admin-set password

## Import/Export a hunt

PuzzleSpring provides robust functionality for exporting and importing hunts, allowing you to back up hunt data, transfer hunts between instances, or create templates for future hunts.

### Exporting a Hunt

#### From the Staff Interface

1. Navigate to the Staff > Hunts page
2. Find the hunt you want to export
3. Click the export button for the hunt you want to export
4. Choose whether to include activity data (submissions, hints, etc.)
5. The hunt will be exported as a `.phe` (PuzzleHunt Export) file

#### What Gets Exported

A hunt export includes:

- Hunt configuration and settings
- All puzzles and their attributes
- Puzzle files and solution files
- Hunt template files
- Canned hints and responses
- Team ranking rules
- Pre-puzzles associated with the hunt

If you choose to include activity data, the export will also contain:
- Teams and their members
- Puzzle statuses (unlocks and solves)
- Hint requests and responses
- Submissions
- Updates and announcements

### Importing a Hunt

#### From the Staff Interface

1. Navigate to the Staff > Hunts page
2. Click the "Import Hunt" button
3. Select a `.phe` file to upload
4. Choose whether to include activity data
5. Click "Import"
6. The import will be processed in the background

#### Import Considerations

- The import process runs in the background and may take several minutes for large hunts
- User references in activity data will be linked to existing users if they exist
- File paths and references are automatically adjusted to work in the new instance

### Using Export/Import for Templates

You can use the export/import functionality to create template hunts:

1. Create a hunt with your desired structure and settings
2. Add template puzzles with placeholder content
3. Configure the unlocking rules and other settings
4. Export the hunt without activity data
5. Import this template whenever you need to create a new hunt with similar structure

### Troubleshooting Import Issues

If you encounter issues during import:

1. Check the server logs for detailed error messages
2. Ensure the `.phe` file is valid and not corrupted
3. Verify that your instance has enough disk space for the imported files

{: .warning }
> Importing a hunt with activity data will create duplicate teams if teams with the same names already exist. Use this option with caution.

## Set up a playtest team

PuzzleSpring includes special functionality for playtest teams, allowing them to access hunts before the official start date. This feature is essential for testing puzzles and hunt mechanics prior to public release.

### What Are Playtest Teams?

Playtest teams are special teams designated to test hunt content before it's released to the general public. They can:

- Access the hunt before the official start date
- Provide feedback on puzzles and mechanics
- Help identify issues or bugs
- Test the difficulty and flow of the hunt

### Setting Up Playtest Teams

#### Creating a New Playtest Team

1. Go to Django Admin > Teams
2. Click "Add Team"
3. Fill in the team details
4. Check the "Playtester" checkbox
5. Set the "Playtest start date" and "Playtest end date"
6. Save the team

#### Converting an Existing Team to a Playtest Team

1. Go to Django Admin > Teams
2. Select the team you want to convert
3. Check the "Playtester" checkbox
4. Set the "Playtest start date" and "Playtest end date"
5. Save the team

### Playtest Date Fields

- **Playtest start date**: When the team can begin accessing the hunt
- **Playtest end date**: When the team's playtest period ends

These dates define a specific window during which the playtest team can access the hunt, regardless of the hunt's official start and end dates.

### Monitoring Playtest Teams

Staff can monitor playtest teams through the standard staff interfaces:

- The Progress page shows playtest team progress alongside regular teams
- The Feed page includes playtest team activity

{: .note }
> Playtest teams can be identified in the admin interface and staff pages by the "Playtester" flag on their team record.


## Send an update about the hunt or a specific puzzle

To send create an update about the hunt or a specific puzzle:

1. Log in with a staff or superuser account
2. Navigate to the Django Admin interface at `/admin/`
3. Click on "Updates" in the Puzzlehunt section
4. Click "Add Update" in the top right corner
5. Fill in the update form:
   - **Hunt**: Select the hunt this announcement is for
   - **Puzzle**: (Optional) Select a specific puzzle if the announcement is puzzle-specific, or leave blank for a general hunt announcement
   - **Text**: Enter the announcement text (up to 1000 characters)
   - **Time**: Set the announcement time (defaults to current time)
6. Click "Save" to create the announcement

When an update is created, it will:
- Appear on the "Updates" page accessible to all teams in the hunt
- Generate a notification event in the system
- Be visible to teams who have unlocked the associated puzzle (if puzzle-specific)


## Reset the database

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