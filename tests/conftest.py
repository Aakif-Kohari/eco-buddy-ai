import sys
import os

# Add the project root directory to sys.path so that 'tests' package can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

pytest_plugins = ["tests.fixtures.conftest"]
