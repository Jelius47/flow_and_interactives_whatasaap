#!/bin/bash

# Stage all changes
git add .

# Ask for commit message
read -p "Enter commit message: " commit_msg

# Commit with the message
git commit -m "$commit_msg"

# Ask to push or not
read -p "Do you want to push to the remote repository? (y/n): " should_push

if [[ "$should_push" =~ ^[Yy]$ ]]; then
  # Get current branch
  branch=$(git rev-parse --abbrev-ref HEAD)
  git push origin "$branch"
else
  echo "Changes committed but not pushed."
fi
