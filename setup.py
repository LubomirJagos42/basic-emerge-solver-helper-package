from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="basicemergesolverhelperpackage",
    version="0.0.9",
    author="Lubomir Jagos",
    author_email="lubomir.jagos.42@gmail.com",
    description="Mesh creation and plot utilities for EMerge solver or other FEM solver.",
    long_description="Helper methods to make easier to do simulation when working with imported STEP files from FreeCAD",
    long_description_content_type="text/markdown",
    url="https://github.com/LubomirJagos42/basic-emerge-solver-helper-package",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "numpy",
        "gmsh",
        "scipy",
        "pandas"
        # "other-package>=1.0.0",
    ],
)