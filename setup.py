from setuptools import setup

with open("README.md", "r", encoding="UTF-8") as rdm:
    long_desc = rdm.read()

with open("requirements.txt", "r", encoding="UTF-8") as rq:
    req = rq.read()

setup(
    name="vspreview",
    version="0.1b",
    author="Endilll",
    description="Preview for VapourSynth scripts",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    url="https://github.com/Endilll/vapoursynth-preview",
    packages=["vspreview"],
    install_requires=req,
    python_requires=">=3.7",  # Untested below 3.9, but VS supports 3.8+
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Natural Language :: English",
        "Topic :: Multimedia :: Graphics"
    ],
    project_urls={
        "Bug Tracker": "https://github.com/Endilll/vapoursynth-preview/issues"
    }
)
