import os
from setuptools import setup, find_packages

__version__ = "1.0.5"


requirements_filepath = os.path.join(os.path.dirname(__name__), "requirements.txt")
with open(requirements_filepath) as fp:
    install_requires = fp.read()

setup(
    name="Flask-COMBO-JSONAPI",
    version=__version__,
    description="Flask extension to create REST web api according to JSONAPI 1.0 specification"
                " with Flask, Marshmallow and data provider of your choice (SQLAlchemy, MongoDB, ...)",
    url="https://github.com/AdCombo/flask-combo-jsonapi",
    author="AdCombo Team",
    author_email="roman@adcombo.com",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Flask",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Internet",
    ],
    keywords="web api rest jsonapi flask sqlalchemy marshmallow",
    packages=find_packages(exclude=["tests"]),
    zip_safe=False,
    platforms="any",
    install_requires=install_requires,
    tests_require=["pytest"],
    extras_require={"tests": "pytest", "docs": "sphinx"},
)
