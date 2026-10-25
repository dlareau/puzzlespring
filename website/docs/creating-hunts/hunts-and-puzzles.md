---
layout: default
title: Hunts and Puzzles
parent: Creating Hunts
nav_order: 1
---

# Hunts and Puzzles

This guide covers creating and configuring hunts and puzzles in PuzzleSpring.

## Overview

PuzzleSpring is designed with flexibility in mind, allowing you to host puzzle hunts without having to modify the source code. This is achieved through:

- Uploading files for puzzle content and styling
- The ability to provide your own templates that can layer on top of PuzzleSpring's base templates
- Extensive configuration options in the admin interface

{: .note }
We recommend focusing on data setup before styling:
1. Create the basic hunt structure and puzzles
2. Configure core settings and functionality
3. Add puzzle content and files
4. Apply custom styling and templates

## Creating a Hunt

The first step is creating a Hunt object, which serves as the foundation for your puzzle hunt. If you used the setup script, a default hunt will already be created for you. If not, you'll need to create one manually through the Django admin interface.

### Hunt Settings

A Hunt object requires several key settings:

- **Name**: The public-facing name of your hunt
- **Team Size Limit**: Maximum number of members allowed per team
- **Dates**:
  - Start Date: When the hunt becomes visible to registered users
  - End Date: When the hunt is archived and available to the public
  - Display Start/End Dates: The dates shown to users (can differ from actual dates)
- **Location**: Starting location of the hunt (optional, used for in-person hunts)
- **Current Hunt**: Whether this is the active hunt

{: .important }
PuzzleSpring supports multiple hunts in order to allow organizations to archive past hunts and allow them to still be played, but only one hunt can be the active "current hunt" at a time.

Don't worry about the other settings for now, we'll cover them in later sections. You can go ahead and save the hunt and move on to the next step.

### Hunt-wide Templates

The hunt itself can have several global files configured in the Django admin:

1. **Template File**: Defines the layout for the main hunt page

2. **CSS File**: Global stylesheet applied to all hunt pages including all puzzle pages

3. **Info Page File**: Optional Django template for hunt information

When using template files, you have access to the following context:

**Hunt Context**:
```
hunt: The current hunt object
puzzles: List of accessible puzzles
team: The current team
solved: List of solved puzzles
rounds: List of unlocked rounds (all rounds for staff, or once the hunt is public)
```

## Creating Puzzles

After setting up your hunt, the next step is to create the puzzles. Each puzzle is created through the Django admin interface and requires several key pieces of information.

{: .note }
At this stage, focus on creating the basic puzzle structure. You'll add puzzle content and files in the [Puzzle Content](puzzle-content.html) guide.

### Basic Puzzle Information

- **ID**: A unique 3-8 character hex string identifier used in URLs and configurations.
- **Name**: The puzzle name shown to participants
- **Order Number**: Position in the hunt (for sorting)
- **Type**: One of:
  - Standard: Regular puzzle
  - Meta: Meta-puzzle that uses answers from other puzzles
  - Final: Final puzzle of the hunt, solving it can be used to mark the team as finished.
  - Non-puzzle: Content that isn't a puzzle (e.g., story elements), and will not be counted on the leaderboard.

{: .note }
The puzzle ID must be unique across all puzzles on the site, so it is recommended to build in some form of hunt prefix to your puzzle IDs. For example, we made the first puzzle in our first hunt "1001", and the first puzzle in our second hunt "2001", giving us 3 digits for the puzzle IDs in each hunt.

## Rounds

Rounds are an optional way to group a hunt's puzzles. Each round has a name, a number, and its own page at `/hunt/<hunt id>/round/<round number>/view/`. A team can't open a round, or any puzzle in it, until the round is unlocked.

Create rounds and choose their puzzles on the [Rounds](../running-hunts/staff-tools.html#rounds) staff page. Then add rules to the hunt config to unlock them, for example:

```
[R1] <= 0 POINTS     # Round 1 is open from the start
[R2] <= P009         # Round 2 opens when puzzle 009 is solved
```

See [Unlock Rules](unlock-rules.html#rounds) for the full syntax.

### Round Templates

By default, a round's page lists its puzzles with their solve status. To give a round a custom page, select it from the dropdown at the top of the **Hunt Template** staff page and write a template the same way you would for the hunt.

Round templates have the following context:

**Round Context**:
```
round: The current round
hunt: The current hunt object
puzzles: The round's puzzles that the team has unlocked
team: The current team
solved: List of solved puzzles in this round
rounds: List of unlocked rounds (all rounds for staff, or once the hunt is public)
```

Two template tags help when laying out rounds and puzzles by number:

- `round_unlocked` checks whether a round is in a list of rounds:
  ```
  {% raw %}{% if rounds|round_unlocked:2 %}<a href="...">Round 2</a>{% endif %}{% endraw %}
  ```
- `with_puzzle` renders its contents only if the puzzle with the given order number is in the list, and makes it available by name:
  ```
  {% raw %}{% with_puzzle puzzles 21 as puzzle %}
    <a href="/puzzle/{{ puzzle.id }}/view/">{{ puzzle.name }}</a>
  {% endwith_puzzle %}{% endraw %}
  ```

{: .note }
Use the **Unlocked rounds** box in the template editor's preview to see how the hunt or round page looks with different rounds unlocked.

## Team Ranking Rules

At the bottom of the Hunt admin page, configure Team Ranking Rules to control the leaderboard order and team standings display. You can choose an ordering method and specify whether each ranking statistic should be visible on the leaderboard.
