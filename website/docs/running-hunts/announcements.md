---
layout: default
title: Announcements
parent: Running Hunts
nav_order: 5
---

# Announcements

This guide covers sending updates and announcements to teams during a hunt.

## Send an Update

To create an update about the hunt or a specific puzzle:

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

## Update Visibility

When an update is created, it will:
- Appear on the "Updates" page accessible to all teams in the hunt
- Generate a notification event in the system
- Be visible to teams who have unlocked the associated puzzle (if puzzle-specific)

## Best Practices

- Keep announcements concise and clear
- Use puzzle-specific updates for errata or hints related to individual puzzles
- Use hunt-wide updates for schedule changes, general hints, or important announcements
- Consider the timing of your updates - teams may be asleep or away during off-hours
