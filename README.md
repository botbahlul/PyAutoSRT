# pyautosrt <a href="https://pypi.python.org/pypi/pyautosrt"><img src="https://img.shields.io/pypi/v/pyautosrt.svg"></img></a>



https://user-images.githubusercontent.com/88623122/218178963-fb77891c-1845-4514-8806-069dc342dca3.mp4



### Auto-generated subtitles for any video

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

Another alternative way to install this script with python is by cloning this git (or downloading this git as zip then extract it into a folder), and then just type :

```
python setup.py build
python setup.py install
```

### Usage 

```
usage: pyautosrt.py [-h] [-S SRC_LANGUAGE] [-D DST_LANGUAGE] [-v] [-lf] [-ll]

options:
  -h, --help            show this help message and exit
  -S SRC_LANGUAGE, --src-language SRC_LANGUAGE
                        Voice language
  -D DST_LANGUAGE, --dst-language DST_LANGUAGE
                        Desired language for translation
  -v, --version         show program's version number and exit
  -lf, --list-formats   List all available subtitle formats
  -ll, --list-languages
                        List all available source/destination languages
```

Those command switch '-S' and '-D' are not mandatory. It's just to make combobox directly select your desired language if you prefer to type it rather that click on combobox.

### License

MIT
