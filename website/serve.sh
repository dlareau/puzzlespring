#!/bin/bash

# Initial setup
rm -rf docs/_site
mkdir -p docs/_site
ln -s ../../public/images docs/_site/images
ln -s ../../public/index.html docs/_site/index.html

# Change to docs directory for Jekyll commands
cd docs

# Start Jekyll in watch mode (build only, no server)
bundle exec jekyll build \
  --baseurl /docs \
  --destination _site/docs \
  --watch \
  --incremental &

# Wait for Jekyll to start
sleep 2

# Change back to website directory for Python server
cd ..

# Start Python server for the built site
python3 -m http.server 4000 --directory docs/_site
