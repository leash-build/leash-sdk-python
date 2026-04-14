from setuptools import setup, find_packages

setup(
    name="leash-sdk",
    version="0.2.0",
    packages=find_packages(),
    install_requires=["requests>=2.28"],
    python_requires=">=3.8",
)
