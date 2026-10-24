#!/bin/bash
# Runs after Claude compacts the conversation.
# Prints the files that have changed, so Claude remembers them.

cd "$CLAUDE_PROJECT_DIR" || exit 0

CHANGELOG_FILE=".claude/compact-changelog.txt"
CHANGES=$(git diff --name-only HEAD)
echo "$CHANGES" >> "$CHANGELOG_FILE"

[ -z "$CHANGES" ] && echo "No changes detected." || echo "Changes detected and logged to $CHANGELOG_FILE."

echo "Compact summary hook completed."
exit 0;