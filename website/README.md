# PuzzleSpring Website

This repository contains both the landing page and documentation for the PuzzleSpring project.

## Project Structure

```
website/
├── docs/           # Jekyll documentation site
│   ├── _config.yml
│   ├── index.md
│   └── ...
└── public/         # Landing page and static assets
    ├── index.html
    ├── css/
    └── images/
```

## Local Development

To preview the full site locally:

1. Install Ruby and Bundler
2. Navigate to the website directory:
   ```bash
   cd website
   ```
3. Install dependencies:
   ```bash
   cd docs && bundle install && cd ..
   ```
4. Run the development server:
   ```bash
   chmod +x serve.sh  # First time only
   ./serve.sh
   ```
5. Visit `http://localhost:4000`

The site will automatically rebuild when you make changes to the documentation. Note that you'll need to restart the script if you make changes to the landing page files.

## Deployment

The site is automatically deployed to GitHub Pages when changes are pushed to the main branch. The GitHub Action will:
1. Build the Jekyll documentation site
2. Copy the landing page files into the built site
3. Deploy everything to GitHub Pages 