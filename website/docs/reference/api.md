---
layout: default
title: API
parent: Reference
nav_order: 2
---

# API Reference

This document describes the available API endpoints in PuzzleSpring.

## Base

### <u>view</u>

_Description:_ Provide a redirect on any GET request.

_URL Patterns:_
- `hunt/<hunt:hunt>/`
- `puzzle/<str:pk>/`

## Hunt Views

### <u>hunt_info</u>

_Description:_ No description available.

_URL Patterns:_
- `hunt/<hunt:hunt>/info/`

_Parameters:_
- `hunt`: any

### <u>hunt_leaderboard</u>

_Description:_ No description available.

_URL Patterns:_
- `hunt/<hunt:hunt>/leaderboard/`

_Parameters:_
- `hunt`: any

### <u>hunt_prepuzzle</u>

_Description:_ A simple view that locates the correct prepuzzle for a hunt and redirects there if it exists.

_URL Patterns:_
- `hunt/<hunt:hunt>/prepuzzle/`

_Parameters:_
- `hunt`: any

### <u>hunt_updates</u>

_Description:_ No description available.

_URL Patterns:_
- `hunt/<hunt:hunt>/updates/`

_Parameters:_
- `hunt`: any

### <u>hunt_view</u>

_Description:_ The main view to render hunt templates. Does various permission checks to determine the set
of puzzles to display and then renders the string in the hunt's "template" field to HTML.

_URL Patterns:_
- `hunt/<hunt:hunt>/view/`

_Parameters:_
- `hunt`: any

### <u>prepuzzle_check</u>

_Description:_ No description available.

_URL Patterns:_
- `prepuzzle/<int:pk>/check/`

_Parameters:_
- `pk`: any

### <u>prepuzzle_submit</u>

_Description:_ No description available.

_URL Patterns:_
- `prepuzzle/<int:pk>/submit/`

_Parameters:_
- `pk`: any

### <u>prepuzzle_view</u>

_Description:_ No description available.

_URL Patterns:_
- `prepuzzle/<int:pk>/`
- `prepuzzle/<int:pk>/view/`

_Parameters:_
- `pk`: any

### <u>protected_static</u>

_Description:_ A view to serve protected static content. If the permission check passes, the file is served via X-Sendfile.

_URL Patterns:_
- `hunt/<str:pk>/view/<path:file_path>`
- `protected/<str:base>/<str:pk>/<path:file_path>`
- `protected/trusted/<str:base>/<str:pk>/<path:file_path>`
- `puzzle/<str:pk>/solution/<path:file_path>`
- `puzzle/<str:pk>/view/<path:file_path>`

_Parameters:_
- `pk`: any
- `file_path`: any
- `base`: any
- `add_prefix`: any

### <u>puzzle_hints_submit</u>

_Description:_ No description available.

_URL Patterns:_
- `puzzle/<str:pk>/hints/submit/`

_Parameters:_
- `pk`: any

### <u>puzzle_hints_use_canned</u>

_Description:_ No description available.

_URL Patterns:_
- `puzzle/<str:pk>/hints/canned/`

_Parameters:_
- `pk`: any

### <u>puzzle_hints_view</u>

_Description:_ No description available.

_URL Patterns:_
- `puzzle/<str:pk>/hints/view/`

_Parameters:_
- `pk`: any

### <u>puzzle_solution</u>

_Description:_ No description available.

_URL Patterns:_
- `puzzle/<str:pk>/solution/`

_Parameters:_
- `pk`: any

### <u>puzzle_submit</u>

_Description:_ No description available.

_URL Patterns:_
- `puzzle/<str:pk>/submit/`

_Parameters:_
- `pk`: any

### <u>puzzle_view</u>

_Description:_ No description available.

_URL Patterns:_
- `puzzle/<str:pk>/view/`

_Parameters:_
- `pk`: any

## Info Views

### <u>archive</u>

_Description:_ A view to render the list of previous hunts, will show any hunt that is 'public' 

_URL Patterns:_
- `archive/`

### <u>index</u>

_Description:_ Main landing page view, mostly static except for hunt info 

_URL Patterns:_
- ``

### <u>notification_delete</u>

_Description:_ No description available.

_URL Patterns:_
- `notifications/<int:pk>/delete/`

_Parameters:_
- `pk`: any

### <u>notification_toggle</u>

_Description:_ No description available.

_URL Patterns:_
- `notifications/<int:pk>/toggle/`

_Parameters:_
- `pk`: any

### <u>notification_view</u>

_Description:_ No description available.

_URL Patterns:_
- `notifications/`

### <u>team_create</u>

_Description:_ The view that handles team registration. Mostly deals with creating the team object from the post request.

_URL Patterns:_
- `team/create/`

### <u>team_join</u>

_Description:_ No description available.

_URL Patterns:_
- `team/<str:pk>/join/`
- `team/join/`

_Parameters:_
- `pk`: any

### <u>team_leave</u>

_Description:_ No description available.

_URL Patterns:_
- `team/<str:pk>/leave/`

_Parameters:_
- `pk`: any

### <u>team_update</u>

_Description:_ No description available.

_URL Patterns:_
- `team/<str:pk>/update/`

_Parameters:_
- `pk`: any

### <u>team_view</u>

_Description:_ No description available.

_URL Patterns:_
- `team/<str:pk>/view/`

_Parameters:_
- `pk`: any

### <u>user_detail_view</u>

_Description:_ No description available.

_URL Patterns:_
- `user/detail`

## Staff Views

### <u>charts</u>

_Description:_ View function to display charts for the current hunt.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/charts/`

_Parameters:_
- `hunt`: any

### <u>config_tester</u>

_Description:_ View for testing hunt configuration without creating actual team data.
Simulates puzzle unlocks based on provided solved states and time.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/config-tester/`

_Parameters:_
- `hunt`: any

### <u>download_emails</u>

_Description:_ Generate and download a CSV file with participant emails from non-playtester teams.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/download-emails/`

_Parameters:_
- `hunt`: any

### <u>export_hunt</u>

_Description:_ No description available.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/export/`

_Parameters:_
- `hunt`: any

### <u>feed</u>

_Description:_ No description available.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/feed/`

_Parameters:_
- `hunt`: any

### <u>file_delete</u>

_Description:_ Delete a file.

This view function deletes a specified file by its primary key (pk).

Args:
    parent_type (str): The type of the parent (e.g., 'solution', 'hunt').
    pk (int): The primary key of the file to be deleted.

_URL Patterns:_
- `staff/<str:parent_type>/file/<str:pk>/delete/`

_Parameters:_
- `parent_type`: any
- `pk`: any

### <u>file_delete_all</u>

_Description:_ Delete all files of a certain type for a parent object.

This view function deletes all files of a specified parent_type type for a parent object.

Args:
    parent_type (str): The type of the parent (e.g., 'solution', 'hunt').
    pk (int): The primary key of the parent object whose files are to be deleted.

_URL Patterns:_
- `staff/<str:parent_type>/<str:pk>/files/delete_all/`

_Parameters:_
- `parent_type`: any
- `pk`: any

### <u>file_download</u>

_Description:_ Download a file.

This view function allows a staff member to download a specified file by its primary key (pk).

Args:
    parent_type (str): The type of the parent (e.g., 'solution', 'hunt').
    pk (int): The primary key of the file to be downloaded.

_URL Patterns:_
- `staff/<str:parent_type>/file/<str:pk>/download/`

_Parameters:_
- `parent_type`: any
- `pk`: any

### <u>file_editor</u>

_Description:_ Main file editor page with three-panel selector and Ace editor.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/file-editor/`

_Parameters:_
- `hunt`: any

### <u>file_editor_file_list</u>

_Description:_ HTMX endpoint returning file select dropdown for a given puzzle or hunt.

_URL Patterns:_
- `staff/file-editor/file-list/`

### <u>file_editor_load_content</u>

_Description:_ HTMX endpoint returning the editor partial with file content.

_URL Patterns:_
- `staff/file-editor/load-content/`

### <u>file_editor_puzzle_list</u>

_Description:_ HTMX endpoint returning puzzle select dropdown for a given hunt.

_URL Patterns:_
- `staff/file-editor/puzzle-list/`

### <u>file_replace</u>

_Description:_ Replace a file with a new upload.

This view function replaces a specified file with a new uploaded file.

Args:
    parent_type (str): The type of the parent (e.g., 'solution', 'hunt').
    pk (int): The primary key of the file to be replaced.

_URL Patterns:_
- `staff/<str:parent_type>/file/<str:pk>/replace/`

_Parameters:_
- `parent_type`: any
- `pk`: any

### <u>file_save_content</u>

_Description:_ Save edited content back to file.

_URL Patterns:_
- `staff/file/<str:parent_type>/<int:pk>/save/`

_Parameters:_
- `parent_type`: any
- `pk`: any

### <u>file_set_main</u>

_Description:_ Set a file as the main file for its parent object.

This view function sets a specified file as the main file for its parent object.
The type of main file is determined by the parent_type parameter.

Args:
    parent_type (str): The type of the parent (e.g., 'solution', 'hunt').
    pk (int): The primary key of the file to be set as main.

_URL Patterns:_
- `staff/<str:parent_type>/file/<str:pk>/set_main/`

_Parameters:_
- `parent_type`: any
- `pk`: any

### <u>file_upload</u>

_Description:_ Upload one or more new files.

This view function uploads one or more files and associates them with a parent object.
It can handle both single file uploads and multiple file uploads.

Args:
    parent_type (str): The type of the parent (e.g., 'solution', 'hunt').
    pk (int): The primary key of the parent object to which the files will be associated.

_URL Patterns:_
- `staff/<str:parent_type>/<str:pk>/files/upload/`

_Parameters:_
- `parent_type`: any
- `pk`: any

### <u>get_modal</u>

_Description:_ Get the modal for a hint.

This view function gets the modal a hint by its primary key (pk). For use by htmx requests.

Args:
    pk (int): The primary key of the hint for the modal.

_URL Patterns:_
- `staff/hint/<int:pk>/get_modal/`

_Parameters:_
- `pk`: any

### <u>hints_claim</u>

_Description:_ Claim a hint for the current user.

This view function allows a staff member to claim a hint by its primary key (pk).

Args:
    pk (int): The primary key of the hint to be claimed.

_URL Patterns:_
- `staff/hint/<int:pk>/claim/`

_Parameters:_
- `pk`: any

### <u>hints_refund</u>

_Description:_ Refund a hint.

This view function allows a staff member to refund a hint by its primary key (pk).

Args:
    pk (int): The primary key of the hint to be refunded.

_URL Patterns:_
- `staff/hint/<int:pk>/refund/`

_Parameters:_
- `pk`: any

### <u>hints_release</u>

_Description:_ Release a claimed hint.

This view function allows a staff member to release a previously claimed hint by its primary key (pk).

Args:
    pk (int): The primary key of the hint to be released.

_URL Patterns:_
- `staff/hint/<int:pk>/release/`

_Parameters:_
- `pk`: any

### <u>hints_respond</u>

_Description:_ Respond to a hint request.

This view function allows a staff member to respond to a hint request by its primary key (pk).
The response is taken from the POST data. If the 'response' key is not present in the POST data,
a SuspiciousOperation exception is raised. The responded hint is then rendered in the '_hint_row.html'
partial template.

Args:
    pk (int): The primary key of the hint to be responded to.

_URL Patterns:_
- `staff/hint/<int:pk>/respond/`

_Parameters:_
- `pk`: any

### <u>hints_view</u>

_Description:_ View function to display hints for the current hunt.

This view fetches hints based on optional filters provided via GET parameters.
The hints are paginated and rendered in the 'staff_hints.html' template.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/hints/`

_Parameters:_
- `hunt`: any

### <u>hunt_config</u>

_Description:_ Render or update the hunt configuration page.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/config/`

_Parameters:_
- `hunt`: any

### <u>hunt_puzzles</u>

_Description:_ View function to display puzzles for the current hunt.

This view fetches puzzles for a given hunt.
The puzzles are then rendered in the 'staff_hunt_puzzles.html' template.

Args:
    hunt (Hunt): The hunt instance for which to display puzzles

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/puzzles/`

_Parameters:_
- `hunt`: any

### <u>hunt_reset</u>

_Description:_ No description available.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/reset/`

_Parameters:_
- `hunt`: any

### <u>hunt_set_current</u>

_Description:_ Set a hunt as the current hunt.

This view function sets the specified hunt as the current hunt and saves it.
The updated list of hunts is then rendered in the 'staff_hunts.html' template.

Args:
    hunt (Hunt): The hunt to be set as the current hunt.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/set_current/`

_Parameters:_
- `hunt`: any

### <u>hunt_template</u>

_Description:_ No description available.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/template/`

_Parameters:_
- `hunt`: any

### <u>import_hunt</u>

_Description:_ Import a hunt from a zip file.

This view accepts a zip file upload and queues it for background processing.
The zip file should have been created by the export_hunt view.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/import/`

_Parameters:_
- `hunt`: any

### <u>participant_info</u>

_Description:_ View function to display participant information for the current hunt.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/participant_info/`

_Parameters:_
- `hunt`: any

### <u>preview_template</u>

_Description:_ No description available.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/template/preview/`

_Parameters:_
- `hunt`: any

### <u>progress</u>

_Description:_ View function to display the progress of teams in the current hunt.

Args:
    request (HttpRequest): The HTTP request object.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/progress/`

_Parameters:_
- `hunt`: any

### <u>progress_data</u>

_Description:_ API endpoint to return progress data for DataTables consumption.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/progress_data/`

_Parameters:_
- `hunt`: any

### <u>search</u>

_Description:_ View function for searching users and teams.

This view allows staff members to search for users and teams by name/email.
Results are returned via HTMX for dynamic updates.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/search/`

_Parameters:_
- `hunt`: any

### <u>staff_base</u>

_Description:_ View function for the staff dashboard/index page.

_URL Patterns:_
- `staff/`

### <u>view_hunts</u>

_Description:_ View the list of hunts.

This view function retrieves all hunts ordered by start date with the current hunt first.
The hunts are then rendered in the 'staff_hunts.html' template.

_URL Patterns:_
- `staff/hunt/<hunt-fallback:hunt>/hunts/`

_Parameters:_
- `hunt`: any

## Views

### <u>events</u>

_Description:_ No description available.

_URL Patterns:_
- `sse/staff/`
- `sse/team/<str:pk>/`

### <u>flatpage</u>

_Description:_ Public interface to the flat page view.

Models: `flatpages.flatpages`
Templates: Uses the template defined by the ``template_name`` field,
    or :template:`flatpages/default.html` if template_name is not defined.
Context:
    flatpage
        `flatpages.flatpages` object

_URL Patterns:_
- `info/<path:url>`

_Parameters:_
- `url`: any

### <u>view</u>

_Description:_ No description available.

_URL Patterns:_
- `password_reset/`
- `password_reset/done/`
- `reset/<uidb64>/<token>`
- `reset/done/`

_Parameters:_
- `self`: any
