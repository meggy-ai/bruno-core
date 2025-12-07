#!/usr/bin/env python3
"""
Setup script for development environment.

Installs all dependencies and sets up pre-commit hooks.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str):
    """Run a command and report result."""
    print(f"🔧 {description}...")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print(f"  ✅ {description} complete")
    else:
        print(f"  ❌ {description} failed")
        sys.exit(1)


def main():
    """Setup development environment."""
    print("🚀 Bruno Core - Development Setup")
    print("=" * 60)
    
    # Check Python version
    print(f"\n🐍 Python version: {sys.version}")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    
    # Install package in editable mode with all extras
    run_command(
        [sys.executable, '-m', 'pip', 'install', '-e', '.[dev,test,docs]'],
        "Installing bruno-core with dev dependencies"
    )
    
    # Install additional dev tools
    run_command(
        [sys.executable, '-m', 'pip', 'install', 'pre-commit', 'twine', 'build'],
        "Installing additional development tools"
    )
    
    # Setup pre-commit hooks
    if Path('.git').exists():
        run_command(
            ['pre-commit', 'install'],
            "Setting up pre-commit hooks"
        )
    else:
        print("  ⚠️  Not a git repository, skipping pre-commit setup")
    
    print("\n" + "=" * 60)
    print("✅ Development environment setup complete!")
    print("\n📝 Next steps:")
    print("  1. Read CONTRIBUTING.md for guidelines")
    print("  2. Run tests: pytest")
    print("  3. Check code quality: python scripts/check_release.py")
    print("  4. Build docs: mkdocs serve")


if __name__ == '__main__':
    main()
