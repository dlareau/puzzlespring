---
layout: default
title: Prepuzzles
parent: Creating Hunts
nav_order: 6
---

# Prepuzzles

Pre-puzzles are special puzzles that can be accessed by the public without logging in, designed to be available before the main puzzle hunt begins.

## Creating Pre-Puzzles

Pre-puzzles can be created through the Django admin interface.

## Pre-Puzzle Settings

**Basic Information**:
- `name`: The puzzle name (up to 200 characters)
- `released`: Boolean controlling public visibility
- `hunt`: Optional link to an associated hunt

All other settings are the same as for regular puzzles.

## Access Control

Pre-puzzles have simpler access control than regular puzzles:
- Public access is controlled by the `released` flag
- No team or hunt membership required
- No unlocking rules or dependencies

## File Organization

Pre-puzzle files are organized similarly to regular puzzles:

1. **Main File**:
   - HTML, PDF, or template file
   - Defines the puzzle content and layout

2. **Supporting Files**:
   - Stored in the pre-puzzle's file directory
   - Accessible through the `prepuzzle_static` template tag

## Template Integration

Pre-puzzles can use Django templates with access to:
```
puzzle: The pre-puzzle object
form: The answer submission form
submission: The latest submission (if any)
```
