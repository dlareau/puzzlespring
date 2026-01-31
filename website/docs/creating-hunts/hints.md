---
layout: default
title: Hints
parent: Creating Hunts
nav_order: 4
---

# Hints

PuzzleSpring provides a flexible hint system with multiple configuration options and management tools. All hint settings are configured in the Django Admin under the hunt's "Hint Behaviour" section.

## Earning Hints

Teams earn hints through the hunt configuration language. See the [Unlock Rules](unlock-rules.html) reference for details on hint allocation rules such as:

```
# Give 2 hints every 30 minutes
2 HINTS <= EVERY 30 MINUTES

# Give 1 puzzle specific hint 30 minutes after unlocking a puzzle
1 PX HINT <= 30 MINUTES AFTER PX UNLOCK
```

## Hint Lockout

The **Hint Lockout** setting controls how long teams must wait after unlocking a puzzle before they can request hints. This prevents teams from immediately using hints on newly unlocked puzzles.

- Configured on the Hunt in Django Admin
- Value is in minutes (default: 60 minutes)
- Set to 0 to disable the lockout

## Hint Types

### Custom Hints

- Teams request specific help
- Staff members respond manually
- Can be claimed and managed by staff
- Support for refunding used hints

### Canned Hints

- Pre-written hints for common issues
- Automatically revealed in order
- No staff intervention needed
- Configurable per puzzle

## Creating Canned Hints

To add canned hints to a puzzle:

1. Go to Django Admin > Puzzles
2. Select the puzzle you want to add hints to
3. Scroll down to the "Canned Hints" section
4. For each hint, enter:
   - **Order**: The sequence in which hints are revealed (lower numbers first)
   - **Text**: The hint content shown to teams
5. Click "Save"

Teams will see canned hints revealed in order as they spend hints on the puzzle.

## Hint Pools

The hunt can be configured with different hint pool types:

### Global Pool

- All hints come from a team's global hint count
- Simpler to manage
- Default setting

### Puzzle-Specific

- Each puzzle has its own hint pool
- More granular control
- Hints earned through puzzle-specific rules

### Both Pools

- Combines global and puzzle-specific pools
- Most flexible option
- Complex allocation rules

## Hint Policies

Configure how canned and custom hints interact:

### Canned First

- Teams must use canned hints before custom hints
- Encourages using prepared help first
- Default setting

### Canned Only

- Only canned hints allowed
- No custom hint requests
- Fully automated hint system

### Mixed

- Teams can use either type
- Maximum flexibility
- May increase staff workload

## Pool Allocation

When using both pools, configure how hints are allocated:

### Puzzle Priority

- Use puzzle-specific hints before global hints
- Default setting

### Hint Type Split

- Canned hints use puzzle pool
- Custom hints use global pool
