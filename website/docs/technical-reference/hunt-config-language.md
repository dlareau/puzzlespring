---
layout: default
title: Hunt Configuration Language
parent: Technical Reference
nav_order: 4
---

# Hunt Configuration Language

The Hunt Configuration Language is a domain-specific language used by PuzzleSpring to define puzzle unlocking rules, point rewards, and hint allocations in a puzzle hunt. This document describes the syntax and usage of the language.

## Quick Start

Here's a simple example that demonstrates basic unlocking rules:

```
# Unlock puzzle 2 when puzzle 1 is solved
P2 <= P1

# Give 10 points when puzzle 1 is solved
10 POINTS <= P1

# Unlock puzzle 3 when either puzzle 1 or 2 is solved
P3 <= (P1 OR P2)

# Give 2 hints every 30 minutes if the team has at least 10 points
2 HINTS <= EVERY 30 MINUTES IF 10 POINTS
```

## Basic Concepts

### Puzzle IDs

Puzzles are referenced using `P` followed by their hexadecimal ID. For example:
- `P1` refers to puzzle with ID 1
- `PA5` refers to puzzle with ID A5

{: .note }
When using a puzzle ID in a non-time-based rule condition, you can use just the puzzle ID (e.g. `P1`) as a shortcut for `P1 SOLVE`. For example, `P2 <= P1` is equivalent to `P2 <= P1 SOLVE`.

The special identifier `PX` can be used to create rules that apply to all puzzles. When `PX` appears multiple times in a single rule, each instance refers to the same puzzle when the rule is evaluated for each puzzle.

{: .note }
For example, the rule `2 PX HINTS <= PX UNLOCK` will give 2 hints for puzzle A when puzzle A is unlocked, 2 hints for puzzle B when puzzle B is unlocked, and so on.

### Rule Structure

Each rule follows the format:
```
<unlockable> <= <condition>
```

where `<unlockable>` specifies what should be unlocked or awarded, and `<condition>` specifies when this should happen.

### Comments

The language supports shell-style comments using the `#` character. Everything after a `#` on a line is treated as a comment and ignored by the parser:
```
# This entire line is a comment
P2 <= P1  # This is an end-of-line comment
```

## Unlockables

### Puzzles
```
P1 <= <condition>  # Unlock puzzle 1
[P1, P2] <= <condition>  # Unlock multiple puzzles
```

### Points
```
10 POINTS <= <condition>  # Award 10 points
[5 POINTS, P1] <= <condition>  # Award 5 points and unlock P1
```

### Hints
```
2 HINTS <= <condition>  # Award 2 hints
3 P1 HINTS <= <condition>  # Award 3 hints for puzzle 1
```

## Rule Conditions

### Single-Use Rules

These rules are evaluated once and trigger when their condition is met:

#### Basic Conditions
- Puzzle solve: `P1 SOLVE`
- Puzzle unlock: `P1 UNLOCK`
- Point threshold: `10 POINTS`
- Time since hunt start: `+1:30` (1 hour 30 minutes)

#### Logical Operators
```
# AND operator
P3 <= (P1 AND P2)

# OR operator
P3 <= (P1 OR P2)

# N of M condition
P4 <= 2 OF (P1, P2, P3)
```

### Multi-Use Rules

These rules can trigger multiple times based on intervals:

#### Time Intervals
```
# Every N minutes/hours
2 HINTS <= EVERY 30 MINUTES
5 POINTS <= EVERY 2 HOURS

# Intervals after events
2 HINTS <= EVERY 30 MINUTES AFTER P1 SOLVE
5 POINTS <= EVERY 1 HOUR AFTER +1:00

# Conditional intervals
2 HINTS <= EVERY 30 MINUTES IF 10 POINTS
```

{: .note }
When using both `AFTER` and `IF` in a multi-use rule, the `IF` condition must come after the `AFTER` clause. For example: `2 HINTS <= EVERY 30 MINUTES AFTER P1 SOLVE IF 10 POINTS` is valid, but `2 HINTS <= EVERY 30 MINUTES IF 10 POINTS AFTER P1 SOLVE` is not.

## Formal Grammar

The language follows this simplified grammar:

```
rule := unlockable "<=" condition

unlockable := puzzle_id | point_reward | hint_reward | "[" unlockable_list "]"
unlockable_list := unlockable ("," unlockable)*

puzzle_id := "P" hex_number
point_reward := number "POINTS"
hint_reward := number ["puzzle_id"] "HINTS"

condition := single_use_condition | multi_use_condition

single_use_condition := puzzle_solve | puzzle_id | puzzle_unlock | time_since_start | 
                       point_threshold | logical_expression
logical_expression := "(" condition ("AND"|"OR") condition ")" |
                     number "OF" "(" condition_list ")"

multi_use_condition := time_interval ["IF" single_use_condition]
time_interval := "EVERY" number ("MINUTES"|"HOURS") ["AFTER" point_in_time]
point_in_time := time_since_start | puzzle_solve | puzzle_unlock

puzzle_solve := puzzle_id "SOLVE"
puzzle_unlock := puzzle_id "UNLOCK"
time_since_start := "+" hours ":" minutes
point_threshold := number "POINTS"
```
