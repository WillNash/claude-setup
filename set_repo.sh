#!/bin/bash

# 1. Define the repository you want to mount
TARGET_REPO=${1:-"$(pwd)/worldrugby-scrm-mobile"}
echo $TARGET_REPO


# 3. Safety Check: Ensure the target directory actually exists
if [ ! -d "$TARGET_REPO" ]; then
    echo "❌ Error: The directory '$TARGET_REPO' does not exist."
    exit 1
fi

# Convert the repo path to an absolute path (Docker requires absolute paths for volume mounts)
TARGET_REPO_ABS=$(cd "$TARGET_REPO" && pwd)
echo $TARGET_REPO_ABS