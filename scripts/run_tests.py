#!/usr/bin/env python
"""
Test runner script for the Kizuna Restaurant Analytics project.
Provides easy commands to run different types of tests.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}\n")

    try:
        subprocess.run(command, check=True, capture_output=False)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False


def run_unit_tests():
    """Run unit tests"""
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/",
        "-v",
        "--tb=short",
        "--strict-markers",
    ]
    return run_command(command, "Unit Tests")


def run_integration_tests():
    """Run integration tests"""
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/integration/",
        "-v",
        "--tb=short",
        "--strict-markers",
    ]
    return run_command(command, "Integration Tests")


def run_all_tests():
    """Run all tests"""
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--strict-markers",
    ]
    return run_command(command, "All Tests")


def run_specific_test(test_path):
    """Run a specific test file or test function"""
    command = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"]
    return run_command(command, f"Specific Test: {test_path}")


def run_tests_with_coverage():
    """Run tests with coverage report"""
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "--cov=data_engineering",
        "--cov=apps",
        "--cov-report=html",
        "--cov-report=term-missing",
        "-v",
        "--tb=short",
    ]
    return run_command(command, "Tests with Coverage")


def run_tests_with_markers(marker):
    """Run tests with specific markers"""
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-m",
        marker,
        "-v",
        "--tb=short",
    ]
    return run_command(command, f"Tests with marker: {marker}")


def check_test_environment():
    """Check if the test environment is properly set up"""
    print("Checking test environment...")

    # Check if Django settings are available
    try:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.testing")
        import django

        django.setup()
        print("✅ Django test settings loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load Django test settings: {e}")
        return False

    # Check if required packages are installed
    required_packages = ["pytest", "pytest_django", "pandas", "openpyxl"]
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is available")
        except ImportError:
            print(f"❌ {package} is not available")
            return False

    return True


def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(
        description="Test runner for Kizuna Restaurant Analytics project"
    )

    parser.add_argument("--unit", action="store_true", help="Run unit tests only")

    parser.add_argument(
        "--integration", action="store_true", help="Run integration tests only"
    )

    parser.add_argument("--all", action="store_true", help="Run all tests")

    parser.add_argument(
        "--coverage", action="store_true", help="Run tests with coverage report"
    )

    parser.add_argument(
        "--marker", type=str, help="Run tests with specific marker (e.g., slow, e2e)"
    )

    parser.add_argument(
        "--test", type=str, help="Run a specific test file or test function"
    )

    parser.add_argument(
        "--check", action="store_true", help="Check test environment setup"
    )

    args = parser.parse_args()

    # Check environment first
    if not check_test_environment():
        print("\n❌ Test environment check failed. Please fix the issues above.")
        sys.exit(1)

    success = True

    if args.check:
        print("\n✅ Test environment is ready!")
        return

    if args.unit:
        success = run_unit_tests()
    elif args.integration:
        success = run_integration_tests()
    elif args.coverage:
        success = run_tests_with_coverage()
    elif args.marker:
        success = run_tests_with_markers(args.marker)
    elif args.test:
        success = run_specific_test(args.test)
    elif args.all:
        success = run_all_tests()
    else:
        # Default: run all tests
        success = run_all_tests()

    if success:
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
