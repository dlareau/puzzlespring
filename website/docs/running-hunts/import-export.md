---
layout: default
title: Import/Export
parent: Running Hunts
nav_order: 4
---

# Import/Export

PuzzleSpring provides robust functionality for exporting and importing hunts, allowing you to back up hunt data, transfer hunts between instances, or create templates for future hunts.

## Exporting a Hunt

### From the Staff Interface

1. Navigate to the Staff > Hunts page
2. Find the hunt you want to export
3. Click the export button for the hunt you want to export
4. Choose whether to include activity data (submissions, hints, etc.)
5. The hunt will be exported as a `.phe` (PuzzleHunt Export) file

### What Gets Exported

A hunt export includes:

- Hunt configuration and settings
- All puzzles and their attributes
- Puzzle files and solution files
- Hunt template files
- Canned hints and responses
- Team ranking rules
- Pre-puzzles associated with the hunt

If you choose to include activity data, the export will also contain:
- Teams and their members
- Puzzle statuses (unlocks and solves)
- Hint requests and responses
- Submissions
- Updates and announcements

## Importing a Hunt

### From the Staff Interface

1. Navigate to the Staff > Hunts page
2. Click the "Import Hunt" button
3. Select a `.phe` file to upload
4. Choose whether to include activity data
5. Click "Import"
6. The import will be processed in the background

### Import Considerations

- The import process runs in the background and may take several minutes for large hunts
- User references in activity data will be linked to existing users if they exist
- File paths and references are automatically adjusted to work in the new instance

## Using Export/Import for Templates

You can use the export/import functionality to create template hunts:

1. Create a hunt with your desired structure and settings
2. Add template puzzles with placeholder content
3. Configure the unlocking rules and other settings
4. Export the hunt without activity data
5. Import this template whenever you need to create a new hunt with similar structure

## Troubleshooting Import Issues

If you encounter issues during import:

1. Check the server logs for detailed error messages
2. Ensure the `.phe` file is valid and not corrupted
3. Verify that your instance has enough disk space for the imported files

{: .warning }
> Importing a hunt with activity data will create duplicate teams if teams with the same names already exist. Use this option with caution.

## Add Pre-PuzzleSpring Hunts to Archive

PuzzleSpring allows you to add information about hunts that were run before you started using the platform. These display-only hunts appear in the archive but don't have playable puzzles.

### Adding a Display-Only Hunt

1. Navigate to the Django Admin interface at `/admin/`
2. Go to the "Display only hunts" section under Puzzlehunt
3. Click "Add Display Only Hunt"
4. Fill in the following information:
   - **Name**: The name of the hunt
   - **Display start date**: When the hunt started
   - **Display end date**: When the hunt ended
   - **Num teams**: The number of teams that participated
   - **Num puzzles**: The number of puzzles the hunt had
5. Click "Save"

The hunt will now appear in the archive alongside your regular PuzzleSpring hunts, but without playable content.
