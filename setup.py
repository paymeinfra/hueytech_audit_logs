from setuptools import setup, find_packages
import io
import os
import sys
import shutil
from setuptools.command.install import install

with io.open("README.md", encoding="utf-8") as f:
    long_description = f.read()

class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        # Run the standard install
        install.run(self)
        
        # Get the gunicorn_config.py source path
        source_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                  'django_gunicorn_audit_logs', 'gunicorn_config.py')
        
        # Try to determine the project directory
        # First check if we're in a Django project
        try:
            # Get the current working directory or the directory from which pip was called
            project_dir = os.getcwd()
            
            # Check if this looks like a Django project
            if (os.path.exists(os.path.join(project_dir, 'manage.py')) or 
                any(f.endswith('wsgi.py') for f in os.listdir(project_dir) if os.path.isfile(os.path.join(project_dir, f)))):
                # Copy the file to the project directory
                dest_path = os.path.join(project_dir, 'gunicorn_config.py')
                print(f"Copying gunicorn_config.py to {dest_path}")
                shutil.copy2(source_path, dest_path)
            else:
                print("No Django project detected in the current directory. "
                      "You'll need to manually copy the gunicorn_config.py file.")
                print(f"Source path: {source_path}")
        except Exception as e:
            print(f"Error copying gunicorn_config.py: {e}")
            print("You'll need to manually copy the file from the package directory.")

setup(
    name="django-gunicorn-audit-logs",
    version="0.3.4",
    packages=find_packages(),
    install_requires=[
        "Django>=3.2",
        "psycopg2-binary>=2.9.3",
        "gunicorn>=20.1.0",
        "boto3>=1.26.0",
        "python-dotenv>=0.21.0",
    ],
    extras_require={
        'async': ["celery>=5.2.0"],
        'mongo': ["pymongo>=4.0.0", "dnspython>=2.0.0"],
    },
    cmdclass={
        'install': PostInstallCommand,
    },
    author="payme-alok",
    author_email="infra@paymeindia.in",
    description="A Django middleware for logging requests and responses to PostgreSQL with dual logging capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/paymeinfra/hueytech_audit_logs",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)
