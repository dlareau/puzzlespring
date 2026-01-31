---
layout: default
title: Staff Tools
parent: Usage
nav_order: 3
---

# Staff Tools

PuzzleSpring includes several specialized tools for hunt management. These are accessible from the staff sidebar.

## Config Tester

The Config Tester simulates puzzle unlocking rules without affecting real team data. Use it to verify your hunt configuration before the hunt begins.

Located in the sidebar under "Hunt Setup", the Config Tester displays all puzzles in the current hunt and lets you simulate different scenarios.

### Simulating Time

The time controls at the top let you set a simulated time offset from hunt start:

- Use the **-1h**, **-5m**, **+5m**, **+1h** buttons to adjust time
- Enter a time directly in `+H:MM` format (e.g., `+2:30` for 2 hours 30 minutes)
- The absolute timestamp is shown in parentheses

### Marking Puzzles as Solved

Each puzzle row has a toggle switch to mark it as solved. When you toggle a puzzle to solved:

- The solve time defaults to the current simulated time
- You can edit the solve time in the input field using `+H:MM` format
- Toggling off clears the solve time

### Results Display

The summary box shows what a team would have earned based on your configuration:

- **Unlocked**: Number of puzzles that would be unlocked
- **Solved**: Number of puzzles marked as solved
- **Points**: Total points earned from config rules
- **Hints**: Total global hints earned
- **P. Hints**: Puzzle-specific hints (shown per puzzle in the table)
- **Badges**: Any badges earned are displayed below the summary

Use the **Reset All** button to clear all solved states and reset time to zero.

{: .note }
If your hunt configuration has syntax errors, they will be displayed in a red notification box.

## File Editor

The File Editor provides an in-browser code editor for modifying puzzle and hunt files. It uses the Ace editor with syntax highlighting for HTML, CSS, JavaScript, Django templates, and plain text.

Located in the sidebar under "Hunt Setup", the File Editor has three dropdown selectors:

1. **Hunt**: Select which hunt's files to edit
2. **Puzzle / Hunt Files**: Choose a puzzle, or select "[Hunt Files]" for hunt-level files
3. **File**: Choose the specific file to edit

When editing puzzle files, both puzzle content files and solution files are available in the file dropdown.

### Editing and Saving

- Make changes in the editor
- Click **Save** or use **Ctrl+S** (Cmd+S on Mac) to save
- A status indicator shows "Saving..." and then "Saved!" on success

{: .note }
Only text-based files can be edited (HTML, CSS, JS, TMPL, TXT). Binary files like images and PDFs must be replaced through the file upload interface.

## Participant Info

The Participant Info page provides statistics and data export for hunt participants. Located in the sidebar alongside Progress, Feed, Hints, and Charts.

### Statistics

The page displays:

- **Total Participants**: All users across all teams
- **Total Teams**: All teams registered for the hunt
- **Regular Teams**: Non-playtest teams
- **Playtest Teams**: Teams marked as playtesters

### Data Export

Two export options are available for regular (non-playtest) participants:

- **Download Participant CSV**: Downloads a CSV file with email, display name, first name, last name, and team name
- **Copy Emails to Clipboard**: Copies all participant email addresses for quick pasting

### Search

The search box lets you find specific participants or teams by name, email, or team name. Results appear as you type.
