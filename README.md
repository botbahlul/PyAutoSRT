# pyautosrt <a href="https://pypi.python.org/pypi/pyautosrt"><img src="https://img.shields.io/pypi/v/pyautosrt.svg"></img></a>



https://user-images.githubusercontent.com/88623122/218178963-fb77891c-1845-4514-8806-069dc342dca3.mp4

### UPDATE NOTES
SINCE VERSION 0.1.14 I ADDED streamlink MODULE WHICH SUPPORTS urllib3 >=1.26.0, <3.x BRANCH ONLY, SO IF YOU'RE STILL WANT TO INSTALL THIS APP TRY TO REINSTALL streamlink WITH \"--force-reinstall\" ARGUMENT.
```
pip install streamlink --force-reinstall
```

TO COMPILE THAT pyautosrt.pyw IN LINUX/WIN FOLDER WITH pyinstaller YOU SHOULD USE THAT \"mypyinstaller.sh\"/\"mypyinstaller.bat\"

### Auto generate subtitles files for any video/audio files

PyAutoSRT is a PySimpleGUI based desktop app to auto generate subtitle and translated subtitle file for any video or audio file

The core script is a modified version of original autosub made by Anastasis Germanidis
https://github.com/agermanidis/autosub

### Installation

If you don't have python on your Windows system you can try compiled version from https://github.com/botbahlul/pyautosrt/releases/

Just extract those ffmpeg.exe and pyautosrt.exe into a folder that has been added to PATH ENVIRONTMENT for example in C:\Windows\system32

You can get latest version of ffmpeg from https://www.ffmpeg.org/

If it doesn't run well then you need to install python on your Windows system.

In Linux you have to install this script with python (version minimal 3.8 ) and install ffmpeg with your linux package manager for example in debian based linux distribution you can type :

```
apt update
apt install -y ffmpeg
```

To install this pyautosrt, just type :
```
pip install pyautosrt
```

You can compile this script into a single executable file with pyinstaller by downloading "\__init\__.py" file, rename it to pyautosrt.py and type :
```
pip install pyinstaller
pyinstaller --onefile pyautosrt.py
```

The executable compiled file will be placed by pyinstaller into dist subfolder of your current working folder, so you can just rename and put that compiled file into a folder that has been added to your PATH ENVIRONTMENT so you can execute it from anywhere

I was succesfuly compiled it in Windows 10 with pyinstaller-5.1 and Pyhton-3.10.4, and python-3.8.12 in Debian 9

Another alternative way to install this script with python is by cloning this git (or downloading this git as zip then extract it into a folder), and then just type :

```
python setup.py build
python setup.py install
```

### Usage 

```
usage: pyautosrt [-h] [-S SRC_LANGUAGE] [-D DST_LANGUAGE] [-ll] [-F FORMAT] [-lf] [-es EMBED_SRC] [-ed EMBED_DST]
                     [-fr FORCE_RECOGNIZE] [-v]
                     [source_path ...]

positional arguments:
  source_path           Path to the video or audio files to generate subtitle (use wildcard for multiple files or separate them with
                        a space character e.g. "file 1.mp4" "file 2.mp4")

options:
  -h, --help            show this help message and exit
  -S SRC_LANGUAGE, --src-language SRC_LANGUAGE
                        Language code of the audio language spoken in video/audio source_path
  -D DST_LANGUAGE, --dst-language DST_LANGUAGE
                        Desired translation language code for the subtitles
  -ll, --list-languages
                        List all supported languages
  -F FORMAT, --format FORMAT
                        Desired subtitle format
  -lf, --list-formats   List all supported subtitle formats
  -es EMBED_SRC, --embed-src EMBED_SRC
                        Boolean value (True or False) for embed_src subtitles file into video file
  -ed EMBED_DST, --embed-dst EMBED_DST
                        Boolean value (True or False) for embed_src subtitles file into video file
  -fr FORCE_RECOGNIZE, --force-recognize FORCE_RECOGNIZE
                        Boolean value (True or False) for re-recognize media file event if it's already has subtitles stream
  -v, --version         show program's version number and exit
```

Those command switches \'-S\', \'-D\', and \'-F\' are not mandatory. They just make combobox directly select your desired options if you prefer to type it rather that click on combobox. Please note that these arguments are only work if you install this app with pip (won't work if you run that executable from releases zip file).

UPDATE NOTES : SINCE VERSION 0.1.1 YOU CAN SELECT MULTIPLE VIDEO/AUDIO FILES, BUT REMEMBER THAT ALL FILES YOU SELECT SHOULD HAVE SAME AUDIO LANGUAGE AND DESIRED TRANSLATION LANGUAGE.

### License

MIT

Check my other SPEECH RECOGNITIION + TRANSLATE PROJECTS https://github.com/botbahlul?tab=repositories

Buy me coffee : https://sociabuzz.com/botbahlul/tribe
