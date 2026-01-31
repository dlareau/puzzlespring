---
layout: default
title: Puzzle Content Creation
parent: Getting Started
nav_order: 5
---

# Puzzle Content Creation

PuzzleSpring provides a flexible puzzle rendering system that supports multiple content formats.

## Puzzle File Management

The staff interface allows you to upload multiple files for each puzzle. After expanding the file list for a puzzle, click the "Upload File" button to upload a new file.

If you upload a zip file, the contents of the zip file will be extracted and all files contained in the zip file will be added to the puzzle. At the moment this is the only way to create a directory structure within the puzzle files. If the file is not a zip file, it will be added to the puzzle as a single file.

{: .note }
At the moment, new files cannot have the same name as an existing file. If you try to upload a file with the same name as an existing file, you will get an error. Either delete the existing file or use the "Replace File" button to replace the existing file.

Among the files you have uploaded, you can set the "main file" for a puzzle. This is the file that will be displayed in the puzzle page according to the puzzle type logic described below.

## Puzzle Types

PuzzleSpring supports three different types of puzzles, ranging from simple to complex:

1. **PDF Puzzle** - A PDF file that is displayed directly in the puzzle page.
2. **HTML Puzzle** - A fully custom HTML page that is displayed in the puzzle page.
3. **Template Puzzle** - A puzzle that is rendered using a Django template.

## PDF Puzzles

PDF puzzles are the simplest type of puzzle. They are a PDF file that is displayed directly in the puzzle page. This will automatically be done if the "main file" for a puzzle is a PDF.

## HTML Puzzles

HTML puzzles are a fully custom HTML page that is displayed on the puzzle page below the answer submission form. This type of puzzle is more flexible than a PDF puzzle, but less flexible than a template puzzle. This will be done if the "main file" for a puzzle is a file with a `.html` extension.

When using an HTML page for a puzzle, it is recommended to use relative links for images and other resources. This allows you to do rough prototyping on your local machine before uploading to the server.

## Template Puzzles

Template puzzles are the most complex but also the most flexible type of puzzle. They are rendered using a Django template that has access to the puzzle data. This will be done if the "main file" for a puzzle is a file with a `.tmpl` extension. 

The template file is entirely yours to customize, however that also means there isn't any content included by default. This means you are responsible for which template your puzzle inherits from, and all other parts of a normal puzzle page such as the answer submission form, links to hints, and updates. Consider looking the existing templates for inspiration.

The template is rendered with the following context:

- `puzzle`: The puzzle object.
- `team`: The team object that represents the team working on the puzzle.
- `solved`: A boolean indicating whether the puzzle has been solved by the team.
- `form`: The django form object used for submitting answers to the puzzle, this can be used to help render your own submission form.
- `submissions`: A list of submissions made by the team for the puzzle.
- `updates`: A list of updates related to the puzzle.



