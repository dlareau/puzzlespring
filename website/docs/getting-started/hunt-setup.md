---
layout: default
title: Hunt Setup Guide
parent: Getting Started
nav_order: 2
---

{: .warning }
This guide is a work in progress and is not yet complete.

# Setting Up Your First Hunt

PuzzleSpring is designed with flexibility in mind, allowing you to host puzzle hunts without having to modify the source code. That isn't to say you can't, you're welcome to hack away at and turn PuzzleSpring into exactly what you need, but it is the goal of this platform that you won't have to. This is achieved through a flexible customization system that includes:

- Uploaded files for puzzle content and styling
- The ability to provide your own templates that can layer on top of PuzzleSpring's base templates
- Extensive configuration options in the admin interface

{: .note }
This guide will walk you through the process of setting up your first hunt. We recommend following the order presented here your first time using PuzzleSpring, as it's designed to make the setup process as smooth as possible.

## Setup Strategy

The recommended approach is to focus on data setup before styling:

1. Create the basic hunt structure and puzzles
2. Configure core settings and functionality
3. Add puzzle content and files
4. Apply custom styling and templates
// TODO: come back and see if this order is correct

This approach allows you to iterate on the hunt's appearance once all the fundamental pieces are in place. Don't worry if you're unsure about exact puzzle details - everything can be modified later.

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
PuzzleSpring supports multiple hunts in order to allow organizations to archive past hunts and allow them to still be played, but only one can be the active "current hunt" at a time.

Don't worry about the other settings for now, we'll cover them in a later section. You can go ahead and save the hunt and move on to the next step.

## Creating Puzzles

After setting up your hunt, the next step is to create the puzzles. Each puzzle is created through the Django admin interface and requires several key pieces of information.

### Basic Puzzle Information

- **ID**: A unique 3-8 character hex string identifier.
- **Name**: The puzzle name shown to participants
- **Order Number**: Position in the hunt (for sorting)
- **Type**: One of:
  - Standard: Regular puzzle
  - Meta: Meta-puzzle that uses answers from other puzzles
  - Final: Final puzzle of the hunt, solving it can be used to mark the team as finished.
  - Non-puzzle: Content that isn't a puzzle (e.g., story elements), and will not be counted on the leaderboard.

{: .note }
The puzzle ID must be unique across all puzzles on the site, so it is recommended to build in some form of hunt prefix to your puzzle IDs. For example, we made the first puzzle in our first hunt "1001", and the first puzzle in our second hunt "2001", giving us 3 digits for the puzzle IDs in each hunt.

### Answer Settings

Each puzzle has configurable answer validation settings:

- **Answer**: The correct solution to the puzzle
- **Case Sensitive**: If enabled, answers must match the exact case. If disabled, "ANSWER" and "answer" are treated the same.
- **Allow Spaces**: If enabled, spaces in answers are preserved. If disabled, all spaces are removed before checking.
- **Allow Non-alphanumeric**: If enabled, special characters are allowed in answers. If disabled, only letters and numbers are kept.

{: .warning }
Make sure your answer validation settings match your answer format. For example, if your answer contains spaces, you must enable the "Allow Spaces" setting. Don't worry though, the admin interface will validate this for you.

{: .note }
At this stage, focus on creating the basic puzzle structure. You'll add puzzle content and files in a later step.

## Customizing Puzzle Responses

Each puzzle in PuzzleSpring can be configured with custom response settings to provide specific feedback for different answer submissions. This is particularly useful for giving hints or custom messages for common wrong answers.

### Custom Response Messages

You can set up custom responses for specific wrong answers using Python-style regex patterns:

1. In the puzzle's admin page, find the "Auto Responses" section
2. Add a new response with:
   - **Regex**: A Python-style regex pattern to match against submissions
   - **Text**: The response message to show when the pattern matches

For example:
```python
# Match "hello"
Regex: ^hello$
Text: Almost there! Think about saying goodbye instead.

# Match any answer containing "world"
Regex: .*world.*
Text: You're thinking globally, but this puzzle is more personal.
```

The system checks submissions against these patterns in order. If no pattern matches:
- Correct answers receive the response "Correct"
- Wrong answers receive the response "Wrong Answer."

## Puzzle Files and Templates

PuzzleSpring supports multiple file types and templating options for both puzzles and solutions.

### File Types

1. **HTML Files**: Full HTML pages to allow for custom styling and scripts

2. **PDF Files**: Embedded directly in the puzzle page

3. **Template Files** (use custom file extension `.tmpl`): Fully custom django template with access to puzzle context

### File Organization

Each puzzle can have two sets of files:

1. **Puzzle Files**:
   - Main puzzle content (HTML, PDF, or template)
   - Supporting files (images, stylesheets, scripts)
   - Accessible while solving the puzzle

2. **Solution Files**:
   - Solution content (HTML, PDF, or template)
   - Supporting files for the solution
   - Only accessible after solving the puzzle

{: .note }
PuzzleSpring automatically protects puzzle files from being accessed before the related puzzle is unlocked.


### Hunt-wide Templates

The hunt itself can have several global files:

1. **Template File**: Defines the layout for the main hunt page

2. **CSS File**: Global stylesheet applied to all hunt pages including all puzzle pages

3. **Info Page File**: Optional Django template for hunt information

### Template Context

When using template files, you have access to:

1. **Puzzle Context**:
   ```
   puzzle: The current puzzle object
   team: The current team
   solved: Boolean indicating if the puzzle is solved
   submissions: List of team's submissions for this puzzle
   form: The answer submission form
   updates: List of updates for this puzzle
   ```

2. **Hunt Context**:
   ```
   hunt: The current hunt object
   puzzles: List of accessible puzzles
   team: The current team
   solved: List of solved puzzles
   ```

### File Management Interface

Access the file management interface through:
1. Staff Hunt Overview page → Files button (folder icon)
2. Staff Puzzle Overview page → Files button (folder icon with "P")
3. Staff Puzzle Overview page → Solution Files button (folder icon with "S")

For each file, you can:
- Upload new files
- Replace existing files
- Set as main/CSS file (toggle switch)
- Download files
- Preview files (eye icon)

{: .note }
When linking to files from HTML or templates, use relative paths. For puzzle files, use the `puzzle_static` template tag.
// TODO: consolidate on whether we should use the template tag or not

Below the template and CSS file section, there is an option to upload an Info Page file. This file, which can be a Django template, serves as the hunt's general information page. It typically contains details such as an FAQ and other relevant information. This page is generally accessible before the hunt begins.

At the bottom of the Hunt page, there is a section for Team Ranking Rules. This determines the leaderboard order and is also used in various places throughout the site to visualize team standings. You can choose an ordering method and specify whether each ranking statistic should be visible on the leaderboard.

Beyond setting up your hunt, you can also configure general site settings. The most notable site-wide configuration is the addition of Info Pages. These are extra informational pages, such as resources or FAQs, that appear in the top navigation bar. You can create them through the Django admin in the Info Page section. Here, you can define the URL, title, and content of each page. The content can be a Django template, allowing for dynamic rendering.

## Pre-Puzzles

Pre-puzzles are special puzzles that can be accessed by the public without logging in, designed to be available before the main puzzle hunt begins.

### Creating Pre-Puzzles

Pre-puzzles can be created through the Django admin interface

### Pre-Puzzle Settings

**Basic Information**:
   - `name`: The puzzle name (up to 200 characters)
   - `released`: Boolean controlling public visibility
   - `hunt`: Optional link to an associated hunt

All other settings are the same as for regular puzzles.

### Access Control

Pre-puzzles have simpler access control than regular puzzles:
- Public access is controlled by the `released` flag
- No team or hunt membership required
- No unlocking rules or dependencies

### File Organization

Pre-puzzle files are organized similarly to regular puzzles:
1. **Main File**:
   - HTML, PDF, or template file
   - Defines the puzzle content and layout

2. **Supporting Files**:
   - Stored in the pre-puzzle's file directory
   - Accessible through the `prepuzzle_static` template tag

### Template Integration

Pre-puzzles can use Django templates with access to:
```
puzzle: The pre-puzzle object
form: The answer submission form
submission: The latest submission (if any)
```

## Puzzle Unlocking and Configuration

PuzzleSpring uses a powerful domain-specific language to configure puzzle unlocking rules, point rewards, and hint allocations. You can find more information in the [Hunt Configuration Language](../technical-reference/hunt-config-language.md) reference.

### Best Practices
   - Plan puzzle dependencies carefully
   - Consider multiple paths to progress
   - Balance point requirements
   - Test unlocking sequences thoroughly


## Hints and Hint Management

PuzzleSpring provides a flexible hint system with multiple configuration options and management tools.

### Hint Types

1. **Custom Hints**:
   - Teams request specific help
   - Staff members respond manually
   - Can be claimed and managed by staff
   - Support for refunding used hints

2. **Canned Hints**:
   - Pre-written hints for common issues
   - Automatically revealed in order
   - No staff intervention needed
   - Configurable per puzzle

### Hint Pools

The hunt can be configured with different hint pool types:

1. **Global Pool**:
   - All hints come from a team's global hint count
   - Simpler to manage
   - Default setting

2. **Puzzle-Specific**:
   - Each puzzle has its own hint pool
   - More granular control
   - Hints earned through puzzle-specific rules

3. **Both Pools**:
   - Combines global and puzzle-specific pools
   - Most flexible option
   - Complex allocation rules

### Hint Policies

Configure how canned and custom hints interact:

1. **Canned First**:
   - Teams must use canned hints before custom hints
   - Encourages using prepared help first
   - Default setting

2. **Canned Only**:
   - Only canned hints allowed
   - No custom hint requests
   - Fully automated hint system

3. **Mixed**:
   - Teams can use either type
   - Maximum flexibility
   - May increase staff workload

### Pool Allocation

When using both pools, configure how hints are allocated:

1. **Puzzle Priority**:
   - Use puzzle-specific hints before global hints
   - Default setting

2. **Hint Type Split**:
   - Canned hints use puzzle pool
   - Custom hints use global pool
