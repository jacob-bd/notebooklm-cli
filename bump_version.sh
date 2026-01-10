#!/bin/bash
# Version bump script for nlm
# Usage: ./bump_version.sh <new_version>
# Example: ./bump_version.sh 0.2.0

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <new_version>"
    echo "Example: $0 0.2.0"
    exit 1
fi

NEW_VERSION=$1

echo "Bumping version to $NEW_VERSION..."

# Update pyproject.toml
sed -i '' "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml

# Update __init__.py
sed -i '' "s/__version__ = \".*\"/__version__ = \"$NEW_VERSION\"/" src/nlm/__init__.py

echo "Updated files:"
grep "version" pyproject.toml | head -1
grep "__version__" src/nlm/__init__.py

echo ""
echo "To publish:"
echo "  git add pyproject.toml src/nlm/__init__.py"
echo "  git commit -m 'chore: bump version to $NEW_VERSION'"
echo "  git tag v$NEW_VERSION"
echo "  git push origin main --tags"
