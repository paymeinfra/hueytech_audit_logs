#!/bin/bash
# Script to build and upload the package to PyPI

set -e  # Exit immediately if a command exits with a non-zero status

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
REPO_URL="https://upload.pypi.org/legacy/"
REPO_NAME="PyPI"
DEFAULT_PACKAGE_NAME="django-gunicorn-audit-logs"

# Display usage information
function show_usage {
    echo "Usage: $0 [--test] [--version VERSION] [--name PACKAGE_NAME] [PACKAGE_NAME]"
    echo ""
    echo "Options:"
    echo "  --test             Upload to TestPyPI instead of production PyPI"
    echo "  --version VERSION  Set the package version (e.g., 0.1.1)"
    echo "  --name NAME        Set the package name (e.g., my-package)"
    echo "  PACKAGE_NAME       Set a custom package name (default: $DEFAULT_PACKAGE_NAME)"
    echo ""
    echo "Examples:"
    echo "  $0                                # Use default package name and version from setup.py"
    echo "  $0 --version 0.2.0                # Set version to 0.2.0"
    echo "  $0 --name my-package              # Set package name with flag"
    echo "  $0 --version 0.2.0 --name my-pkg  # Set both version and name with flags"
    echo "  $0 --test --version 0.2.0 --name my-pkg  # Test upload with flags"
    exit 1
}

# Parse arguments
VERSION=""
PACKAGE_NAME=""
USE_TEST_PYPI=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --test)
            USE_TEST_PYPI=true
            shift
            ;;
        --version)
            if [[ -z "$2" || "$2" == --* ]]; then
                echo -e "${RED}Error: --version requires a value${NC}"
                show_usage
            fi
            VERSION="$2"
            shift 2
            ;;
        --name)
            if [[ -z "$2" || "$2" == --* ]]; then
                echo -e "${RED}Error: --name requires a value${NC}"
                show_usage
            fi
            PACKAGE_NAME="$2"
            shift 2
            ;;
        --help|-h)
            show_usage
            ;;
        *)
            if [[ -z "$PACKAGE_NAME" ]]; then
                PACKAGE_NAME="$1"
            else
                echo -e "${RED}Error: Too many arguments${NC}"
                show_usage
            fi
            shift
            ;;
    esac
done

# Set repository based on flag
if [ "$USE_TEST_PYPI" = true ]; then
    REPO_URL="https://test.pypi.org/legacy/"
    REPO_NAME="TestPyPI"
fi

# Set default package name if not provided
if [ -z "$PACKAGE_NAME" ]; then
    PACKAGE_NAME=$DEFAULT_PACKAGE_NAME
fi

# Update package name if provided
if [ "$PACKAGE_NAME" != "$DEFAULT_PACKAGE_NAME" ]; then
    # Update the name in setup.py
    sed -i '' "s/name=\"[^\"]*\"/name=\"$PACKAGE_NAME\"/" setup.py
    echo -e "${YELLOW}Package name set to: $PACKAGE_NAME${NC}"
else
    # Check if setup.py has a different name
    SETUP_NAME=$(grep -m 1 "name=" setup.py | cut -d'"' -f2)
    if [ "$SETUP_NAME" != "$DEFAULT_PACKAGE_NAME" ]; then
        # Update setup.py to use the default name
        sed -i '' "s/name=\"[^\"]*\"/name=\"$DEFAULT_PACKAGE_NAME\"/" setup.py
        echo -e "${YELLOW}Package name set to default: $DEFAULT_PACKAGE_NAME${NC}"
    else
        echo -e "${YELLOW}Using default package name: $DEFAULT_PACKAGE_NAME${NC}"
    fi
fi

# Update version if provided
if [ -n "$VERSION" ]; then
    # Update the version in setup.py
    sed -i '' "s/version=\"[^\"]*\"/version=\"$VERSION\"/" setup.py
    echo -e "${YELLOW}Package version set to: $VERSION${NC}"
else
    # Use the default version from setup.py
    VERSION=$(grep -m 1 "version=" setup.py | cut -d'"' -f2)
    echo -e "${YELLOW}Using version from setup.py: $VERSION${NC}"
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
echo -e "${YELLOW}Ready to upload $PACKAGE_NAME v$VERSION to $REPO_NAME.${NC}"
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
echo -e "${GREEN}Package $PACKAGE_NAME v$VERSION has been uploaded to $REPO_NAME successfully!${NC}"

# Installation instructions
echo -e "${YELLOW}To install from $REPO_NAME, run:${NC}"
if [ "$REPO_NAME" == "TestPyPI" ]; then
    echo -e "pip install --index-url https://test.pypi.org/simple/ $PACKAGE_NAME==$VERSION"
else
    echo -e "pip install $PACKAGE_NAME==$VERSION"
fi

# Final notes
echo -e "${YELLOW}Don't forget to tag this release in git:${NC}"
echo -e "git tag -a v$VERSION -m 'version $VERSION'"
echo -e "git push origin v$VERSION"
