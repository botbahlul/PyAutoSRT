#!/usr/bin/env python3.8
from __future__ import unicode_literals
import platform
from pyautosrt import VERSION
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module='setuptools')
warnings.filterwarnings("ignore", category=UserWarning, module='setuptools')
warnings.filterwarnings("ignore", message=".*is deprecated*")

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

long_description = (
    'pyautosrt  is a python based desktop app  for automatic speech  recognition and '
    'subtitle generation. It takes a video or an audio file as input, performs voice'
    'activity detection  to find speech regions,  makes parallel requests to  Google '
    'Web Speech API  to generate transcriptions  for those regions,  then translates'
    'them to a different language, and finally saves the resulting subtitles to disk.'
    'It supports  a variety of input and output languages  and can currently produce '
    'subtitles in SRT, VTT, JSON, and RAW format.'
)

install_requires=[
    "requests>=2.3.0",
    "httpx>=0.13.3",
    "pysrt>=1.0.1",
    "six>=1.11.0",
    "pysimplegui>=4.60.1",
    "streamlink>=5.3.1",
    "urllib3>=1.26.0,<3.0",
]

setup(
    name="pyautosrt",
    version=VERSION,
    description="pyautosrt is a python based desktop app to generate subtitle and translated subtitle file",
    long_description = long_description,
    author="Bot Bahlul",
    author_email="bot.bahlul@gmail.com",
    url="https://github.com/botbahlul/pyautosrt",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "pyautosrt = pyautosrt:main",
        ],
    },
    install_requires=install_requires,
    license=open("LICENSE").read()
)
