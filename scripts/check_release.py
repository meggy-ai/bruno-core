#!/usr/bin/env python3
"""
Check if the package is ready for release.

Runs all quality checks and reports any issues.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    print(f"🔍 Checking {description}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"  ✅ {description} passed")
        return True, ""
    else:
        print(f"  ❌ {description} failed")
        return False, result.stdout + result.stderr


def check_file_exists(filepath: str) -> bool:
    """Check if a required file exists."""
    path = Path(filepath)
    exists = path.exists()
    
    if exists:
        print(f"  ✅ {filepath} exists")
    else:
        print(f"  ❌ {filepath} missing")
    
    return exists


def main():
    """Run all pre-release checks."""
    print("🚀 Bruno Core - Release Readiness Check")
    print("=" * 60)
    
    all_passed = True
    errors = []
    
    # Check required files
    print("\n📁 Checking required files...")
    required_files = [
        "setup.py",
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "bruno_core/__init__.py",
        "bruno_core/__version__.py",
    ]
    
    for filepath in required_files:
        if not check_file_exists(filepath):
            all_passed = False
            errors.append(f"Missing file: {filepath}")
    
    # Run tests
    print("\n🧪 Running tests...")
    passed, output = run_command(
        ['pytest', 'tests/', '-v', '--tb=short'],
        "Test suite"
    )
    if not passed:
        all_passed = False
        errors.append("Tests failed")
        print(output)
    
    # Check test coverage
    print("\n📊 Checking test coverage...")
    passed, output = run_command(
        ['pytest', 'tests/', '--cov=bruno_core', '--cov-report=term-missing', '--cov-fail-under=80'],
        "Test coverage (80%+)"
    )
    if not passed:
        all_passed = False
        errors.append("Test coverage below 80%")
    
    # Check formatting
    print("\n🎨 Checking code formatting...")
    passed, output = run_command(
        ['black', '--check', 'bruno_core/', 'tests/', 'examples/'],
        "Black formatting"
    )
    if not passed:
        all_passed = False
        errors.append("Code formatting issues (run: black bruno_core/ tests/ examples/)")
    
    # Check import sorting
    print("\n📦 Checking import sorting...")
    passed, output = run_command(
        ['isort', '--check-only', 'bruno_core/', 'tests/', 'examples/'],
        "Import sorting"
    )
    if not passed:
        all_passed = False
        errors.append("Import sorting issues (run: isort bruno_core/ tests/ examples/)")
    
    # Check linting
    print("\n🔍 Checking code quality...")
    passed, output = run_command(
        ['flake8', 'bruno_core/', '--max-line-length=100'],
        "Flake8 linting"
    )
    if not passed:
        all_passed = False
        errors.append("Linting issues")
    
    # Check type hints
    print("\n🏷️  Checking type hints...")
    passed, output = run_command(
        ['mypy', 'bruno_core/', '--ignore-missing-imports'],
        "Type checking"
    )
    if not passed:
        all_passed = False
        errors.append("Type checking issues")
    
    # Check if documentation builds
    print("\n📚 Checking documentation...")
    passed, output = run_command(
        ['mkdocs', 'build', '--strict'],
        "Documentation build"
    )
    if not passed:
        all_passed = False
        errors.append("Documentation build failed")
    
    # Final report
    print("\n" + "=" * 60)
    
    if all_passed:
        print("✅ ALL CHECKS PASSED!")
        print("\n🎉 Package is ready for release!")
        print("\nNext steps:")
        print("  1. Run: python scripts/release.py [major|minor|patch]")
        print("  2. Update CHANGELOG.md with release notes")
        print("  3. Push to GitHub and create release")
        return 0
    else:
        print("❌ SOME CHECKS FAILED!")
        print("\n⚠️  Please fix the following issues:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        print("\nRun this script again after fixing issues.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
