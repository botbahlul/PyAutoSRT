#!/usr/bin/env python
from __future__ import unicode_literals
from pyautosrt import VERSION
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
    install_requires=[
        "requests>=2.3.0",
        "pysrt>=1.0.1",
        "six>=1.11.0",
        "pysimplegui>=4.60.1",
        "httpx>=0.13.3",
        "streamlink>=5.3.1",
        "urllib3 >=1.26.0,<2.0",
    ],
    license=open("LICENSE").read()
)
