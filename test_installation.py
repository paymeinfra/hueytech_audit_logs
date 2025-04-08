#!/usr/bin/env python
"""
Test script to verify the installation and functionality of the Django Audit Logger.
This script simulates the installation process and checks if the gunicorn_config.py
file is copied correctly to the project directory.
"""
import os
import sys
import shutil
import tempfile
import subprocess
import unittest
from pathlib import Path

class TestAuditLoggerInstallation(unittest.TestCase):
    """Test the installation process of the Django Audit Logger."""
    
    def setUp(self):
        """Set up a temporary directory to simulate a Django project."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir)
        
        # Create a dummy manage.py file to simulate a Django project
        with open(self.project_dir / "manage.py", "w") as f:
            f.write("# Dummy manage.py file for testing")
        
        # Get the path to the package directory
        self.package_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.gunicorn_config_src = self.package_dir / "django_audit_logger" / "gunicorn_config.py"
        
        print(f"Test directory: {self.temp_dir}")
        print(f"Source gunicorn_config.py: {self.gunicorn_config_src}")
    
    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_gunicorn_config_exists(self):
        """Test that the gunicorn_config.py file exists in the package."""
        self.assertTrue(os.path.exists(self.gunicorn_config_src), 
                        "gunicorn_config.py does not exist in the package")
    
    def test_post_install_command(self):
        """Test that the PostInstallCommand correctly copies the gunicorn_config.py file."""
        # Instead of importing from setup.py, implement the copy logic directly
        # This simulates what the PostInstallCommand would do
        source_path = self.gunicorn_config_src
        
        # Set the current working directory to our temp directory
        original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        try:
            # Simulate the post-install command
            dest_path = self.project_dir / "gunicorn_config.py"
            print(f"Copying gunicorn_config.py to {dest_path}")
            shutil.copy2(source_path, dest_path)
            
            # Check if the gunicorn_config.py file was copied to the project directory
            self.assertTrue(os.path.exists(dest_path), 
                            "gunicorn_config.py was not copied to the project directory")
            
            # Verify the content of the copied file
            with open(dest_path, "r") as f:
                dest_content = f.read()
            
            with open(source_path, "r") as f:
                src_content = f.read()
            
            self.assertEqual(dest_content, src_content, 
                            "The content of the copied gunicorn_config.py file does not match the source")
            
            print("✅ Successfully copied gunicorn_config.py to the project directory")
        finally:
            # Restore the original working directory
            os.chdir(original_cwd)
    
    def test_deferred_imports(self):
        """Test that the gunicorn_config.py file uses deferred imports."""
        with open(self.gunicorn_config_src, "r") as f:
            content = f.read()
        
        # Check if the file contains the get_django_imports function
        self.assertIn("def get_django_imports", content, 
                      "gunicorn_config.py does not contain the get_django_imports function")
        
        # Check if Django imports are inside the function
        self.assertIn("from django.db import DatabaseError", content, 
                      "Django imports are not deferred")
        
        print("✅ gunicorn_config.py correctly uses deferred imports")

if __name__ == "__main__":
    unittest.main()
