from setuptools import setup, find_packages

LONG_DESCRIPTION = open("README.md").read()

setup(
    name="django-firebase-cache",
    url="http://github.com/christippett/django-firebase-cache/",
    author="Chris Tippett",
    author_email="c.tippett@gmail.com",
    version="1.0.0",
    license="MIT",
    package_dir={"": "src"},
    packages=find_packages("src"),
    description="Firebase cache for Django",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    install_requires=["google-cloud-firestore", "firebase_admin"],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 1.11",
        "Framework :: Django :: 2.0",
        "Framework :: Django :: 2.1",
        "Framework :: Django :: 2.2",
    ],
)
