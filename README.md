# pyautosrt <a href="https://pypi.python.org/pypi/pyautosrt"><img src="https://img.shields.io/pypi/v/pyautosrt.svg"></img></a>



https://user-images.githubusercontent.com/88623122/218178963-fb77891c-1845-4514-8806-069dc342dca3.mp4



### Auto generate subtitles files for any video/audio files

PyAutoSRT is a PySimpleGUI based desktop app to auto generate subtitle and translated subtitle file for any video or audio file

The core script is a modified version of original autosub made by Anastasis Germanidis
https://github.com/agermanidis/autosub

### Installation

If you don't have python on your Windows system you can get compiled version from https://github.com/botbahlul/pyautosrt/releases/

Just extract those ffmpeg.exe and pyautosrt.exe into a folder that has been added to PATH ENVIRONTMET for example in C:\Windows\system32

You can get latest version of ffmpeg from https://www.ffmpeg.org/

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

NOTES : SINCE VERSION 0.1.9 YOU SHOULD USE THAT \"mypyinstaller.bat\" (FOR WINDOWS) OR \"mypyinstaller.sh\" (FOR LINUX) TO COMPILE THAT \"pyautosrt.pyw\"

Another alternative way to install this script with python is by cloning this git (or downloading this git as zip then extract it into a folder), and then just type :

```
python setup.py build
python setup.py install
```

### Usage 

```
usage: pyautosrt.py [-h] [-S SRC_LANGUAGE] [-D DST_LANGUAGE] [-ll] [-F FORMAT] [-lf] [-v] [source_path ...]

positional arguments:
  source_path           Path to the video or audio files to generate subtitle (use wildcard for multiple files or separate them with
                        space eg. "file 1.mp4" "file 2.mp4")

options:
  -h, --help            show this help message and exit
  -S SRC_LANGUAGE, --src-language SRC_LANGUAGE
                        Spoken language
  -D DST_LANGUAGE, --dst-language DST_LANGUAGE
                        Desired language for translation
  -ll, --list-languages
                        List all available source/translation languages
  -F FORMAT, --format FORMAT
                        Desired subtitle format
  -lf, --list-formats   List all available subtitle formats
  -v, --version         show program's version number and exit
```

Those command switch '-S' and '-D' are not mandatory. It's just to make combobox directly select your desired language if you prefer to type it rather that click on combobox.

UPDATE NOTES : SINCE VERSION 0.1.1 YOU CAN SELECT MULTIPLE VIDEO/AUDIO FILES, BUT REMEMBER THAT ALL FILES YOU SELECT SHOULD HAVE SAME AUDIO LANGUAGE AND DESIRED TRANSLATION LANGUAGE.

### License

MIT
