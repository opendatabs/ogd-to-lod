#!/bin/bash
# Setup a new git worktree for working on an issue
# Usage: ./scripts/setup-worktree.sh <issue-number>

set -e

ISSUE=$1
MAIN_WORKTREE="$(cd "$(dirname "$0")/.." && pwd)"
PARENT_DIR="$(dirname "$MAIN_WORKTREE")"
WORKTREE_DIR="$PARENT_DIR/ogd-to-lod-issue-$ISSUE"

if [ -z "$ISSUE" ]; then
    echo "Usage: $0 <issue-number>"
    echo "Example: $0 12"
    exit 1
fi

# Check if worktree already exists
if [ -d "$WORKTREE_DIR" ]; then
    echo "Error: Worktree already exists at $WORKTREE_DIR"
    exit 1
fi

echo "Creating worktree for issue #$ISSUE..."
echo "  Location: $WORKTREE_DIR"
echo "  Branch: feature/issue-$ISSUE"

# Create worktree with new branch
git worktree add "$WORKTREE_DIR" -b "feature/issue-$ISSUE"

# Symlink .env if it exists
if [ -f "$MAIN_WORKTREE/.env" ]; then
    ln -s "$MAIN_WORKTREE/.env" "$WORKTREE_DIR/.env"
    echo "  Linked: .env"
fi

# Symlink .claude directory if it exists
if [ -d "$MAIN_WORKTREE/.claude" ]; then
    ln -s "$MAIN_WORKTREE/.claude" "$WORKTREE_DIR/.claude"
    echo "  Linked: .claude/"
fi

echo ""
echo "Worktree created successfully!"
echo ""
echo "Next steps:"
echo "  cd $WORKTREE_DIR"
echo "  # Open a new Claude Code session there"
echo ""
echo "When done, clean up with:"
echo "  git worktree remove $WORKTREE_DIR"