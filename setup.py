import os
from setuptools import setup, find_packages

__version__ = "1.1.0"


requirements_filepath = os.path.join(os.path.dirname(__name__), "requirements.txt")
with open(requirements_filepath) as fp:
    install_requires = fp.read()


def get_description():
    """
    Read full description from 'README.rst'
    """
    with open('README.rst', 'r', encoding='utf-8') as f:
        return f.read()


setup(
    name="Flask-COMBO-JSONAPI",
    version=__version__,
    description="Flask extension to create REST web api according to JSON:API 1.0 specification"
                " with Flask, Marshmallow and data provider of your choice (SQLAlchemy, MongoDB, ...)",
    long_description=get_description(),
    long_description_content_type='text/x-rst',
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
