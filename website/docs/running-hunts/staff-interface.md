---
layout: default
title: Staff Interface
parent: Running Hunts
nav_order: 1
---

# Staff Interface

This guide provides an overview of the staff pages and navigation in PuzzleSpring.

PuzzleSpring provides two different interfaces for managing the application: Staff Pages and the Django Admin interface. Each serves different purposes and offers different levels of control.

## Staff Pages

Staff pages are purpose-built interfaces designed specifically for puzzle hunt management. They're accessible to any user with staff privileges and focus on hunt-specific operations.

### Accessing Staff Pages

1. Log in with a staff account
2. Navigate to any normal site page
3. Click on the wrench icon in the navigation bar

### Available Staff Pages

- **Hunts**: Overview of all hunts with creation and management options
- **Search**: Search functionality across teams, users, and puzzles
- **Progress**: Real-time team progress tracking with filtering options
- **Feed**: Activity feed showing submissions, hints, and other events
- **Hints**: Interface for managing and responding to hint requests
- **Charts**: Visual analytics of hunt progress and team performance
- **Hunt Template**: Editor for customizing the hunt's appearance
- **Puzzles**: Interface for managing puzzles and their attributes
- **Hunt Config**: Editor for puzzle unlocking rules and hunt configuration

## Django Admin Interface

The Django Admin interface provides low-level access to the database models and is intended for system administrators and developers. It offers more powerful but less user-friendly controls.

### Accessing Django Admin

1. Log in with a superuser account
2. Navigate to `/admin/` or click "Django Admin" in the staff sidebar

### Key Admin Sections

- **Users**: Create, modify, and delete user accounts
- **Teams**: Manage team membership and properties
- **Hunts**: Configure hunt settings and properties
- **Puzzles**: Create and edit puzzles at the database level
- **Submissions**: View and manage all submissions
- **Hints**: Access all hint requests and responses
- **Updates**: Manage hunt announcements and updates
- **Constance Config**: Modify site-wide settings

### When to Use Django Admin

- Fixing data inconsistencies
- Configuring system-wide settings
- Managing user permissions and roles

{: .warning }
> The Django Admin interface provides direct access to the database. Use with caution, as improper changes can affect system stability.

## Permissions and Access Control

- **Staff Users**: Can access staff pages but not necessarily Django Admin
- **Superusers**: Have full access to both staff pages and Django Admin
- **Regular Users**: Cannot access either interface

To grant staff privileges to a user:
1. Go to Django Admin > Users
2. Select the user
3. Check the "Staff" or "Superuser" status checkbox
4. Save changes

{: .note }
> For day-to-day hunt management, staff pages are recommended over Django Admin due to their specialized interfaces and safety features.
