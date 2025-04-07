from setuptools import setup, find_packages
import io

with io.open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="django-audit-logger",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Django>=3.2",
        "psycopg2-binary>=2.9.3",
        "gunicorn>=20.1.0",
    ],
    author="Your Organization",
    author_email="admin@yourorganization.com",
    description="A Django middleware for logging requests and responses to PostgreSQL",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourorganization/django-audit-logger",
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
