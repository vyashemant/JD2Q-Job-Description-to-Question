import pytest
import sys

def main():
    """Run all tests for JD2Q."""
    print("Initializing JD2Q Test Suite...")
    # Run pytest and capture results
    exit_code = pytest.main(["-v", "tests"])
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
