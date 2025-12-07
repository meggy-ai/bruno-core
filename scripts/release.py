#!/usr/bin/env python3
"""
Release automation script for bruno-core.

Usage:
    python scripts/release.py [major|minor|patch]
"""

import re
import sys
import subprocess
from pathlib import Path
from datetime import datetime


def get_current_version():
    """Read current version from __version__.py"""
    version_file = Path("bruno_core/__version__.py")
    content = version_file.read_text()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)
    raise ValueError("Could not find version in __version__.py")


def bump_version(version: str, bump_type: str) -> str:
    """Bump version number."""
    major, minor, patch = map(int, version.split('.'))
    
    if bump_type == 'major':
        return f"{major + 1}.0.0"
    elif bump_type == 'minor':
        return f"{major}.{minor + 1}.0"
    elif bump_type == 'patch':
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def update_version_file(new_version: str):
    """Update __version__.py with new version."""
    version_file = Path("bruno_core/__version__.py")
    content = version_file.read_text()
    
    new_content = re.sub(
        r'__version__\s*=\s*["\'][^"\']+["\']',
        f'__version__ = "{new_version}"',
        content
    )
    
    version_file.write_text(new_content)
    print(f"✅ Updated {version_file} to version {new_version}")


def update_changelog(new_version: str):
    """Add new version section to CHANGELOG.md"""
    changelog = Path("CHANGELOG.md")
    content = changelog.read_text()
    
    today = datetime.now().strftime("%Y-%m-%d")
    new_section = f"""
## [{new_version}] - {today}

### Added
- 

### Changed
- 

### Fixed
- 

"""
    
    # Insert after the first heading
    lines = content.split('\n')
    insert_pos = next(i for i, line in enumerate(lines) if line.startswith('## ['))
    lines.insert(insert_pos, new_section)
    
    changelog.write_text('\n'.join(lines))
    print(f"✅ Updated CHANGELOG.md with version {new_version}")


def run_tests():
    """Run test suite."""
    print("🧪 Running tests...")
    result = subprocess.run(['pytest', 'tests/', '-v'], capture_output=True)
    if result.returncode != 0:
        print("❌ Tests failed!")
        print(result.stdout.decode())
        print(result.stderr.decode())
        return False
    print("✅ All tests passed")
    return True


def run_linting():
    """Run code quality checks."""
    print("🔍 Running linting...")
    
    checks = [
        (['black', '--check', 'bruno_core/', 'tests/'], "Black formatting"),
        (['isort', '--check-only', 'bruno_core/', 'tests/'], "Import sorting"),
        (['flake8', 'bruno_core/'], "Flake8 linting"),
    ]
    
    for cmd, name in checks:
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            print(f"❌ {name} failed!")
            print(result.stdout.decode())
            return False
        print(f"✅ {name} passed")
    
    return True


def git_commit_and_tag(version: str):
    """Commit changes and create git tag."""
    print(f"📦 Creating git commit and tag for v{version}...")
    
    # Stage changes
    subprocess.run(['git', 'add', 'bruno_core/__version__.py', 'CHANGELOG.md'])
    
    # Commit
    subprocess.run(['git', 'commit', '-m', f'chore: Release v{version}'])
    
    # Create tag
    subprocess.run(['git', 'tag', '-a', f'v{version}', '-m', f'Release v{version}'])
    
    print(f"✅ Created commit and tag v{version}")
    print("\n⚠️  Don't forget to push:")
    print(f"    git push origin main")
    print(f"    git push origin v{version}")


def main():
    """Main release process."""
    if len(sys.argv) != 2 or sys.argv[1] not in ['major', 'minor', 'patch']:
        print("Usage: python scripts/release.py [major|minor|patch]")
        sys.exit(1)
    
    bump_type = sys.argv[1]
    
    print("🚀 Bruno Core Release Process")
    print("=" * 50)
    
    # Get current version
    current_version = get_current_version()
    print(f"📌 Current version: {current_version}")
    
    # Calculate new version
    new_version = bump_version(current_version, bump_type)
    print(f"📈 New version: {new_version}")
    
    # Confirm
    response = input(f"\nProceed with release v{new_version}? [y/N]: ")
    if response.lower() != 'y':
        print("❌ Release cancelled")
        sys.exit(0)
    
    # Run checks
    if not run_tests():
        print("\n❌ Release aborted: tests failed")
        sys.exit(1)
    
    if not run_linting():
        print("\n❌ Release aborted: linting failed")
        sys.exit(1)
    
    # Update files
    update_version_file(new_version)
    update_changelog(new_version)
    
    # Git operations
    git_commit_and_tag(new_version)
    
    print("\n" + "=" * 50)
    print(f"✅ Release v{new_version} prepared successfully!")
    print("\n📝 Next steps:")
    print("1. Review the changes")
    print("2. Edit CHANGELOG.md to add details")
    print("3. Push to GitHub:")
    print(f"   git push origin main")
    print(f"   git push origin v{new_version}")
    print("4. Create GitHub release (will trigger PyPI publish)")


if __name__ == '__main__':
    main()
