
import os
try:
    from setuptools import setup
except ImportError as e:
    from distutils.core import setup

DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(DIR, "docs", "README.txt"), "r") as f:
    long_description = f.read()
with open(os.path.join(DIR, "requirements.txt"), "r") as f:
    REQUIRED = [i for i in f.read().split("\n") if len(i)]


setup(
    name="tweezers",
    packages=["tweezers"],
    version="0.0.1",
    description="A lightweight library for scraping Twitter data.",
    long_description=long_description,
    author="Toby Petty",
    author_email="tobypetty@hotmail.com",
    url="https://github.com/toby-p/tweezers",
    install_requires=REQUIRED,
    python_requires='>=3.6',
    keywords=["api", "twitter", "data"],
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
    ],
    include_package_data=True,
    package_data={"tweezers": ["docs/Tweezers.ipynb", "docs/README.txt"]}
)
