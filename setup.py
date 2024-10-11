from setuptools import find_packages, setup

description = """
Python package to manipulate Snowsight worksheets
 and easily apply Git versioning on it.
"""

with open("README.md", "r") as f:
    long_description = f.read()

with open("requirements.txt", "r") as f:
    requirements = f.read()

setup(
    name="sf_git",
    version="1.4.1",
    setup_requires=["setuptools_scm"],
    author="Thomas Dambrin",
    author_email="thomas.dambrin@gmail.com",
    url="https://github.com/tdambrin/sf_git",
    license="MIT",
    description=description,
    packages=find_packages(),
    install_requires=requirements,
    keywords=["python", "snowflake", "git"],
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Unix",
        "Operating System :: Microsoft :: Windows",
    ],
    # include_package_data: to install data from MANIFEST.in
    include_package_data=True,
    zip_safe=False,
    # all functions @cli.command() decorated in sf_git/cli.py
    entry_points={"console_scripts": ["sfgit = sf_git.cli:cli"]},
    scripts=[],
    long_description=long_description,
    long_description_content_type="text/markdown",
)
