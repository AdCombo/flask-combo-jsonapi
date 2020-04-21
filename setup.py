from setuptools import setup, find_packages


__version__ = "0.30.1"


setup(
    name="Flask-REST-JSONAPI",
    version=__version__,
    description="Flask extension to create REST web api according to JSONAPI 1.0 specification with Flask, Marshmallow \
                 and data provider of your choice (SQLAlchemy, MongoDB, ...)",
    url="https://github.com/miLibris/flask-rest-jsonapi",
    author="miLibris API Team",
    author_email="pf@milibris.net",
    license="MIT",
    classifiers=[
        "Framework :: Flask",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="web api rest jsonapi flask sqlalchemy marshmallow",
    packages=find_packages(exclude=["tests"]),
    zip_safe=False,
    platforms="any",
    install_requires=[
        "Flask>=1.0.1",
        "marshmallow==3.2.1",
        "marshmallow_jsonapi>=0.22.0",
        "apispec>=2.0.2",
        "sqlalchemy",
    ],
    # setup_requires=['pytest-runner'],
    tests_require=["pytest"],
    extras_require={"tests": "pytest", "docs": "sphinx"},
)
