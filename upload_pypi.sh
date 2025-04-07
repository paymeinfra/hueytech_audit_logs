#!/bin/bash
# Script to build and upload the package to PyPI

set -e  # Exit immediately if a command exits with a non-zero status

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default repository is the production PyPI
REPO_URL="https://upload.pypi.org/legacy/"
REPO_NAME="PyPI"

# Check if a test repository was specified
if [ "$1" == "--test" ]; then
    REPO_URL="https://test.pypi.org/legacy/"
    REPO_NAME="TestPyPI"
    shift
fi

# Check if a custom repository name was provided
if [ -n "$1" ]; then
    PACKAGE_NAME="$1"
    # Update the name in setup.py
    sed -i '' "s/name=\"django-audit-logger\"/name=\"$PACKAGE_NAME\"/" setup.py
    echo -e "${YELLOW}Package name set to: $PACKAGE_NAME${NC}"
else
    # Use the default name from setup.py
    PACKAGE_NAME=$(grep -m 1 "name=" setup.py | cut -d'"' -f2)
    echo -e "${YELLOW}Using package name from setup.py: $PACKAGE_NAME${NC}"
fi

# Clean up any previous builds
echo -e "${YELLOW}Cleaning up previous builds...${NC}"
rm -rf build/ dist/ *.egg-info/

# Make sure we have the latest versions of build tools
echo -e "${YELLOW}Upgrading build tools...${NC}"
pip install --upgrade pip setuptools wheel twine build

# Build the package
echo -e "${YELLOW}Building the package...${NC}"
python -m build

# Check the distribution files
echo -e "${YELLOW}Checking the distribution files...${NC}"
twine check dist/*

# Confirm upload
echo -e "${YELLOW}Ready to upload to $REPO_NAME.${NC}"
read -p "Do you want to continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Upload canceled.${NC}"
    exit 1
fi

# Upload to the repository
echo -e "${YELLOW}Uploading to $REPO_NAME...${NC}"
if [ "$REPO_NAME" == "TestPyPI" ]; then
    twine upload --repository-url $REPO_URL dist/*
else
    twine upload dist/*
fi

# Success message
echo -e "${GREEN}Package $PACKAGE_NAME has been uploaded to $REPO_NAME successfully!${NC}"

# Installation instructions
echo -e "${YELLOW}To install from $REPO_NAME, run:${NC}"
if [ "$REPO_NAME" == "TestPyPI" ]; then
    echo -e "pip install --index-url https://test.pypi.org/simple/ $PACKAGE_NAME"
else
    echo -e "pip install $PACKAGE_NAME"
fi

# Final notes
echo -e "${YELLOW}Don't forget to tag this release in git:${NC}"
VERSION=$(grep -m 1 "version=" setup.py | cut -d'"' -f2)
echo -e "git tag -a v$VERSION -m 'version $VERSION'"
echo -e "git push origin v$VERSION"
