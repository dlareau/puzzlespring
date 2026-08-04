---
layout: default
title: Staff Tools
parent: Running Hunts
nav_order: 2
---

# Staff Tools

PuzzleSpring includes several specialized tools for hunt management. These are accessible from the staff sidebar.

## Team Data Questions

The Team Data Questions page lets you configure custom registration questions for a hunt. Located in the sidebar under "Hunt Setup", next to Puzzles.

Each hunt has its own independent set of questions - configuring questions on one hunt has no effect on any other hunt.

### Question Types

- **Text**: A free-text field, up to 200 characters
- **Yes/No**: A toggle switch
- **Select (single choice)**: A dropdown with a staff-defined list of options

### Adding and Editing Questions

Click **Add Question** to create a new question, or the pencil icon on an existing question to edit it in place. Each question has:

- **Name**: The label shown to teams when registering
- **Leaderboard Label**: An optional shorter label for the leaderboard/participant-info columns. If left blank, the question's name is used there instead.
- **Description**: Optional help text shown under the field on the registration form
- **Type**: Text, Yes/No, or Select
- **Required**: Whether a team must answer this to register or update their team
- **Visible on Leaderboard**: Whether this question's answers appear as a column on the leaderboard
- **Groups Leaderboard**: Whether the leaderboard is split into per-answer tabs based on this question. Only one question per hunt can be used for grouping - enabling it on a question automatically disables it on any other.

For **Select** questions, enter one option per line. To show different text on the leaderboard than what's shown in the dropdown, add `| shorter text` after the option, e.g.:

```
N/A (not affiliated with any group) | N/A
Rookie
Veteran
```

Here, teams would see the full "N/A (not affiliated with any group)" text when registering, but the leaderboard and participant-info tables would just show "N/A". Options without a `|` use the same text everywhere.

### Reordering and Deleting

Use the up/down arrow buttons to reorder questions - this controls both the order fields appear in on the registration form and the order of columns on the leaderboard/participant-info tables.

{: .warning }
> Deleting a question also deletes every team's answer to it. This cannot be undone.

### Adding Questions to an Active Hunt

Adding a question after teams have already registered doesn't retroactively require anything of existing teams - it simply appears the next time they visit their team page. Until a team answers it, they'll show as "-" on the leaderboard/participant-info, or fall into an "Unspecified" leaderboard group if the question is used for grouping.

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

### Team Data

If the hunt has any [Team Data Questions](#team-data-questions) configured, a table of every team's answers is shown below the search box, one column per question (using each question's leaderboard label, if set).
