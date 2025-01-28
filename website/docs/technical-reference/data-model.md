---
layout: default
title: Data Model
parent: Technical Reference
nav_order: 2
---

# Data Model

This document describes the data models used in the PuzzleSpring application.

## CannedHint Model

A pre-written hint that can be revealed to teams

Fields:
- `id` (AutoField): No description available
- `puzzle` (ForeignKey): The puzzle this canned hint belongs to
- `text` (TextField): The text of the hint
- `order` (IntegerField): Order in which this hint should be shown (lower numbers first)

## DisplayOnlyHunt Model

Model for the display only hunt, only to be shown on the archive page 

Fields:
- `id` (AutoField): No description available
- `name` (CharField): The name of the hunt as the public will see it
- `display_start_date` (DateTimeField): The date/time at which a hunt will become visible to registered users
- `display_end_date` (DateTimeField): The date/time at which a hunt will be archived and available to the public
- `num_teams` (IntegerField): The number of teams that were registered for this hunt
- `num_puzzles` (IntegerField): The number of puzzles this hunt had

## Event Model

Event(id, timestamp, type, related_data, related_object_id, user, hunt, team, puzzle)

Fields:
- `id` (AutoField): No description available
- `timestamp` (DateTimeField): The time of the event
- `type` (CharField): The type of event
- `related_data` (CharField): No description available
- `related_object_id` (CharField): No description available
- `user` (ForeignKey): The user associated with this event
- `hunt` (ForeignKey): The hunt associated with this event
- `team` (ForeignKey): The team associated with this event, if applicable
- `puzzle` (ForeignKey): The puzzle associated with this event, if applicable

## FlatPageProxyObject Model

FlatPageProxyObject(id, url, title, content, enable_comments, template_name, registration_required)

Fields:
- `id` (AutoField): No description available
- `url` (CharField): No description available
- `title` (CharField): No description available
- `content` (TextField): No description available
- `enable_comments` (BooleanField): No description available
- `template_name` (CharField): Example: “flatpages/contact_page.html”. If this isn’t provided, the system will use “flatpages/default.html”.
- `registration_required` (BooleanField): If this is checked, only logged-in users will be able to view the page.
- `sites` (ManyToManyField): No description available

## Hint Model

A class to represent a hint to a puzzle 

Fields:
- `id` (AutoField): No description available
- `puzzle` (ForeignKey): The puzzle that this hint is related to
- `team` (ForeignKey): The team that requested the hint
- `request` (TextField): The text of the request for the hint
- `request_time` (DateTimeField): Hint request time
- `response` (TextField): The text of the response to the hint request
- `response_time` (DateTimeField): Hint response time
- `last_modified_time` (DateTimeField): Last time of modification
- `responder` (ForeignKey): Staff member that has claimed the hint.
- `refunded` (BooleanField): Whether or not the hint was refunded
- `from_puzzle_pool` (BooleanField): Whether this hint was drawn from the puzzle-specific pool
- `canned_hint` (ForeignKey): If this was a canned hint, which one

## Hunt Model

Base class for a hunt. Contains basic details about a puzzlehunt. 

Fields:
- `id` (AutoField): No description available
- `name` (CharField): The name of the hunt as the public will see it
- `team_size_limit` (IntegerField): No description available
- `start_date` (DateTimeField): The date/time at which a hunt will become visible to registered users
- `end_date` (DateTimeField): The date/time at which a hunt will be archived and available to the public
- `display_start_date` (DateTimeField): The start date/time displayed to users
- `display_end_date` (DateTimeField): The end date/time displayed to users
- `location` (CharField): Starting location of the puzzlehunt
- `is_current_hunt` (BooleanField): No description available
- `template_file` (FileField): No description available
- `info_page_file` (FileField): No description available
- `hint_lockout` (IntegerField): Time (in minutes) teams must wait before a hint can be used on a newly unlocked puzzle
- `css_file` (ForeignKey): No description available
- `config` (TextField): Configuration for puzzle, point and hint unlocking rules
- `hint_pool_type` (CharField): Which hint pools are available in this hunt
- `canned_hint_policy` (CharField): How canned hints interact with custom hints
- `hint_pool_allocation` (CharField): How hints are allocated between puzzle and global pools when both exist

## HuntFile Model

HuntFile(id, file, parent)

Fields:
- `id` (AutoField): No description available
- `file` (FileField): No description available
- `parent` (ForeignKey): No description available

## NotificationPlatform Model

A platform that can be used to send notifications (Discord, Email, etc.)

Fields:
- `id` (AutoField): No description available
- `type` (CharField): The type of notification platform
- `name` (CharField): A friendly name for this platform configuration
- `enabled` (BooleanField): Whether this platform is currently enabled
- `config` (JSONField): Platform-specific configuration (API keys, URLs, etc.)

## NotificationSubscription Model

A user's subscription to notifications for specific event types

Fields:
- `id` (AutoField): No description available
- `user` (ForeignKey): The user who owns this subscription
- `platform` (ForeignKey): The platform to send notifications through
- `hunt` (ForeignKey): Optional: limit notifications to a specific hunt
- `event_types` (CharField): Comma-separated list of event types to notify on
- `destination` (CharField): Platform-specific destination (webhook URL, email, channel ID, etc.)
- `active` (BooleanField): Whether this subscription is currently active
- `created_at` (DateTimeField): No description available
- `updated_at` (DateTimeField): No description available

## Prepuzzle Model

A class representing a pre-puzzle within a hunt 

Fields:
- `id` (AutoField): No description available
- `name` (CharField): The name of the puzzle as it will be seen by hunt participants
- `released` (BooleanField): No description available
- `hunt` (OneToOneField): The hunt that this puzzle is a part of, leave blank for no associated hunt.
- `answer` (CharField): The answer to the puzzle, not case sensitive
- `response_string` (TextField): Data returned to the webpage for use upon solving.
- `allow_spaces` (BooleanField): Allow spaces in the answer submissions
- `case_sensitive` (BooleanField): Check for case in answer submissions
- `allow_non_alphanumeric` (BooleanField): Allow for full unicode in answer submissions (rather than just A-Z and 0-9)
- `main_file` (ForeignKey): No description available

## PrepuzzleFile Model

PrepuzzleFile(id, file, parent)

Fields:
- `id` (AutoField): No description available
- `file` (FileField): No description available
- `parent` (ForeignKey): No description available

## Puzzle Model

A class representing a puzzle within a hunt 

Fields:
- `id` (CharField): A 3-8 character hex string that uniquely identifies the puzzle
- `hunt` (ForeignKey): The hunt that this puzzle is a part of
- `name` (CharField): The name of the puzzle as it will be seen by hunt participants
- `order_number` (IntegerField): The number of the puzzle within the hunt, for sorting purposes
- `answer` (CharField): The answer to the puzzle.
- `type` (CharField): The type of puzzle
- `extra_data` (CharField): A misc. field for any extra data to be stored with the puzzle.
- `allow_spaces` (BooleanField): Allow spaces in the answer submissions
- `case_sensitive` (BooleanField): Check for case in answer submissions
- `allow_non_alphanumeric` (BooleanField): Allow for full unicode in answer submissions (rather than just A-Z and 0-9)
- `main_file` (ForeignKey): No description available
- `main_solution_file` (ForeignKey): No description available

## PuzzleFile Model

PuzzleFile(id, file, parent)

Fields:
- `id` (AutoField): No description available
- `file` (FileField): No description available
- `parent` (ForeignKey): No description available

## PuzzleStatus Model

A class representing the status of a puzzle for a team 

Fields:
- `id` (AutoField): No description available
- `puzzle` (ForeignKey): The puzzle this status is for
- `team` (ForeignKey): The team that this puzzle status for
- `unlock_time` (DateTimeField): The time this puzzle was unlocked for this team
- `solve_time` (DateTimeField): The time this puzzle was solved for this team
- `num_available_hints` (IntegerField): Number of puzzle-specific hints available
- `num_total_hints_earned` (IntegerField): The total number of puzzle-specific hints this puzzle/team pair has earned

## Response Model

A class to represent an automated response regex 

Fields:
- `id` (AutoField): No description available
- `puzzle` (ForeignKey): The puzzle that this automated response is related to
- `regex` (CharField): The python-style regex that will be checked against the user's response
- `text` (CharField): The text to use in the submission response if the regex matched

## SolutionFile Model

SolutionFile(id, file, parent)

Fields:
- `id` (AutoField): No description available
- `file` (FileField): No description available
- `parent` (ForeignKey): No description available

## Submission Model

A class representing a submission to a given puzzle from a given team 

Fields:
- `id` (AutoField): No description available
- `team` (ForeignKey): The team that made the submission
- `submission_time` (DateTimeField): No description available
- `submission_text` (CharField): No description available
- `response_text` (CharField): Response to the given answer.
- `puzzle` (ForeignKey): The puzzle that this submission is in response to
- `modified_time` (DateTimeField): Last date/time of response modification
- `user` (ForeignKey): The user who created the submission

## Team Model

A class representing a team within a hunt 

Fields:
- `id` (AutoField): No description available
- `name` (CharField): The team name as it will be shown to hunt participants
- `hunt` (ForeignKey): The hunt that the team is a part of
- `is_local` (BooleanField): Is this team a majority CMU users?
- `join_code` (CharField): The 8 character random alphanumeric password needed for a user to join a team
- `playtester` (BooleanField): A boolean to indicate if the team is a playtest team and will get early access
- `playtest_start_date` (DateTimeField): The date/time at which a hunt will become available to the playtesters
- `playtest_end_date` (DateTimeField): The date/time at which a hunt will no longer be available to playtesters
- `num_available_hints` (IntegerField): The number of hints the team currently has available to use
- `num_total_hints_earned` (IntegerField): The total number of hints this team has earned through config rules
- `points` (IntegerField): The total number of points this team has earned through config rules
- `puzzle_statuses` (ManyToManyField): The statuses of puzzles the team has unlocked
- `members` (ManyToManyField): Members of this team

## Team_members Model

Team_members(id, team, user)

Fields:
- `id` (AutoField): No description available
- `team` (ForeignKey): No description available
- `user` (ForeignKey): No description available

## TeamRankingRule Model

A class to represent the rules used to rank teams 

Fields:
- `id` (AutoField): No description available
- `hunt` (ForeignKey): The hunt that this ranking rule refers to
- `rule_type` (CharField): The type of ranking rule
- `rule_order` (IntegerField): The order in which the rule is applied
- `visible` (BooleanField): Is this rule visible on the leaderboard?

## Update Model

A class to represent puzzle/hunt updates 

Fields:
- `id` (AutoField): No description available
- `hunt` (ForeignKey): The hunt that update is part of
- `puzzle` (ForeignKey): The puzzle this update relates to (leave blank for hunt updates)
- `text` (TextField): The text of the update announcement.
- `time` (DateTimeField): The time the update was announced

## User Model

User(id, password, last_login, is_superuser, first_name, last_name, is_staff, is_active, date_joined, email, display_name)

Fields:
- `id` (AutoField): No description available
- `password` (CharField): No description available
- `last_login` (DateTimeField): No description available
- `is_superuser` (BooleanField): Designates that this user has all permissions without explicitly assigning them.
- `first_name` (CharField): No description available
- `last_name` (CharField): No description available
- `is_staff` (BooleanField): Designates whether the user can log into this admin site.
- `is_active` (BooleanField): Designates whether this user should be treated as active. Unselect this instead of deleting accounts.
- `date_joined` (DateTimeField): No description available
- `email` (CharField): No description available
- `display_name` (CharField): No description available
- `groups` (ManyToManyField): The groups this user belongs to. A user will get all permissions granted to each of their groups.
- `user_permissions` (ManyToManyField): Specific permissions for this user.

## User_groups Model

User_groups(id, user, group)

Fields:
- `id` (AutoField): No description available
- `user` (ForeignKey): No description available
- `group` (ForeignKey): No description available

## User_user_permissions Model

User_user_permissions(id, user, permission)

Fields:
- `id` (AutoField): No description available
- `user` (ForeignKey): No description available
- `permission` (ForeignKey): No description available
