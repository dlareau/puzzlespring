---
layout: default
title: Templates
parent: Technical Reference
nav_order: 3
---

# Templates

This document describes the templates used in the PuzzleSpring application.

## Root

### <u>access_error.html</u>

_Description:_ Displays an error message when a user tries to access a resource they don't have permission to view.


_Extends:_ info_base.html


_Context Variables:_

- `reason`: The reason for access denial ('hunt', 'team', 'puzzle', or 'hint')


_Template Blocks:_

- `title`: Sets page title to "Not Available"
- `content`: Displays the appropriate error message based on the reason



### <u>archive.html</u>

_Description:_ Displays a list of all past puzzle hunts in reverse chronological order with links to their pages.


_Extends:_ info_base.html


_Context Variables:_

- `hunts`: List of all past Hunt objects with their associated data


_Template Blocks:_

- `content`: Displays a table of past hunts with links to their various pages



### <u>base.html</u>

_Description:_ The base template that all other templates extend from. Provides the basic HTML structure, meta tags, and common includes.


_Template Blocks:_

- `title_meta_elements`: Block containing all meta elements for the page title and social sharing
- `extra_meta_elements`: Block for additional meta elements
- `favicon`: Block for the favicon
- `base_includes`: Block for including base CSS/JS files
- `bulma_includes`: Block for including Bulma-specific CSS/JS files
- `includes`: Block for template-specific includes
- `extra_head`: Block for additional head content
- `content_wrapper`: Block containing the main content wrapper structure
- `content`: Block for the main content of the page
- `footer`: Block containing the footer content
- `extra_body`: Block for additional body content



### <u>hint_unlock_plan_formset.html</u>

_Description:_ Form for configuring hint unlock plans in the staff interface.


_Context Variables:_

- `hunt`: The current Hunt object
- `formset`: Django formset for hint unlock plan configuration



### <u>hunt_base.html</u>

_Description:_ Base template for hunt-related pages. Provides hunt-specific styling and real-time updates via SSE.


_Extends:_ base.html


_Context Variables:_

- `tmpl_hunt`: The current hunt object
- `team`: The current team object (optional)
- `title`: Optional page title override


_Template Blocks:_

- `title_meta_elements`: Overrides title meta elements to include hunt name
- `base_includes`: Adds hunt-specific CSS and custom hunt CSS if available
- `bulma_includes`: Removes default Bulma includes
- `content_wrapper`: Adds SSE-based live updates for hunt content
- `content`: Block for hunt-specific content
- `footer`: Removes default footer



### <u>hunt_info_base.html</u>

_Description:_ Base template for hunt information pages with a centered content layout.


_Extends:_ info_base.html


_Template Blocks:_

- `title`: Sets page title to "Hunt Details"
- `content_wrapper`: Provides a centered content layout with specific width
- `content`: Block for hunt information content



### <u>hunt_info_non_template.html</u>

_Description:_ Displays hunt information page for non-template hunts.


_Extends:_ hunt_info_base.html


_Context Variables:_

- `hunt`: The current Hunt object


_Template Blocks:_

- `content`: The main content area displaying hunt details and rules



### <u>hunt_non_template.html</u>

_Description:_ Displays a simple list view of all puzzles in a hunt with their solve status and answers.


_Extends:_ hunt_base.html


_Context Variables:_

- `hunt`: The current Hunt object
- `team`: The current Team object
- `puzzles`: List of all Puzzle objects in the hunt
- `solved`: List of puzzles that have been solved by the team


_Template Blocks:_

- `content_wrapper`: Displays hunt title, team name, and puzzle list table



### <u>index.html</u>

_Description:_ The home page of the puzzlehunt website.


_Extends:_ info_base.html


_Context Variables:_

- `curr_hunt`: The current hunt object


_Template Blocks:_

- `content`: The content of the page



### <u>info_base.html</u>

_Description:_ Base template for informational pages. Provides a centered content layout with configurable width.


_Extends:_ base.html


_Context Variables:_

- `info_size`: Controls the width of the content ('full-width', 'wide', 'narrow', 'narrow_padded', or default)


_Template Blocks:_

- `base_includes`: Adds info-specific CSS
- `content_wrapper`: Provides a centered content layout with configurable width
- `content`: Block for page-specific content



### <u>leaderboard.html</u>

_Description:_ Displays a leaderboard of teams for a specific hunt with customizable ranking rules.


_Extends:_ info_base.html


_Context Variables:_

- `hunt`: The Hunt object being displayed
- `ruleset`: List of LeaderboardRule objects defining the columns and ranking rules
- `team_data`: List of Team objects with their ranking data


_Template Blocks:_

- `title_meta_elements`: Sets page title to include hunt name
- `content_wrapper`: Sets wide layout for the leaderboard
- `content`: Displays the leaderboard table with team rankings



### <u>notification_detail.html</u>

_Description:_ Displays and manages user notification preferences and subscriptions.


_Extends:_ allauth/layouts/manage.html


_Context Variables:_

- `form`: Form for adding new notification subscriptions


_Template Blocks:_

- `content`: Displays current subscriptions and a form to add new ones



### <u>notification_table.html</u>

_Description:_ Displays a table of notification subscriptions with platform, hunt, event types, and management controls.


_Context Variables:_

- `subscriptions`: List of NotificationSubscription objects
- `event_type_choices`: List of tuples containing event type choices



### <u>partial_header.html</u>

_Description:_ Partial template for displaying message container if messages exist.


_Context Variables:_

- `messages`: List of messages to display



### <u>prepuzzle_base.html</u>

_Description:_ Base template for prepuzzle pages. Provides answer checking functionality.


_Extends:_ base.html


_Context Variables:_

- `puzzle`: The current prepuzzle object


_Template Blocks:_

- `title_meta_elements`: Sets page title to puzzle name
- `base_includes`: Adds JavaScript for answer checking
- `content`: Block for prepuzzle-specific content



### <u>prepuzzle_infobox.html</u>

_Description:_ Displays the information box for a prepuzzle, including title and answer submission form.


_Context Variables:_

- `puzzle`: The current prepuzzle object
- `form`: Form for submitting prepuzzle answers



### <u>prepuzzle_non_template.html</u>

_Description:_ Displays a non-template prepuzzle, supporting HTML and PDF file types.


_Extends:_ puzzle_base.html


_Context Variables:_

- `puzzle`: The current prepuzzle object


_Template Blocks:_

- `content`: The main content area displaying the puzzle content



### <u>puzzle_base.html</u>

_Description:_ Base template for puzzle pages. Provides puzzle-specific layout and info box.


_Extends:_ hunt_base.html


_Context Variables:_

- `puzzle`: The current puzzle object
- `is_prepuzzle`: Template tag result indicating if this is a prepuzzle


_Template Blocks:_

- `title_meta_elements`: Sets page title to puzzle name
- `content_wrapper`: Adds puzzle info box section
- `content`: Block for puzzle-specific content



### <u>puzzle_hints.html</u>

_Description:_ Displays hint request form and previous hints for a puzzle with real-time updates via SSE.


_Extends:_ hunt_base.html


_Context Variables:_

- `puzzle`: The puzzle object hints are being requested for
- `team`: The current team object
- `hints`: List of previous Hint objects for this puzzle
- `status`: PuzzleStatus object for this team and puzzle


_Template Blocks:_

- `title_meta_elements`: Sets page title to puzzle name with "Hints" suffix
- `content_wrapper`: Displays hint request form and previous hints



### <u>puzzle_infobox.html</u>

_Description:_ Displays puzzle information box with answer submission, stats, hints access, and updates.


_Context Variables:_

- `puzzle`: The current Puzzle object
- `team`: The current Team object
- `form`: Form for submitting puzzle answers
- `updates`: List of Update objects for this puzzle



### <u>puzzle_non_template.html</u>

_Description:_ Displays a non-template puzzle, supporting HTML and PDF file types.


_Extends:_ puzzle_base.html


_Context Variables:_

- `puzzle`: The current puzzle object


_Template Blocks:_

- `content`: The main content area displaying the puzzle content



### <u>puzzle_solution.html</u>

_Description:_ Displays the solution for a puzzle, supporting both HTML and PDF formats.


_Extends:_ hunt_base.html


_Context Variables:_

- `puzzle`: The puzzle object containing the solution file


_Template Blocks:_

- `title_meta_elements`: Sets page title to puzzle name with "Solution" suffix
- `content`: Displays the puzzle solution content based on file type



### <u>staff_charts.html</u>

_Description:_ Displays various charts and statistics about puzzle solves, submissions, and hints using Google Charts.


_Extends:_ staff_hunt_base.html


_Context Variables:_

- `chart_rows`: List of earliest solve data for each puzzle
- `chart_solves_data`: Data for puzzle solve status chart
- `chart_submissions_data`: Data for puzzle submissions chart
- `chart_hints_data`: Data for hints per puzzle chart
- `chart_submissions_by_time_data`: Data for submissions over time chart
- `chart_solves_by_time_data`: Data for solves over time chart


_Template Blocks:_

- `extra_head`: Adds Google Charts loader
- `staff_content`: Displays charts and earliest solves table



### <u>staff_feed.html</u>

_Description:_ Displays a real-time feed of hunt events with filtering by team, puzzle, and event type.


_Extends:_ staff_hunt_base.html


_Context Variables:_

- `hunt`: The current Hunt object
- `puzzle_tags`: List of selected puzzle IDs for filtering
- `team_tags`: List of selected team IDs for filtering
- `types`: List of event type options
- `display_checkboxes`: List of currently selected event types
- `num_items`: Number of items to display per page
- `feed_items`: Paginated list of feed events


_Template Blocks:_

- `staff_content`: Displays feed filters and event items with real-time updates



### <u>staff_hints.html</u>

_Description:_ Displays staff interface for managing hint requests with filtering and real-time updates.


_Extends:_ staff_hunt_base.html


_Context Variables:_

- `hunt`: The current Hunt object
- `hints`: Paginated list of Hint objects


_Template Blocks:_

- `staff_content`: Displays hint management interface with filters and hint list



### <u>staff_hunt_base.html</u>

_Description:_ Base template for staff hunt management pages. Provides a collapsible sidebar with navigation and hunt selection.


_Extends:_ base.html


_Context Variables:_

- `hunt`: The current Hunt object being managed
- `tmpl_all_hunts`: List of all Hunt objects for the hunt selector


_Template Blocks:_

- `includes`: Adds staff-specific CSS and JS files
- `content_wrapper`: Provides the main layout with collapsible sidebar
- `staff_content`: Block for staff page-specific content
- `footer`: Removes default footer



### <u>staff_hunt_config.html</u>

_Description:_ Provides an interface for editing hunt configuration using the Ace editor.


_Extends:_ staff_hunt_base.html


_Context Variables:_

- `hunt`: The current Hunt object
- `config_text`: Current hunt configuration text


_Template Blocks:_

- `staff_content`: Displays configuration editor and puzzle list
- `extra_body`: Adds JavaScript for Ace editor initialization and keyboard shortcuts



### <u>staff_hunt_puzzles.html</u>

_Description:_ Staff interface for managing and viewing puzzle statistics and files.


_Extends:_ staff_hunt_base.html


_Context Variables:_

- `puzzles`: List of all Puzzle objects in the hunt
- `num_teams`: Total number of teams in the hunt


_Template Blocks:_

- `staff_content`: The main content area displaying puzzle management interface



### <u>staff_hunt_template.html</u>

_Description:_ Staff interface for editing and previewing hunt templates.


_Extends:_ staff_hunt_base.html


_Context Variables:_

- `hunt`: The current Hunt object
- `template_text`: The current template text content
- `puzzle_numbers`: List of puzzle numbers for preview functionality


_Template Blocks:_

- `staff_content`: The main content area with template editor and preview functionality
- `extra_body`: Additional JavaScript for Ace editor initialization



### <u>staff_hunts.html</u>

_Description:_ Staff interface for managing and viewing all hunts.


_Extends:_ staff_hunt_base.html


_Context Variables:_

- `hunts`: List of all Hunt objects


_Template Blocks:_

- `staff_content`: The main content area displaying hunt management interface



### <u>staff_progress.html</u>

_Description:_ Displays a real-time progress board showing teams' puzzle solving status, hints, and submissions using DataTables.


_Extends:_ staff_hunt_base.html


_Context Variables:_

- `hunt`: The current Hunt object
- `puzzles`: List of Puzzle objects in the hunt
- `info_columns`: List of additional information columns to display
- `page_size`: Optional pagination size for the table


_Template Blocks:_

- `includes`: Adds DataTables and other required CSS/JS files
- `staff_content`: Displays the progress board with team and puzzle data



### <u>staff_search.html</u>

_Description:_ Provides a search interface for staff to find users and teams.


_Extends:_ staff_hunt_base.html


_Context Variables:_

- `hunt`: The current Hunt object
- `query`: The current search query


_Template Blocks:_

- `staff_content`: Displays search input and results area



### <u>team_detail.html</u>

_Description:_ Displays team details and management interface. Shows team members, join code, and team management options.


_Extends:_ allauth/layouts/manage.html


_Context Variables:_

- `current_team`: The user's current team
- `teams`: List of user's previous teams
- `team`: The team being viewed
- `form`: Team management form


_Template Blocks:_

- `content`: Main content block containing team information and management interface



### <u>team_registration.html</u>

_Description:_ Provides interface for creating a new team or joining an existing team.


_Extends:_ info_base.html


_Context Variables:_

- `form`: Form for creating a new team
- `current_hunt`: The current hunt
- `errors`: Error messages from join team attempts


_Template Blocks:_

- `title`: Sets page title to "Team Registration"
- `content_wrapper`: Sets wide layout for the registration form
- `content`: Displays team creation form and join team interface



### <u>updates.html</u>

_Description:_ Displays a list of hunt updates and announcements in chronological order.


_Extends:_ info_base.html


_Context Variables:_

- `updates`: List of Update objects containing announcements


_Template Blocks:_

- `title`: Sets page title to "Updates"
- `content`: Displays updates in a card-based layout



### <u>user_detail.html</u>

_Description:_ Displays and manages user profile details.


_Extends:_ allauth/layouts/manage.html


_Context Variables:_

- `user_form`: Form for editing user details


_Template Blocks:_

- `content`: Displays user details form



## Components

### <u>_bulma_expanded_text_input.html</u>

_Description:_ Renders an expanded text input field with Bulma styling and error handling.


_Context Variables:_

- `field`: The form field to render



### <u>_bulma_rounded_checkbox.html</u>

_Description:_ Renders a rounded checkbox switch with Bulma styling.


_Context Variables:_

- `field`: The form field to render as a checkbox switch



### <u>_feed_item.html</u>

_Description:_ Displays a single feed item with icon, text, and timestamp in a styled box.


_Context Variables:_

- `item`: The FeedEvent object to display
- `compact`: Boolean indicating if the item should be displayed in compact mode



### <u>_message_container.html</u>

_Description:_ Displays Django messages as Bulma toast notifications.


_Context Variables:_

- `messages`: List of Django message objects to display



### <u>_navbar.html</u>

_Description:_ Main navigation bar with user menu, team selection, and site navigation.


_Context Variables:_

- `debug`: Boolean indicating if in debug mode
- `user`: The current User object
- `current_hunt_team`: The current Team object for the user in the current hunt
- `team_list`: List of Team objects the user belongs to
- `is_staff`: Boolean indicating if the user is staff



### <u>_paginator.html</u>

_Description:_ Displays a pagination navigation bar with page numbers and ellipsis.


_Context Variables:_

- `page_info`: Django Page object containing pagination information



## Partials

### <u>_hint_row.html</u>

_Description:_ Displays a single hint row with request details and response status.


_Context Variables:_

- `hint`: The Hint object to display
- `staff`: Boolean indicating if viewing as staff
- `puzzle`: The current Puzzle object



### <u>_message_update_user_form.html</u>

_Description:_ Displays user form updates with messages and user display information.


_Context Variables:_

- `user`: The current User object
- `user_form`: Form for updating user information



### <u>_notification_active_toggle.html</u>

_Description:_ Toggle switch for activating/deactivating notification subscriptions.


_Context Variables:_

- `subscription`: The NotificationSubscription object to toggle



### <u>_notification_table_and_form.html</u>

_Description:_ Displays notification subscriptions table and subscription form.


_Context Variables:_

- `subscriptions`: List of NotificationSubscription objects
- `form`: Form for creating new notification subscriptions



### <u>_puzzle_public_response.html</u>

_Description:_ Displays the response status for a puzzle submission with appropriate styling.


_Context Variables:_

- `submission`: The PuzzleSubmission object containing response information



### <u>_search_results.html</u>

_Description:_ Displays search results for users and teams in the staff interface.


_Context Variables:_

- `query`: The search query string
- `users`: List of User objects matching the search
- `teams`: List of Team objects matching the search



### <u>_staff_file_list.html</u>

_Description:_ Displays a list of files associated with a puzzle or hunt with management controls.


_Context Variables:_

- `parent`: The parent object (Puzzle or Hunt) owning the files
- `parent_type`: String indicating the type of parent ('puzzle', 'solution', or 'hunt')



### <u>_staff_hint_modal.html</u>

_Description:_ Modal dialog for staff to view and respond to hint requests.


_Context Variables:_

- `hint`: The Hint object being responded to
- `previous_hints`: List of previous Hint objects for this team and puzzle
- `previous_submissions`: List of previous PuzzleSubmission objects for this team and puzzle
- `form`: Form for submitting hint response



### <u>_submission_table.html</u>

_Description:_ Displays a table of previous puzzle submissions with real-time updates.


_Context Variables:_

- `puzzle`: The current Puzzle object
- `submissions`: List of PuzzleSubmission objects for this puzzle



### <u>_team_name_and_form.html</u>

_Description:_ Displays team name and form for editing team information.


_Context Variables:_

- `team`: The current Team object
- `form`: Form for editing team information


