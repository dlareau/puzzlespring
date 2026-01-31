---
layout: default
title: Managing Teams
parent: Running Hunts
nav_order: 3
---

# Managing Teams

This guide covers common team management tasks including playtest teams, manual puzzle unlocks, and password resets.

## Set Up a Playtest Team

PuzzleSpring includes special functionality for playtest teams, allowing them to access hunts before the official start date. This feature is essential for testing puzzles and hunt mechanics prior to public release.

### What Are Playtest Teams?

Playtest teams are special teams designated to test hunt content before it's released to the general public. They can:

- Access the hunt before the official start date
- Provide feedback on puzzles and mechanics
- Help identify issues or bugs
- Test the difficulty and flow of the hunt

### Creating a New Playtest Team

1. Go to Django Admin > Teams
2. Click "Add Team"
3. Fill in the team details
4. Check the "Playtester" checkbox
5. Set the "Playtest start date" and "Playtest end date"
6. Save the team

### Converting an Existing Team to a Playtest Team

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

## Manually Unlock a Puzzle

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

## Reset a User's Password

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
