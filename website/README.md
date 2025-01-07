# PuzzleSpring Website

This repository contains both the landing page and documentation for the PuzzleSpring project.

## Project Structure

```
website/
├── docs/ # Jekyll documentation site
│ ├── config.yml
│ ├── index.md
│ └── ...
└── public/ # Landing page and static assets
├── index.html
├── css/
└── images/
```

## Local Development

### Documentation Site

To preview the full site locally (including both landing page and documentation):

1. Install Ruby and Bundler
2. Navigate to the docs directory:
   ```bash
   cd website/docs
   ```
3. Install dependencies:
   ```bash
   bundle install
   ```
4. Create site directory and copy landing page:
   ```bash
   mkdir -p _site && cp -r ../public/* _site/
   ```
5. Start the Jekyll server:
   ```bash
   bundle exec jekyll serve --baseurl /docs --destination _site/docs
   ```
6. Visit `http://localhost:4000` for the landing page
7. Visit `http://localhost:4000/docs` for the documentation

### Landing Page Only

To preview just the landing page:

1. Navigate to the public directory:
   ```bash
   cd website/public
   ```
2. Start a local server (e.g., using Python):
   ```bash
   python -m http.server 4000
   ```
3. Visit `http://localhost:4000`

## Deployment

The site is automatically deployed to GitHub Pages when changes are pushed to the main branch. The GitHub Action will:
1. Build the Jekyll documentation site
2. Copy the landing page files into the built site
3. Deploy everything to GitHub Pages 