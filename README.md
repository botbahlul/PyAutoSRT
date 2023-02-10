# pyautosrt <a href="https://pypi.python.org/pypi/pyautosrt"><img src="https://img.shields.io/pypi/v/pyautosrt.svg"></img></a>
  
### Auto-generated subtitles for any video

PyAutoSRT is a PySimpleGUI based desktop app to auto generate subtitle and translated subtitle file for any video or audio file

### Installation

if you don't have python on your Windows system you can get compiled version from https://github.com/botbahlul/pyautosrt/releases/

just extract those ffmpeg.exe and pyautosrt.exe into a folder that has been added to PATH ENVIRONTMET for example in C:\Windows\system32

you can get latest version of ffmpeg from https://www.ffmpeg.org/

in Linux you have to install this script with python (version minimal 3.8 ) and install ffmpeg with your linux package manager for example in debian based linux distribution you can type :

```
apt update
apt install -y ffmpeg
```

to install this pyautosrt, just type :
```
pip install pyautosrt
```

you can compile this script into a single executable file with pyinstaller by downloading "\__init\__.py" file, rename it to pyautosrt.py and type :
```
pip install pyinstaller
pyinstaller --onefile pyautosrt.py
```

the executable compiled file will be placed by pyinstaller into dist subfolder of your current working folder, so you can just rename and put that compiled file into a folder that has been added to your PATH ENVIRONTMENT so you can execute it from anywhere

I was succesfuly compiled it in Windows 10 with pyinstaller-5.1 and Pyhton-3.10.4, and python-3.8.12 in Debian 9

another alternative way to install this script with python is by cloning this git (or downloading this git as zip then extract it into a folder), and then just type :

```
python setup.py build
python setup.py install
```

### usage 

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

### License

MIT
