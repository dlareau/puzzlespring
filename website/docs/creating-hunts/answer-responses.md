---
layout: default
title: Answer Responses
parent: Creating Hunts
nav_order: 5
---

# Answer Responses

This guide covers configuring answer validation and custom response messages for puzzles in PuzzleSpring.

## Answer Settings

Each puzzle has configurable answer validation settings:

- **Answer**: The correct solution to the puzzle
- **Case Sensitive**: If enabled, answers must match the exact case. If disabled, "ANSWER" and "answer" are treated the same.
- **Allow Spaces**: If enabled, spaces in answers are preserved. If disabled, all spaces are removed before checking.
- **Allow Non-alphanumeric**: If enabled, special characters are allowed in answers. If disabled, only letters and numbers are kept.

{: .warning }
Make sure your answer validation settings match your answer format. For example, if your answer contains spaces, you must enable the "Allow Spaces" setting. Don't worry though, the admin interface will validate this for you.

## Custom Response Messages

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
