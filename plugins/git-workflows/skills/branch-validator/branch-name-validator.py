#!/usr/bin/env python3
"""
Branch Name Validator

Validates branch naming conventions according to common patterns:
- feature/description
- fix/description
- chore/description
- refactor/description
- docs/description
- test/description
- hotfix/description

Input: branch name (command-line argument)
Output: validation result (valid/invalid with reason)
Exit codes:
  0: Valid branch name
  1: Invalid branch name
  2: Invalid usage
"""

import re
import sys
from typing import Optional, Tuple


VALID_PREFIXES = {
    "feature",
    "fix",
    "bugfix",
    "chore",
    "refactor",
    "docs",
    "test",
    "hotfix",
    "release",
    "perf",
    "style",
    "ci",
    "build",
}

BRANCH_PATTERN = re.compile(r"^([a-z]+)/([a-z0-9\-_]+)$")


def validate_branch_name(branch_name: str) -> Tuple[bool, Optional[str]]:
    if not branch_name:
        return False, "Branch name cannot be empty"

    branch_name = branch_name.replace("refs/heads/", "")

    protected_branches = {"main", "master", "develop", "staging", "production"}
    if branch_name in protected_branches:
        return True, None

    match = BRANCH_PATTERN.match(branch_name)
    if not match:
        return False, (
            "Invalid format. Expected: prefix/description\n"
            f"  - Prefix: {', '.join(sorted(VALID_PREFIXES))}\n"
            "  - Description: lowercase alphanumeric, hyphens, underscores\n"
            "  - Example: feature/add-user-authentication"
        )

    prefix = match.group(1)
    description = match.group(2)

    if prefix not in VALID_PREFIXES:
        return False, f"Invalid prefix '{prefix}'. Valid prefixes: {', '.join(sorted(VALID_PREFIXES))}"

    if len(description) < 3:
        return False, "Description must be at least 3 characters"

    if len(description) > 50:
        return False, "Description must be at most 50 characters"

    if "--" in description or "__" in description:
        return False, "Description cannot contain consecutive hyphens or underscores"

    if description.startswith("-") or description.startswith("_"):
        return False, "Description cannot start with hyphen or underscore"

    if description.endswith("-") or description.endswith("_"):
        return False, "Description cannot end with hyphen or underscore"

    return True, None


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: branch-name-validator.py <branch-name>", file=sys.stderr)
        raise SystemExit(2)

    branch_name = sys.argv[1]
    is_valid, error_msg = validate_branch_name(branch_name)

    if is_valid:
        print(f"Valid branch name: {branch_name}")
        raise SystemExit(0)

    print(f"Invalid branch name: {branch_name}", file=sys.stderr)
    if error_msg:
        print(f"  {error_msg}", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
