---
layout: default
title: Info Pages
parent: Customization
nav_order: 3
---

# Info Pages

PuzzleSpring supports two types of informational pages: hunt-specific info pages and site-wide info pages.

## Hunt Information Page

Each hunt can have its own information page that provides details such as an FAQ and other relevant information. This page is generally accessible before the hunt begins.

### Setting Up a Hunt Info Page

1. Navigate to the hunt in Django Admin
2. Below the template and CSS file section, find the Info Page file option
3. Upload a Django template file for the hunt's general information page

The info page can use Django template syntax for dynamic content.

## Site-Wide Info Pages

Beyond hunt-specific settings, you can create site-wide Info Pages that appear in the top navigation bar. These are useful for resources, FAQs, or other static content.

### Creating an Info Page

1. Navigate to the Django Admin interface at `/admin/`
2. Go to the "Info pages" section under Puzzlehunt
3. Click "Add info page"
4. Fill in the page details:
   - **URL**: The path for the page (e.g., `/rules/` will be accessible at `/info/rules/`)
   - **Title**: The page title shown in the navigation bar
   - **Content**: The HTML content of the page (can include Django template tags)
   - **Registration required**: Check if the page should only be visible to logged-in users
5. Click "Save"

The new info page will immediately appear in the navigation bar and be accessible to users.

### Info Page Features

- **Custom URLs**: Define the path where the page will be accessible
- **Navigation Integration**: Pages automatically appear in the navigation bar
- **Template Support**: Content can include Django template tags for dynamic rendering
- **Access Control**: Optionally require users to be logged in to view the page

### Common Use Cases

- **Rules Page**: Explain the rules and format of your puzzle hunts
- **About Page**: Information about your organization
- **Resources Page**: Links to helpful tools or references
- **FAQ Page**: Answers to frequently asked questions
- **Contact Page**: How to reach the organizing team
