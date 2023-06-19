# ORIGINAL AUTOSUB IMPORTS
from __future__ import absolute_import, print_function, unicode_literals
import argparse
import audioop
import math
import multiprocessing
import os
import subprocess
import sys
import tempfile
import wave
import json
import requests
try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError
import pysrt
import six
# ADDTIONAL IMPORTS
import io
import time
import threading
from threading import Thread
import PySimpleGUI as sg
import tkinter as tk
import httpx
from glob import glob, escape
import ctypes
if sys.platform == "win32":
    import win32clipboard
from streamlink import Streamlink
from streamlink.exceptions import NoPluginError, StreamlinkError, StreamError
from datetime import datetime, timedelta
import shutil
import select
import shlex

#import warnings
#warnings.filterwarnings("ignore", category=DeprecationWarning)
#warnings.filterwarnings("ignore", category=RuntimeWarning)
#sys.tracebacklimit = 0

VERSION = "0.2.6"


def stop_ffmpeg_windows(error_messages_callback=None):
    try:
        tasklist_output = subprocess.check_output(['tasklist'], creationflags=subprocess.CREATE_NO_WINDOW).decode('utf-8')
        ffmpeg_pid = None
        for line in tasklist_output.split('\n'):
            if "ffmpeg" in line:
                ffmpeg_pid = line.split()[1]
                break
        if ffmpeg_pid:
            devnull = open(os.devnull, 'w')
            subprocess.Popen(['taskkill', '/F', '/T', '/PID', ffmpeg_pid], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

    except KeyboardInterrupt:
        if error_messages_callback:
            error_messages_callback("Cancelling all tasks")
        else:
            print("Cancelling all tasks")
        return

    except Exception as e:
        if error_messages_callback:
            error_messages_callback(e)
        else:
            print(e)
        return


def stop_ffmpeg_linux(error_messages_callback=None):
    process_name = 'ffmpeg'
    try:
        output = subprocess.check_output(['ps', '-ef'])
        pid = [line.split()[1] for line in output.decode('utf-8').split('\n') if process_name in line][0]
        subprocess.call(['kill', '-9', str(pid)])
        #print(f"{process_name} has been killed")
    except IndexError:
        #print(f"{process_name} is not running")
        pass

    except KeyboardInterrupt:
        if error_messages_callback:
            error_messages_callback("Cancelling all tasks")
        else:
            print("Cancelling all tasks")
        return

    except Exception as e:
        if error_messages_callback:
            error_messages_callback(e)
        else:
            print(e)
        return


def remove_temp_files(extension, error_messages_callback=None):
    try:
        temp_dir = tempfile.gettempdir()
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith("." + extension):
                    os.remove(os.path.join(root, file))
    except KeyboardInterrupt:
        if error_messages_callback:
            error_messages_callback("Cancelling all tasks")
        else:
            print("Cancelling all tasks")
        return

    except Exception as e:
        if error_messages_callback:
            error_messages_callback(e)
        else:
            print(e)
        return


def is_same_language(src, dst, error_messages_callback=None):
    try:
        return src.split("-")[0] == dst.split("-")[0]
    except Exception as e:
        if error_messages_callback:
            error_messages_callback(e)
        else:
            print(e)
        return


def check_file_type(file_path, error_messages_callback=None):
    try:
        if "\\" in file_path:
            file_path = file_path.replace("\\", "/")

        ffprobe_cmd = [
                        'ffprobe',
                        '-hide_banner',
                        '-v', 'error',
                        '-loglevel', 'error',
                        '-show_format',
                        '-show_streams',
                        '-print_format',
                        'json',
                        file_path
                      ]

        output = None

        if sys.platform == "win32":
            output = subprocess.check_output(ffprobe_cmd, stdin=open(os.devnull), stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW).decode('utf-8')
        else:
            output = subprocess.check_output(ffprobe_cmd, stdin=open(os.devnull), stderr=subprocess.PIPE).decode('utf-8')

        data = json.loads(output)

        if 'streams' in data:
            for stream in data['streams']:
                if 'codec_type' in stream and stream['codec_type'] == 'audio':
                    return 'audio'
                elif 'codec_type' in stream and stream['codec_type'] == 'video':
                    return 'video'

    except (subprocess.CalledProcessError, json.JSONDecodeError):
        pass

    except Exception as e:
        if error_messages_callback:
            error_messages_callback(e)
        else:
            print(e)

    return None


class Language:
    def __init__(self):
        self.list_codes = []
        self.list_codes.append("af")
        self.list_codes.append("sq")
        self.list_codes.append("am")
        self.list_codes.append("ar")
        self.list_codes.append("hy")
        self.list_codes.append("as")
        self.list_codes.append("ay")
        self.list_codes.append("az")
        self.list_codes.append("bm")
        self.list_codes.append("eu")
        self.list_codes.append("be")
        self.list_codes.append("bn")
        self.list_codes.append("bho")
        self.list_codes.append("bs")
        self.list_codes.append("bg")
        self.list_codes.append("ca")
        self.list_codes.append("ceb")
        self.list_codes.append("ny")
        self.list_codes.append("zh")
        self.list_codes.append("zh-CN")
        self.list_codes.append("zh-TW")
        self.list_codes.append("co")
        self.list_codes.append("hr")
        self.list_codes.append("cs")
        self.list_codes.append("da")
        self.list_codes.append("dv")
        self.list_codes.append("doi")
        self.list_codes.append("nl")
        self.list_codes.append("en")
        self.list_codes.append("eo")
        self.list_codes.append("et")
        self.list_codes.append("ee")
        self.list_codes.append("fil")
        self.list_codes.append("fi")
        self.list_codes.append("fr")
        self.list_codes.append("fy")
        self.list_codes.append("gl")
        self.list_codes.append("ka")
        self.list_codes.append("de")
        self.list_codes.append("el")
        self.list_codes.append("gn")
        self.list_codes.append("gu")
        self.list_codes.append("ht")
        self.list_codes.append("ha")
        self.list_codes.append("haw")
        self.list_codes.append("he")
        self.list_codes.append("hi")
        self.list_codes.append("hmn")
        self.list_codes.append("hu")
        self.list_codes.append("is")
        self.list_codes.append("ig")
        self.list_codes.append("ilo")
        self.list_codes.append("id")
        self.list_codes.append("ga")
        self.list_codes.append("it")
        self.list_codes.append("ja")
        self.list_codes.append("jv")
        self.list_codes.append("kn")
        self.list_codes.append("kk")
        self.list_codes.append("km")
        self.list_codes.append("rw")
        self.list_codes.append("gom")
        self.list_codes.append("ko")
        self.list_codes.append("kri")
        self.list_codes.append("kmr")
        self.list_codes.append("ckb")
        self.list_codes.append("ky")
        self.list_codes.append("lo")
        self.list_codes.append("la")
        self.list_codes.append("lv")
        self.list_codes.append("ln")
        self.list_codes.append("lt")
        self.list_codes.append("lg")
        self.list_codes.append("lb")
        self.list_codes.append("mk")
        self.list_codes.append("mg")
        self.list_codes.append("ms")
        self.list_codes.append("ml")
        self.list_codes.append("mt")
        self.list_codes.append("mi")
        self.list_codes.append("mr")
        self.list_codes.append("mni-Mtei")
        self.list_codes.append("lus")
        self.list_codes.append("mn")
        self.list_codes.append("my")
        self.list_codes.append("ne")
        self.list_codes.append("no")
        self.list_codes.append("or")
        self.list_codes.append("om")
        self.list_codes.append("ps")
        self.list_codes.append("fa")
        self.list_codes.append("pl")
        self.list_codes.append("pt")
        self.list_codes.append("pa")
        self.list_codes.append("qu")
        self.list_codes.append("ro")
        self.list_codes.append("ru")
        self.list_codes.append("sm")
        self.list_codes.append("sa")
        self.list_codes.append("gd")
        self.list_codes.append("nso")
        self.list_codes.append("sr")
        self.list_codes.append("st")
        self.list_codes.append("sn")
        self.list_codes.append("sd")
        self.list_codes.append("si")
        self.list_codes.append("sk")
        self.list_codes.append("sl")
        self.list_codes.append("so")
        self.list_codes.append("es")
        self.list_codes.append("su")
        self.list_codes.append("sw")
        self.list_codes.append("sv")
        self.list_codes.append("tg")
        self.list_codes.append("ta")
        self.list_codes.append("tt")
        self.list_codes.append("te")
        self.list_codes.append("th")
        self.list_codes.append("ti")
        self.list_codes.append("ts")
        self.list_codes.append("tr")
        self.list_codes.append("tk")
        self.list_codes.append("tw")
        self.list_codes.append("uk")
        self.list_codes.append("ur")
        self.list_codes.append("ug")
        self.list_codes.append("uz")
        self.list_codes.append("vi")
        self.list_codes.append("cy")
        self.list_codes.append("xh")
        self.list_codes.append("yi")
        self.list_codes.append("yo")
        self.list_codes.append("zu")

        self.list_names = []
        self.list_names.append("Afrikaans")
        self.list_names.append("Albanian")
        self.list_names.append("Amharic")
        self.list_names.append("Arabic")
        self.list_names.append("Armenian")
        self.list_names.append("Assamese")
        self.list_names.append("Aymara")
        self.list_names.append("Azerbaijani")
        self.list_names.append("Bambara")
        self.list_names.append("Basque")
        self.list_names.append("Belarusian")
        self.list_names.append("Bengali")
        self.list_names.append("Bhojpuri")
        self.list_names.append("Bosnian")
        self.list_names.append("Bulgarian")
        self.list_names.append("Catalan")
        self.list_names.append("Cebuano")
        self.list_names.append("Chichewa")
        self.list_names.append("Chinese")
        self.list_names.append("Chinese (Simplified)")
        self.list_names.append("Chinese (Traditional)")
        self.list_names.append("Corsican")
        self.list_names.append("Croatian")
        self.list_names.append("Czech")
        self.list_names.append("Danish")
        self.list_names.append("Dhivehi")
        self.list_names.append("Dogri")
        self.list_names.append("Dutch")
        self.list_names.append("English")
        self.list_names.append("Esperanto")
        self.list_names.append("Estonian")
        self.list_names.append("Ewe")
        self.list_names.append("Filipino")
        self.list_names.append("Finnish")
        self.list_names.append("French")
        self.list_names.append("Frisian")
        self.list_names.append("Galician")
        self.list_names.append("Georgian")
        self.list_names.append("German")
        self.list_names.append("Greek")
        self.list_names.append("Guarani")
        self.list_names.append("Gujarati")
        self.list_names.append("Haitian Creole")
        self.list_names.append("Hausa")
        self.list_names.append("Hawaiian")
        self.list_names.append("Hebrew")
        self.list_names.append("Hindi")
        self.list_names.append("Hmong")
        self.list_names.append("Hungarian")
        self.list_names.append("Icelandic")
        self.list_names.append("Igbo")
        self.list_names.append("Ilocano")
        self.list_names.append("Indonesian")
        self.list_names.append("Irish")
        self.list_names.append("Italian")
        self.list_names.append("Japanese")
        self.list_names.append("Javanese")
        self.list_names.append("Kannada")
        self.list_names.append("Kazakh")
        self.list_names.append("Khmer")
        self.list_names.append("Kinyarwanda")
        self.list_names.append("Konkani")
        self.list_names.append("Korean")
        self.list_names.append("Krio")
        self.list_names.append("Kurdish (Kurmanji)")
        self.list_names.append("Kurdish (Sorani)")
        self.list_names.append("Kyrgyz")
        self.list_names.append("Lao")
        self.list_names.append("Latin")
        self.list_names.append("Latvian")
        self.list_names.append("Lingala")
        self.list_names.append("Lithuanian")
        self.list_names.append("Luganda")
        self.list_names.append("Luxembourgish")
        self.list_names.append("Macedonian")
        self.list_names.append("Malagasy")
        self.list_names.append("Malay")
        self.list_names.append("Malayalam")
        self.list_names.append("Maltese")
        self.list_names.append("Maori")
        self.list_names.append("Marathi")
        self.list_names.append("Meiteilon (Manipuri)")
        self.list_names.append("Mizo")
        self.list_names.append("Mongolian")
        self.list_names.append("Myanmar (Burmese)")
        self.list_names.append("Nepali")
        self.list_names.append("Norwegian")
        self.list_names.append("Odiya (Oriya)")
        self.list_names.append("Oromo")
        self.list_names.append("Pashto")
        self.list_names.append("Persian")
        self.list_names.append("Polish")
        self.list_names.append("Portuguese")
        self.list_names.append("Punjabi")
        self.list_names.append("Quechua")
        self.list_names.append("Romanian")
        self.list_names.append("Russian")
        self.list_names.append("Samoan")
        self.list_names.append("Sanskrit")
        self.list_names.append("Scots Gaelic")
        self.list_names.append("Sepedi")
        self.list_names.append("Serbian")
        self.list_names.append("Sesotho")
        self.list_names.append("Shona")
        self.list_names.append("Sindhi")
        self.list_names.append("Sinhala")
        self.list_names.append("Slovak")
        self.list_names.append("Slovenian")
        self.list_names.append("Somali")
        self.list_names.append("Spanish")
        self.list_names.append("Sundanese")
        self.list_names.append("Swahili")
        self.list_names.append("Swedish")
        self.list_names.append("Tajik")
        self.list_names.append("Tamil")
        self.list_names.append("Tatar")
        self.list_names.append("Telugu")
        self.list_names.append("Thai")
        self.list_names.append("Tigrinya")
        self.list_names.append("Tsonga")
        self.list_names.append("Turkish")
        self.list_names.append("Turkmen")
        self.list_names.append("Twi (Akan)")
        self.list_names.append("Ukrainian")
        self.list_names.append("Urdu")
        self.list_names.append("Uyghur")
        self.list_names.append("Uzbek")
        self.list_names.append("Vietnamese")
        self.list_names.append("Welsh")
        self.list_names.append("Xhosa")
        self.list_names.append("Yiddish")
        self.list_names.append("Yoruba")
        self.list_names.append("Zulu")

        self.list_ffmpeg_codes = []
        self.list_ffmpeg_codes.append("afr")  # Afrikaans
        self.list_ffmpeg_codes.append("alb")  # Albanian
        self.list_ffmpeg_codes.append("amh")  # Amharic
        self.list_ffmpeg_codes.append("ara")  # Arabic
        self.list_ffmpeg_codes.append("hye")  # Armenian
        self.list_ffmpeg_codes.append("asm")  # Assamese
        self.list_ffmpeg_codes.append("aym")  # Aymara
        self.list_ffmpeg_codes.append("aze")  # Azerbaijani
        self.list_ffmpeg_codes.append("bam")  # Bambara
        self.list_ffmpeg_codes.append("eus")  # Basque
        self.list_ffmpeg_codes.append("bel")  # Belarusian
        self.list_ffmpeg_codes.append("ben")  # Bengali
        self.list_ffmpeg_codes.append("bho")  # Bhojpuri
        self.list_ffmpeg_codes.append("bos")  # Bosnian
        self.list_ffmpeg_codes.append("bul")  # Bulgarian
        self.list_ffmpeg_codes.append("cat")  # Catalan
        self.list_ffmpeg_codes.append("ceb")  # Cebuano
        self.list_ffmpeg_codes.append("nya")  # Chichewa
        self.list_ffmpeg_codes.append("zho")  # Chinese
        self.list_ffmpeg_codes.append("zho-CN")  # Chinese (Simplified)
        self.list_ffmpeg_codes.append("zho-TW")  # Chinese (Traditional)
        self.list_ffmpeg_codes.append("cos")  # Corsican
        self.list_ffmpeg_codes.append("hrv")  # Croatian
        self.list_ffmpeg_codes.append("ces")  # Czech
        self.list_ffmpeg_codes.append("dan")  # Danish
        self.list_ffmpeg_codes.append("div")  # Dhivehi
        self.list_ffmpeg_codes.append("doi")  # Dogri
        self.list_ffmpeg_codes.append("nld")  # Dutch
        self.list_ffmpeg_codes.append("eng")  # English
        self.list_ffmpeg_codes.append("epo")  # Esperanto
        self.list_ffmpeg_codes.append("est")  # Estonian
        self.list_ffmpeg_codes.append("ewe")  # Ewe
        self.list_ffmpeg_codes.append("fil")  # Filipino
        self.list_ffmpeg_codes.append("fin")  # Finnish
        self.list_ffmpeg_codes.append("fra")  # French
        self.list_ffmpeg_codes.append("fry")  # Frisian
        self.list_ffmpeg_codes.append("glg")  # Galician
        self.list_ffmpeg_codes.append("kat")  # Georgian
        self.list_ffmpeg_codes.append("deu")  # German
        self.list_ffmpeg_codes.append("ell")  # Greek
        self.list_ffmpeg_codes.append("grn")  # Guarani
        self.list_ffmpeg_codes.append("guj")  # Gujarati
        self.list_ffmpeg_codes.append("hat")  # Haitian Creole
        self.list_ffmpeg_codes.append("hau")  # Hausa
        self.list_ffmpeg_codes.append("haw")  # Hawaiian
        self.list_ffmpeg_codes.append("heb")  # Hebrew
        self.list_ffmpeg_codes.append("hin")  # Hindi
        self.list_ffmpeg_codes.append("hmn")  # Hmong
        self.list_ffmpeg_codes.append("hun")  # Hungarian
        self.list_ffmpeg_codes.append("isl")  # Icelandic
        self.list_ffmpeg_codes.append("ibo")  # Igbo
        self.list_ffmpeg_codes.append("ilo")  # Ilocano
        self.list_ffmpeg_codes.append("ind")  # Indonesian
        self.list_ffmpeg_codes.append("gle")  # Irish
        self.list_ffmpeg_codes.append("ita")  # Italian
        self.list_ffmpeg_codes.append("jpn")  # Japanese
        self.list_ffmpeg_codes.append("jav")  # Javanese
        self.list_ffmpeg_codes.append("kan")  # Kannada
        self.list_ffmpeg_codes.append("kaz")  # Kazakh
        self.list_ffmpeg_codes.append("khm")  # Khmer
        self.list_ffmpeg_codes.append("kin")  # Kinyarwanda
        self.list_ffmpeg_codes.append("kok")  # Konkani
        self.list_ffmpeg_codes.append("kor")  # Korean
        self.list_ffmpeg_codes.append("kri")  # Krio
        self.list_ffmpeg_codes.append("kmr")  # Kurdish (Kurmanji)
        self.list_ffmpeg_codes.append("ckb")  # Kurdish (Sorani)
        self.list_ffmpeg_codes.append("kir")  # Kyrgyz
        self.list_ffmpeg_codes.append("lao")  # Lao
        self.list_ffmpeg_codes.append("lat")  # Latin
        self.list_ffmpeg_codes.append("lav")  # Latvian
        self.list_ffmpeg_codes.append("lin")  # Lingala
        self.list_ffmpeg_codes.append("lit")  # Lithuanian
        self.list_ffmpeg_codes.append("lug")  # Luganda
        self.list_ffmpeg_codes.append("ltz")  # Luxembourgish
        self.list_ffmpeg_codes.append("mkd")  # Macedonian
        self.list_ffmpeg_codes.append("mlg")  # Malagasy
        self.list_ffmpeg_codes.append("msa")  # Malay
        self.list_ffmpeg_codes.append("mal")  # Malayalam
        self.list_ffmpeg_codes.append("mlt")  # Maltese
        self.list_ffmpeg_codes.append("mri")  # Maori
        self.list_ffmpeg_codes.append("mar")  # Marathi
        self.list_ffmpeg_codes.append("mni-Mtei")  # Meiteilon (Manipuri)
        self.list_ffmpeg_codes.append("lus")  # Mizo
        self.list_ffmpeg_codes.append("mon")  # Mongolian
        self.list_ffmpeg_codes.append("mya")  # Myanmar (Burmese)
        self.list_ffmpeg_codes.append("nep")  # Nepali
        self.list_ffmpeg_codes.append("nor")  # Norwegian
        self.list_ffmpeg_codes.append("ori")  # Odiya (Oriya)
        self.list_ffmpeg_codes.append("orm")  # Oromo
        self.list_ffmpeg_codes.append("pus")  # Pashto
        self.list_ffmpeg_codes.append("fas")  # Persian
        self.list_ffmpeg_codes.append("pol")  # Polish
        self.list_ffmpeg_codes.append("por")  # Portuguese
        self.list_ffmpeg_codes.append("pan")  # Punjabi
        self.list_ffmpeg_codes.append("que")  # Quechua
        self.list_ffmpeg_codes.append("ron")  # Romanian
        self.list_ffmpeg_codes.append("rus")  # Russian
        self.list_ffmpeg_codes.append("smo")  # Samoan
        self.list_ffmpeg_codes.append("san")  # Sanskrit
        self.list_ffmpeg_codes.append("gla")  # Scots Gaelic
        self.list_ffmpeg_codes.append("nso")  # Sepedi
        self.list_ffmpeg_codes.append("srp")  # Serbian
        self.list_ffmpeg_codes.append("sot")  # Sesotho
        self.list_ffmpeg_codes.append("sna")  # Shona
        self.list_ffmpeg_codes.append("snd")  # Sindhi
        self.list_ffmpeg_codes.append("sin")  # Sinhala
        self.list_ffmpeg_codes.append("slk")  # Slovak
        self.list_ffmpeg_codes.append("slv")  # Slovenian
        self.list_ffmpeg_codes.append("som")  # Somali
        self.list_ffmpeg_codes.append("spa")  # Spanish
        self.list_ffmpeg_codes.append("sun")  # Sundanese
        self.list_ffmpeg_codes.append("swa")  # Swahili
        self.list_ffmpeg_codes.append("swe")  # Swedish
        self.list_ffmpeg_codes.append("tgk")  # Tajik
        self.list_ffmpeg_codes.append("tam")  # Tamil
        self.list_ffmpeg_codes.append("tat")  # Tatar
        self.list_ffmpeg_codes.append("tel")  # Telugu
        self.list_ffmpeg_codes.append("tha")  # Thai
        self.list_ffmpeg_codes.append("tir")  # Tigrinya
        self.list_ffmpeg_codes.append("tso")  # Tsonga
        self.list_ffmpeg_codes.append("tur")  # Turkish
        self.list_ffmpeg_codes.append("tuk")  # Turkmen
        self.list_ffmpeg_codes.append("twi")  # Twi (Akan)
        self.list_ffmpeg_codes.append("ukr")  # Ukrainian
        self.list_ffmpeg_codes.append("urd")  # Urdu
        self.list_ffmpeg_codes.append("uig")  # Uyghur
        self.list_ffmpeg_codes.append("uzb")  # Uzbek
        self.list_ffmpeg_codes.append("vie")  # Vietnamese
        self.list_ffmpeg_codes.append("wel")  # Welsh
        self.list_ffmpeg_codes.append("xho")  # Xhosa
        self.list_ffmpeg_codes.append("yid")  # Yiddish
        self.list_ffmpeg_codes.append("yor")  # Yoruba
        self.list_ffmpeg_codes.append("zul")  # Zulu

        self.code_of_name = dict(zip(self.list_names, self.list_codes))
        self.name_of_code = dict(zip(self.list_codes, self.list_names))

        self.ffmpeg_code_of_name = dict(zip(self.list_names, self.list_ffmpeg_codes))
        self.ffmpeg_code_of_code = dict(zip(self.list_codes, self.list_ffmpeg_codes))
        self.name_of_ffmpeg_code = dict(zip(self.list_ffmpeg_codes, self.list_names))

        self.dict = {
                        'af': 'Afrikaans',
                        'sq': 'Albanian',
                        'am': 'Amharic',
                        'ar': 'Arabic',
                        'hy': 'Armenian',
                        'as': 'Assamese',
                        'ay': 'Aymara',
                        'az': 'Azerbaijani',
                        'bm': 'Bambara',
                        'eu': 'Basque',
                        'be': 'Belarusian',
                        'bn': 'Bengali',
                        'bho': 'Bhojpuri',
                        'bs': 'Bosnian',
                        'bg': 'Bulgarian',
                        'ca': 'Catalan',
                        'ceb': 'Cebuano',
                        'ny': 'Chichewa',
                        'zh': 'Chinese',
                        'zh-CN': 'Chinese (Simplified)',
                        'zh-TW': 'Chinese (Traditional)',
                        'co': 'Corsican',
                        'hr': 'Croatian',
                        'cs': 'Czech',
                        'da': 'Danish',
                        'dv': 'Dhivehi',
                        'doi': 'Dogri',
                        'nl': 'Dutch',
                        'en': 'English',
                        'eo': 'Esperanto',
                        'et': 'Estonian',
                        'ee': 'Ewe',
                        'fil': 'Filipino',
                        'fi': 'Finnish',
                        'fr': 'French',
                        'fy': 'Frisian',
                        'gl': 'Galician',
                        'ka': 'Georgian',
                        'de': 'German',
                        'el': 'Greek',
                        'gn': 'Guarani',
                        'gu': 'Gujarati',
                        'ht': 'Haitian Creole',
                        'ha': 'Hausa',
                        'haw': 'Hawaiian',
                        'he': 'Hebrew',
                        'hi': 'Hindi',
                        'hmn': 'Hmong',
                        'hu': 'Hungarian',
                        'is': 'Icelandic',
                        'ig': 'Igbo',
                        'ilo': 'Ilocano',
                        'id': 'Indonesian',
                        'ga': 'Irish',
                        'it': 'Italian',
                        'ja': 'Japanese',
                        'jv': 'Javanese',
                        'kn': 'Kannada',
                        'kk': 'Kazakh',
                        'km': 'Khmer',
                        'rw': 'Kinyarwanda',
                        'gom': 'Konkani',
                        'ko': 'Korean',
                        'kri': 'Krio',
                        'kmr': 'Kurdish (Kurmanji)',
                        'ckb': 'Kurdish (Sorani)',
                        'ky': 'Kyrgyz',
                        'lo': 'Lao',
                        'la': 'Latin',
                        'lv': 'Latvian',
                        'ln': 'Lingala',
                        'lt': 'Lithuanian',
                        'lg': 'Luganda',
                        'lb': 'Luxembourgish',
                        'mk': 'Macedonian',
                        'mg': 'Malagasy',
                        'ms': 'Malay',
                        'ml': 'Malayalam',
                        'mt': 'Maltese',
                        'mi': 'Maori',
                        'mr': 'Marathi',
                        'mni-Mtei': 'Meiteilon (Manipuri)',
                        'lus': 'Mizo',
                        'mn': 'Mongolian',
                        'my': 'Myanmar (Burmese)',
                        'ne': 'Nepali',
                        'no': 'Norwegian',
                        'or': 'Odiya (Oriya)',
                        'om': 'Oromo',
                        'ps': 'Pashto',
                        'fa': 'Persian',
                        'pl': 'Polish',
                        'pt': 'Portuguese',
                        'pa': 'Punjabi',
                        'qu': 'Quechua',
                        'ro': 'Romanian',
                        'ru': 'Russian',
                        'sm': 'Samoan',
                        'sa': 'Sanskrit',
                        'gd': 'Scots Gaelic',
                        'nso': 'Sepedi',
                        'sr': 'Serbian',
                        'st': 'Sesotho',
                        'sn': 'Shona',
                        'sd': 'Sindhi',
                        'si': 'Sinhala',
                        'sk': 'Slovak',
                        'sl': 'Slovenian',
                        'so': 'Somali',
                        'es': 'Spanish',
                        'su': 'Sundanese',
                        'sw': 'Swahili',
                        'sv': 'Swedish',
                        'tg': 'Tajik',
                        'ta': 'Tamil',
                        'tt': 'Tatar',
                        'te': 'Telugu',
                        'th': 'Thai',
                        'ti': 'Tigrinya',
                        'ts': 'Tsonga',
                        'tr': 'Turkish',
                        'tk': 'Turkmen',
                        'tw': 'Twi (Akan)',
                        'uk': 'Ukrainian',
                        'ur': 'Urdu',
                        'ug': 'Uyghur',
                        'uz': 'Uzbek',
                        'vi': 'Vietnamese',
                        'cy': 'Welsh',
                        'xh': 'Xhosa',
                        'yi': 'Yiddish',
                        'yo': 'Yoruba',
                        'zu': 'Zulu',
                    }

        self.ffmpeg_dict = {
                                'af': 'afr', # Afrikaans
                                'sq': 'alb', # Albanian
                                'am': 'amh', # Amharic
                                'ar': 'ara', # Arabic
                                'hy': 'arm', # Armenian
                                'as': 'asm', # Assamese
                                'ay': 'aym', # Aymara
                                'az': 'aze', # Azerbaijani
                                'bm': 'bam', # Bambara
                                'eu': 'baq', # Basque
                                'be': 'bel', # Belarusian
                                'bn': 'ben', # Bengali
                                'bho': 'bho', # Bhojpuri
                                'bs': 'bos', # Bosnian
                                'bg': 'bul', # Bulgarian
                                'ca': 'cat', # Catalan
                                'ceb': 'ceb', # Cebuano
                                'ny': 'nya', # Chichewa
                                'zh': 'chi', # Chinese
                                'zh-CN': 'chi', # Chinese (Simplified)
                                'zh-TW': 'chi', # Chinese (Traditional)
                                'co': 'cos', # Corsican
                                'hr': 'hrv', # Croatian
                                'cs': 'cze', # Czech
                                'da': 'dan', # Danish
                                'dv': 'div', # Dhivehi
                                'doi': 'doi', # Dogri
                                'nl': 'dut', # Dutch
                                'en': 'eng', # English
                                'eo': 'epo', # Esperanto
                                'et': 'est', # Estonian
                                'ee': 'ewe', # Ewe
                                'fil': 'fil', # Filipino
                                'fi': 'fin', # Finnish
                                'fr': 'fre', # French
                                'fy': 'fry', # Frisian
                                'gl': 'glg', # Galician
                                'ka': 'geo', # Georgian
                                'de': 'ger', # German
                                'el': 'gre', # Greek
                                'gn': 'grn', # Guarani
                                'gu': 'guj', # Gujarati
                                'ht': 'hat', # Haitian Creole
                                'ha': 'hau', # Hausa
                                'haw': 'haw', # Hawaiian
                                'he': 'heb', # Hebrew
                                'hi': 'hin', # Hindi
                                'hmn': 'hmn', # Hmong
                                'hu': 'hun', # Hungarian
                                'is': 'ice', # Icelandic
                                'ig': 'ibo', # Igbo
                                'ilo': 'ilo', # Ilocano
                                'id': 'ind', # Indonesian
                                'ga': 'gle', # Irish
                                'it': 'ita', # Italian
                                'ja': 'jpn', # Japanese
                                'jv': 'jav', # Javanese
                                'kn': 'kan', # Kannada
                                'kk': 'kaz', # Kazakh
                                'km': 'khm', # Khmer
                                'rw': 'kin', # Kinyarwanda
                                'gom': 'kok', # Konkani
                                'ko': 'kor', # Korean
                                'kri': 'kri', # Krio
                                'kmr': 'kur', # Kurdish (Kurmanji)
                                'ckb': 'kur', # Kurdish (Sorani)
                                'ky': 'kir', # Kyrgyz
                                'lo': 'lao', # Lao
                                'la': 'lat', # Latin
                                'lv': 'lav', # Latvian
                                'ln': 'lin', # Lingala
                                'lt': 'lit', # Lithuanian
                                'lg': 'lug', # Luganda
                                'lb': 'ltz', # Luxembourgish
                                'mk': 'mac', # Macedonian
                                'mg': 'mlg', # Malagasy
                                'ms': 'may', # Malay
                                'ml': 'mal', # Malayalam
                                'mt': 'mlt', # Maltese
                                'mi': 'mao', # Maori
                                'mr': 'mar', # Marathi
                                'mni-Mtei': 'mni', # Meiteilon (Manipuri)
                                'lus': 'lus', # Mizo
                                'mn': 'mon', # Mongolian
                                'my': 'bur', # Myanmar (Burmese)
                                'ne': 'nep', # Nepali
                                'no': 'nor', # Norwegian
                                'or': 'ori', # Odiya (Oriya)
                                'om': 'orm', # Oromo
                                'ps': 'pus', # Pashto
                                'fa': 'per', # Persian
                                'pl': 'pol', # Polish
                                'pt': 'por', # Portuguese
                                'pa': 'pan', # Punjabi
                                'qu': 'que', # Quechua
                                'ro': 'rum', # Romanian
                                'ru': 'rus', # Russian
                                'sm': 'smo', # Samoan
                                'sa': 'san', # Sanskrit
                                'gd': 'gla', # Scots Gaelic
                                'nso': 'nso', # Sepedi
                                'sr': 'srp', # Serbian
                                'st': 'sot', # Sesotho
                                'sn': 'sna', # Shona
                                'sd': 'snd', # Sindhi
                                'si': 'sin', # Sinhala
                                'sk': 'slo', # Slovak
                                'sl': 'slv', # Slovenian
                                'so': 'som', # Somali
                                'es': 'spa', # Spanish
                                'su': 'sun', # Sundanese
                                'sw': 'swa', # Swahili
                                'sv': 'swe', # Swedish
                                'tg': 'tgk', # Tajik
                                'ta': 'tam', # Tamil
                                'tt': 'tat', # Tatar
                                'te': 'tel', # Telugu
                                'th': 'tha', # Thai
                                'ti': 'tir', # Tigrinya
                                'ts': 'tso', # Tsonga
                                'tr': 'tur', # Turkish
                                'tk': 'tuk', # Turkmen
                                'tw': 'twi', # Twi (Akan)
                                'uk': 'ukr', # Ukrainian
                                'ur': 'urd', # Urdu
                                'ug': 'uig', # Uyghur
                                'uz': 'uzb', # Uzbek
                                'vi': 'vie', # Vietnamese
                                'cy': 'wel', # Welsh
                                'xh': 'xho', # Xhosa
                                'yi': 'yid', # Yiddish
                                'yo': 'yor', # Yoruba
                                'zu': 'zul', # Zulu
                           }

    def get_name(self, code):
        return self.name_of_code[code]

    def get_code(self, language):
        return self.code_of_name[language]

    def get_ffmpeg_code(self, code):
        return self.ffmpeg_code_of_code[code]


class WavConverter:
    @staticmethod
    def which(program):
        def is_exe(file_path):
            return os.path.isfile(file_path) and os.access(file_path, os.X_OK)
        fpath, _ = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file
        return None

    @staticmethod
    def ffmpeg_check():
        if WavConverter.which("ffmpeg"):
            return "ffmpeg"
        if WavConverter.which("ffmpeg.exe"):
            return "ffmpeg.exe"
        return None

    def __init__(self, channels=1, rate=48000, progress_callback=None, error_messages_callback=None):
        self.channels = channels
        self.rate = rate
        self.progress_callback = progress_callback
        self.error_messages_callback = error_messages_callback

    def __call__(self, media_filepath):
        temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)

        if "\\" in media_filepath:
            media_filepath = media_filepath.replace("\\", "/")

        if not os.path.isfile(media_filepath):
            if self.error_messages_callback:
                self.error_messages_callback("The given file does not exist: {0}".format(media_filepath))
            else:
                print("The given file does not exist: {0}".format(media_filepath))
                raise Exception("Invalid file: {0}".format(media_filepath))
        if not self.ffmpeg_check():
            if self.error_messages_callback:
                self.error_messages_callback("ffmpeg: Executable not found on machine.")
            else:
                print("ffmpeg: Executable not found on machine.")
                raise Exception("Dependency not found: ffmpeg")

        ffmpeg_command = [
                            'ffmpeg',
                            '-hide_banner',
                            '-loglevel', 'error',
                            '-v', 'error',
                            '-y',
                            '-i', media_filepath,
                            '-ac', str(self.channels),
                            '-ar', str(self.rate),
                            '-progress', '-', '-nostats',
                            temp.name
                         ]

        try:
            media_file_display_name = os.path.basename(media_filepath).split('/')[-1]
            info = f"Converting '{media_file_display_name}' to a temporary WAV file"
            start_time = time.time()

            ffprobe_command = [
                                'ffprobe',
                                '-hide_banner',
                                '-v', 'error',
                                '-loglevel', 'error',
                                '-show_entries',
                                'format=duration',
                                '-of', 'default=noprint_wrappers=1:nokey=1',
                                media_filepath
                              ]

            ffprobe_process = None
            if sys.platform == "win32":
                ffprobe_process = subprocess.check_output(ffprobe_command, stdin=open(os.devnull), universal_newlines=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                ffprobe_process = subprocess.check_output(ffprobe_command, stdin=open(os.devnull), universal_newlines=True)

            total_duration = float(ffprobe_process.strip())

            process = None
            if sys.platform == "win32":
                process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            while True:
                if process.stdout is None:
                    continue

                stderr_line = (process.stdout.readline().decode("utf-8", errors="replace").strip())
 
                if stderr_line == '' and process.poll() is not None:
                    break

                if "out_time=" in stderr_line:
                    time_str = stderr_line.split('time=')[1].split()[0]
                    current_duration = sum(float(x) * 1000 * 60 ** i for i, x in enumerate(reversed(time_str.split(":"))))

                    if current_duration>0:
                        percentage = int(current_duration*100/(int(float(total_duration))*1000))
                        if self.progress_callback:
                            self.progress_callback(info, media_file_display_name, percentage, start_time)

            temp.close()

            return temp.name, self.rate

        except KeyboardInterrupt:
            if self.error_messages_callback:
                self.error_messages_callback("Cancelling all tasks")
            else:
                print("Cancelling all tasks")
            return

        except Exception as e:
            if self.error_messages_callback:
                self.error_messages_callback(f"WavConverter : {e}")
            else:
                print(f"WavConverter : {e}")
            return

# DEFINE progress_callback FUNCTION TO SHOW ffmpeg PROGRESS
# IF WE'RE IN pysimplegui ENVIRONMENT WE CAN DO :
#def show_progress(info, media_file_display_name, percentage, start_time):
    #global main_window
    #main_window.write_event_value('-UPDATE-PROGRESS-', percentage) AND HANDLE THAT EVENT IN pysimplegui MAIN LOOP
# IF WE'RE IN console ENVIRONMENT WE CAN DO :
#def show_progress(info, media_file_display_name, percentage, start_time):
    #global pbar
    #pbar.update(percentage)

# DEFINE error_messages_callback FUNCTION TO SHOW ERROR MESSAGES
# IF WE'RE IN pysimplegui ENVIRONMENT WE CAN DO :
#def show_error_messages(messages):
    #global main_window
    #main_window.write_event_value('-EXCEPTION-', messages) AND HANDLE THAT EVENT IN pysimplegui MAIN LOOP
# IF WE'RE IN console ENVIRONMENT WE CAN DO :
#def show_error_messages(messages):
    #print(messages)


class SpeechRegionFinder:
    @staticmethod
    def percentile(arr, percent):
        arr = sorted(arr)
        k = (len(arr) - 1) * percent
        f = math.floor(k)
        c = math.ceil(k)
        if f == c: return arr[int(k)]
        d0 = arr[int(f)] * (c - k)
        d1 = arr[int(c)] * (k - f)
        return d0 + d1

    def __init__(self, frame_width=4096, min_region_size=0.5, max_region_size=6, error_messages_callback=None):
        self.frame_width = frame_width
        self.min_region_size = min_region_size
        self.max_region_size = max_region_size
        self.error_messages_callback = error_messages_callback

    def __call__(self, wav_filepath):
        try:
            reader = wave.open(wav_filepath)
            sample_width = reader.getsampwidth()
            rate = reader.getframerate()
            n_channels = reader.getnchannels()
            total_duration = reader.getnframes() / rate
            chunk_duration = float(self.frame_width) / rate
            n_chunks = int(total_duration / chunk_duration)
            energies = []
            for i in range(n_chunks):
                chunk = reader.readframes(self.frame_width)
                energies.append(audioop.rms(chunk, sample_width * n_channels))
            threshold = SpeechRegionFinder.percentile(energies, 0.2)
            elapsed_time = 0
            regions = []
            region_start = None
            for energy in energies:
                is_silence = energy <= threshold
                max_exceeded = region_start and elapsed_time - region_start >= self.max_region_size
                if (max_exceeded or is_silence) and region_start:
                    if elapsed_time - region_start >= self.min_region_size:
                        regions.append((region_start, elapsed_time))
                        region_start = None
                elif (not region_start) and (not is_silence):
                    region_start = elapsed_time
                elapsed_time += chunk_duration
            return regions

        except KeyboardInterrupt:
            if self.error_messages_callback:
                self.error_messages_callback("Cancelling all tasks")
            else:
                print("Cancelling all tasks")
            return

        except Exception as e:
            if self.error_messages_callback:
                self.error_messages_callback(e)
            else:
                print(e)
            return


class FLACConverter(object):
    def __init__(self, wav_filepath, include_before=0.25, include_after=0.25, error_messages_callback=None):
        self.wav_filepath = wav_filepath
        self.include_before = include_before
        self.include_after = include_after
        self.error_messages_callback = error_messages_callback

    def __call__(self, region):
        try:
            if "\\" in self.wav_filepath:
                self.wav_filepath = self.wav_filepath.replace("\\", "/")

            start, end = region
            start = max(0, start - self.include_before)
            end += self.include_after
            temp = tempfile.NamedTemporaryFile(suffix='.flac', delete=False)

            command = [
                        'ffmpeg',
                        '-hide_banner',
                        '-loglevel', 'error',
                        '-v', 'error',
                        '-ss', str(start),
                        '-t', str(end - start),
                        '-y',
                        '-i', self.wav_filepath,
                        temp.name
                      ]

            if sys.platform == "win32":
                subprocess.check_output(command, stdin=open(os.devnull), creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.check_output(command, stdin=open(os.devnull))

            content = temp.read()
            temp.close()
            return content

        except KeyboardInterrupt:
            if self.error_messages_callback:
                self.error_messages_callback("Cancelling all tasks")
            else:
                print("Cancelling all tasks")
            return

        except Exception as e:
            if self.error_messages_callback:
                self.error_messages_callback(e)
            else:
                print(e)
            return


class SpeechRecognizer(object):
    def __init__(self, language="en", rate=44100, retries=3, api_key="AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw", timeout=30, error_messages_callback=None):
        self.language = language
        self.rate = rate
        self.api_key = api_key
        self.retries = retries
        self.timeout = timeout
        self.error_messages_callback = error_messages_callback

    def __call__(self, data):
        try:
            for i in range(self.retries):
                url = "http://www.google.com/speech-api/v2/recognize?client=chromium&lang={lang}&key={key}".format(lang=self.language, key=self.api_key)
                headers = {"Content-Type": "audio/x-flac rate=%d" % self.rate}

                try:
                    resp = requests.post(url, data=data, headers=headers, timeout=self.timeout)
                except requests.exceptions.ConnectionError:
                    try:
                        resp = httpx.post(url, data=data, headers=headers, timeout=self.timeout)
                    except httpx.exceptions.NetworkError:
                        continue

                for line in resp.content.decode('utf-8').split("\n"):
                    try:
                        line = json.loads(line)
                        line = line['result'][0]['alternative'][0]['transcript']
                        return line[:1].upper() + line[1:]
                    except:
                        # no result
                        continue

        except KeyboardInterrupt:
            if self.error_messages_callback:
                self.error_messages_callback("Cancelling all tasks")
            else:
                print("Cancelling all tasks")
            return

        except Exception as e:
            if self.error_messages_callback:
                self.error_messages_callback(e)
            else:
                print(e)
            return


class SentenceTranslator(object):
    def __init__(self, src, dst, patience=-1, timeout=30, error_messages_callback=None):
        self.src = src
        self.dst = dst
        self.patience = patience
        self.timeout = timeout
        self.error_messages_callback = error_messages_callback

    def __call__(self, sentence):
        try:
            translated_sentence = []
            # handle the special case: empty string.
            if not sentence:
                return None
            translated_sentence = self.GoogleTranslate(sentence, src=self.src, dst=self.dst, timeout=self.timeout)
            fail_to_translate = translated_sentence[-1] == '\n'
            while fail_to_translate and patience:
                translated_sentence = self.GoogleTranslate(translated_sentence, src=self.src, dst=self.dst, timeout=self.timeout).text
                if translated_sentence[-1] == '\n':
                    if patience == -1:
                        continue
                    patience -= 1
                else:
                    fail_to_translate = False

            return translated_sentence

        except KeyboardInterrupt:
            if self.error_messages_callback:
                self.error_messages_callback("Cancelling all tasks")
            else:
                print("Cancelling all tasks")
            return

        except Exception as e:
            if self.error_messages_callback:
                self.error_messages_callback(e)
            else:
                print(e)
            return

    def GoogleTranslate(self, text, src, dst, timeout=30):
        url = 'https://translate.googleapis.com/translate_a/'
        params = 'single?client=gtx&sl='+src+'&tl='+dst+'&dt=t&q='+text;
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': 'https://translate.google.com',}

        try:
            response = requests.get(url+params, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                response_json = response.json()[0]
                length = len(response_json)
                translation = ""
                for i in range(length):
                    translation = translation + response_json[i][0]
                return translation
            return

        except requests.exceptions.ConnectionError:
            with httpx.Client() as client:
                response = client.get(url+params, headers=headers, timeout=self.timeout)
                if response.status_code == 200:
                    response_json = response.json()[0]
                    length = len(response_json)
                    translation = ""
                    for i in range(length):
                        translation = translation + response_json[i][0]
                    return translation
                return

        except KeyboardInterrupt:
            if self.error_messages_callback:
                self.error_messages_callback("Cancelling all tasks")
            else:
                print("Cancelling all tasks")
            return

        except Exception as e:
            if self.error_messages_callback:
                self.error_messages_callback(e)
            else:
                print(e)
            return


class SubtitleFormatter:
    supported_formats = ['srt', 'vtt', 'json', 'raw']

    def __init__(self, format_type, error_messages_callback=None):
        self.format_type = format_type.lower()
        self.error_messages_callback = error_messages_callback
        
    def __call__(self, subtitles, padding_before=0, padding_after=0):
        try:
            if self.format_type == 'srt':
                return self.srt_formatter(subtitles, padding_before, padding_after)
            elif self.format_type == 'vtt':
                return self.vtt_formatter(subtitles, padding_before, padding_after)
            elif self.format_type == 'json':
                return self.json_formatter(subtitles)
            elif self.format_type == 'raw':
                return self.raw_formatter(subtitles)
            else:
                if error_messages_callback:
                    error_messages_callback(f'Unsupported format type: {self.format_type}')
                else:
                    raise ValueError(f'Unsupported format type: {self.format_type}')

        except KeyboardInterrupt:
            if self.error_messages_callback:
                self.error_messages_callback("Cancelling all tasks")
            else:
                print("Cancelling all tasks")
            return

        except Exception as e:
            if self.error_messages_callback:
                self.error_messages_callback(e)
            else:
                print(e)
            return

    def srt_formatter(self, subtitles, padding_before=0, padding_after=0):
        """
        Serialize a list of subtitles according to the SRT format, with optional time padding.
        """
        sub_rip_file = pysrt.SubRipFile()
        for i, ((start, end), text) in enumerate(subtitles, start=1):
            item = pysrt.SubRipItem()
            item.index = i
            item.text = six.text_type(text)
            item.start.seconds = max(0, start - padding_before)
            item.end.seconds = end + padding_after
            sub_rip_file.append(item)
        return '\n'.join(six.text_type(item) for item in sub_rip_file)

    def vtt_formatter(self, subtitles, padding_before=0, padding_after=0):
        """
        Serialize a list of subtitles according to the VTT format, with optional time padding.
        """
        text = self.srt_formatter(subtitles, padding_before, padding_after)
        text = 'WEBVTT\n\n' + text.replace(',', '.')
        return text

    def json_formatter(self, subtitles):
        """
        Serialize a list of subtitles as a JSON blob.
        """
        subtitle_dicts = [
            {
                'start': start,
                'end': end,
                'content': text,
            }
            for ((start, end), text)
            in subtitles
        ]
        return json.dumps(subtitle_dicts)

    def raw_formatter(self, subtitles):
        """
        Serialize a list of subtitles as a newline-delimited string.
        """
        return ' '.join(text for (_rng, text) in subtitles)


class SubtitleWriter:
    def __init__(self, regions, transcripts, format, error_messages_callback=None):
        self.regions = regions
        self.transcripts = transcripts
        self.format = format
        self.timed_subtitles = [(r, t) for r, t in zip(self.regions, self.transcripts) if t]
        self.error_messages_callback = error_messages_callback

    def get_timed_subtitles(self):
        return self.timed_subtitles

    def write(self, declared_subtitle_filepath):
        try:
            formatter = SubtitleFormatter(self.format)
            formatted_subtitles = formatter(self.timed_subtitles)
            saved_subtitle_filepath = declared_subtitle_filepath
            if saved_subtitle_filepath:
                subtitle_file_base, subtitle_file_ext = os.path.splitext(saved_subtitle_filepath)
                if not subtitle_file_ext:
                    saved_subtitle_filepath = "{base}.{format}".format(base=subtitle_file_base, format=self.format)
                else:
                    saved_subtitle_filepath = declared_subtitle_filepath
            with open(saved_subtitle_filepath, 'wb') as f:
                f.write(formatted_subtitles.encode("utf-8"))
            #with open(saved_subtitle_filepath, 'a') as f:
            #    f.write("\n")

        except KeyboardInterrupt:
            if self.error_messages_callback:
                self.error_messages_callback("Cancelling all tasks")
            else:
                print("Cancelling all tasks")
            return

        except Exception as e:
            if self.error_messages_callback:
                self.error_messages_callback(e)
            else:
                print(e)
            return


class SRTFileReader:
    def __init__(self, srt_file_path, error_messages_callback=None):
        self.timed_subtitles = self(srt_file_path)
        self.error_messages_callback = error_messages_callback

    @staticmethod
    def __call__(srt_file_path):
        try:
            """
            Read SRT formatted subtitles file and return subtitles as list of tuples
            """
            timed_subtitles = []
            with open(srt_file_path, 'r') as srt_file:
                lines = srt_file.readlines()
                # Split the subtitles file into subtitle blocks
                subtitle_blocks = []
                block = []
                for line in lines:
                    if line.strip() == '':
                        subtitle_blocks.append(block)
                        block = []
                    else:
                        block.append(line.strip())
                subtitle_blocks.append(block)

                # Parse each subtitle block and store as tuple in timed_subtitles list
                for block in subtitle_blocks:
                    if block:
                        # Extract start and end times from subtitle block
                        start_time_str, end_time_str = block[1].split(' --> ')
                        time_format = '%H:%M:%S,%f'
                        start_time_time_delta = datetime.strptime(start_time_str, time_format) - datetime.strptime('00:00:00,000', time_format)
                        start_time_total_seconds = start_time_time_delta.total_seconds()
                        end_time_time_delta = datetime.strptime(end_time_str, time_format) - datetime.strptime('00:00:00,000', time_format)
                        end_time_total_seconds = end_time_time_delta.total_seconds()
                        # Extract subtitle text from subtitle block
                        subtitle = ' '.join(block[2:])
                        timed_subtitles.append(((start_time_total_seconds, end_time_total_seconds), subtitle))
                return timed_subtitles

        except KeyboardInterrupt:
            if self.error_messages_callback:
                self.error_messages_callback("Cancelling all tasks")
            else:
                print("Cancelling all tasks")
            return

        except Exception as e:
            if self.error_messages_callback:
                self.error_messages_callback(e)
            else:
                print(e)
            return


class SubtitleStreamParser:
    def __init__(self, error_messages_callback=None):
        self.error_messages_callback = error_messages_callback
        self._indexes = []
        self._languages = []
        self._timed_subtitles = []
        self._number_of_streams = 0

    def __call__(self, media_filepath):
        if "\\" in media_filepath:
            media_filepath = media_filepath.replace("\\", "/")
        subtitle_streams = self.get_subtitle_streams(media_filepath)
        subtitle_streams_data = []
        if subtitle_streams:
            for subtitle_stream in subtitle_streams:
                subtitle_stream_index = subtitle_stream['index']
                subtitle_stream_language = subtitle_stream['language']
                subtitle_streams_data.append((subtitle_stream_index, subtitle_stream_language))

        subtitle_data = []
        subtitle_contents = []

        for subtitle_stream_index in range(len(subtitle_streams)):
            index, language = subtitle_streams_data[subtitle_stream_index]
            self._indexes.append(index)
            self._languages.append(language)
            self._timed_subtitles.append(self.get_timed_subtitles(media_filepath, subtitle_stream_index+1))
            subtitle_data.append((index, language, self.get_timed_subtitles(media_filepath, subtitle_stream_index+1)))

        self._number_of_streams = len(subtitle_data)
        return subtitle_data

    def get_subtitle_streams(self, media_filepath):

        ffprobe_cmd = [
                        'ffprobe',
                        '-hide_banner',
                        '-v', 'error',
                        '-loglevel', 'error',
                        '-print_format', 'json',
                        '-show_entries', 'stream=index:stream_tags=language',
                        '-select_streams', 's',
                        media_filepath
                      ]

        try:
            result = None
            if sys.platform == "win32":
                result = subprocess.run(ffprobe_cmd, stdin=open(os.devnull), capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                result = subprocess.run(ffprobe_cmd, stdin=open(os.devnull), capture_output=True, text=True)

            output = result.stdout

            streams = json.loads(output)['streams']

            subtitle_streams = []
            empty_stream_exists = False

            for index, stream in enumerate(streams, start=1):
                language = stream['tags'].get('language')
                subtitle_streams.append({'index': index, 'language': language})

                # Check if 'No subtitles' stream exists
                if language == 'No subtitles':
                    empty_stream_exists = True

            # Append 'No subtitles' stream if it exists
            if not empty_stream_exists:
                subtitle_streams.append({'index': len(streams) + 1, 'language': 'No subtitles'})

            return subtitle_streams

        except FileNotFoundError:
            if self.error_messages_callback:
                msg = 'ffprobe not found. Make sure it is installed and added to the system PATH.'
                self.error_messages_callback(msg)
            else:
                print(msg)
            return None

        except Exception as e:
            if self.error_messages_callback:
                self.error_messages_callback(e)
            else:
                print(e)
            return None

    def get_timed_subtitles(self, media_filepath, subtitle_stream_index):

        ffmpeg_cmd = [
                        'ffmpeg',
                        '-hide_banner',
                        '-loglevel', 'error',
                        '-v', 'error',
                        '-i', media_filepath,
                        '-map', f'0:s:{subtitle_stream_index-1}',
                        '-f', 'srt',
                        '-'
                     ]

        try:
            result = None
            if sys.platform == "win32":
                result = subprocess.run(ffmpeg_cmd, stdin=open(os.devnull), capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                result = subprocess.run(ffmpeg_cmd, stdin=open(os.devnull), capture_output=True, text=True)

            output = result.stdout

            timed_subtitles = []
            subtitle_data = []
            lines = output.strip().split('\n')
            subtitles = []
            subtitle = None
            subtitle_blocks = []
            block = []
            for line in lines:
                if line.strip() == '':
                    subtitle_blocks.append(block)
                    block = []
                else:
                    block.append(line.strip())
            subtitle_blocks.append(block)

            # Parse each subtitle block and store as tuple in timed_subtitles list
            for block in subtitle_blocks:
                if block:
                    # Extract start and end times from subtitle block
                    start_time_str, end_time_str = block[1].split(' --> ')
                    time_format = '%H:%M:%S,%f'
                    start_time_time_delta = datetime.strptime(start_time_str, time_format) - datetime.strptime('00:00:00,000', time_format)
                    start_time_total_seconds = start_time_time_delta.total_seconds()
                    end_time_time_delta = datetime.strptime(end_time_str, time_format) - datetime.strptime('00:00:00,000', time_format)
                    end_time_total_seconds = end_time_time_delta.total_seconds()
                    # Extract subtitle text from subtitle block
                    subtitle = ' '.join(block[2:])
                    timed_subtitles.append(((start_time_total_seconds, end_time_total_seconds), subtitle))
            return timed_subtitles

        except FileNotFoundError:
            if self.error_messages_callback:
                msg = 'ffmpeg not found. Make sure it is installed and added to the system PATH.'
                self.error_messages_callback(msg)
            else:
                print(msg)
            return None

        except Exception as e:
            if self.error_messages_callback:
                self.error_messages_callback(e)
            else:
                print(e)
            return None

    def number_of_streams(self):
        return self._number_of_streams

    def indexes(self):
        return self._indexes

    def languages(self):
        return self._languages

    def timed_subtitles(self):
        return self._timed_subtitles

    def index_of_language(self, language):
        for i in range(self.number_of_streams()):
            if self.languages()[i] == language:
                return i+1
            return

    def language_of_index(self, index):
        return self.languages()[index-1]

    def timed_subtitles_of_index(self, index):
        return self.timed_subtitles()[index-1]

    def timed_subtitles_of_language(self, language):
        for i in range(self.number_of_streams()):
            if self.languages()[i] == language:
                return self.timed_subtitles()[i]


class MediaSubtitleRenderer:
    @staticmethod
    def which(program):
        def is_exe(file_path):
            return os.path.isfile(file_path) and os.access(file_path, os.X_OK)
        fpath, _ = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file
        return None

    @staticmethod
    def ffmpeg_check():
        if MediaSubtitleRenderer.which("ffmpeg"):
            return "ffmpeg"
        if MediaSubtitleRenderer.which("ffmpeg.exe"):
            return "ffmpeg.exe"
        return None

    def __init__(self, subtitle_path=None, language=None, output_path=None, progress_callback=None, error_messages_callback=None):
        self.subtitle_path = subtitle_path
        self.language = language
        self.output_path = output_path
        self.progress_callback = progress_callback
        self.error_messages_callback = error_messages_callback

    def __call__(self, media_filepath):
        if "\\" in media_filepath:
            media_filepath = media_filepath.replace("\\", "/")

        if "\\" in self.subtitle_path:
            self.subtitle_path = self.subtitle_path.replace("\\", "/")

        if "\\" in self.output_path:
            self.output_path = self.output_path.replace("\\", "/")

        if ":" in self.subtitle_path:
            self.subtitle_path = self.subtitle_path.replace(":", "\:")

        subtitle_path_str = None
        if sys.platform == "win32":
            if ("[" or "]") in str(self.subtitle_path):
                subtitle_path_str = str(self.subtitle_path)
                subtitle_path_str = subtitle_path_str.replace("]", "\]")
                subtitle_path_str = subtitle_path_str.replace("[", "\[")
            else:
                subtitle_path_str = str(self.subtitle_path)
        else:
            subtitle_path_str = str(self.subtitle_path)

        if not os.path.isfile(media_filepath):
            if self.error_messages_callback:
                self.error_messages_callback("The given file does not exist: {0}".format(media_filepath))
            else:
                print("The given file does not exist: {0}".format(media_filepath))
                raise Exception("Invalid file: {0}".format(media_filepath))
        if not self.ffmpeg_check():
            if self.error_messages_callback:
                self.error_messages_callback("ffmpeg: Executable not found on machine.")
            else:
                print("ffmpeg: Executable not found on machine.")
                raise Exception("Dependency not found: ffmpeg")

        try:
            scale_switch = "'trunc(iw/2)*2'\:'trunc(ih/2)*2'"
            ffmpeg_command = [
                                'ffmpeg',
                                '-hide_banner',
                                '-loglevel', 'error',
                                '-v', 'error',
                                '-y',
                                '-i', media_filepath,
                                '-vf', f'subtitles={shlex.quote(subtitle_path_str)},scale={scale_switch}',
                                '-c:v', 'libx264',
                                '-crf', '23',
                                '-preset', 'medium',
                                '-c:a', 'copy',
                                '-progress', '-', '-nostats',
                                self.output_path
                             ]

            media_file_display_name = os.path.basename(media_filepath).split('/')[-1]
            info = f"Rendering subtitles file into '{media_file_display_name}'"
            start_time = time.time()

            ffprobe_command = [
                                'ffprobe',
                                '-hide_banner',
                                '-v', 'error',
                                '-loglevel', 'error',
                                '-show_entries',
                                'format=duration',
                                '-of', 'default=noprint_wrappers=1:nokey=1',
                                media_filepath
                              ]

            ffprobe_process = None
            if sys.platform == "win32":
                ffprobe_process = subprocess.check_output(ffprobe_command, stdin=open(os.devnull), universal_newlines=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                ffprobe_process = subprocess.check_output(ffprobe_command, stdin=open(os.devnull), universal_newlines=True)

            total_duration = float(ffprobe_process.strip())

            process = None
            if sys.platform == "win32":
                process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            while True:
                if process.stdout is None:
                    continue

                stderr_line = (process.stdout.readline().decode("utf-8", errors="replace").strip())
 
                if stderr_line == '' and process.poll() is not None:
                    break

                if "out_time=" in stderr_line:
                    time_str = stderr_line.split('time=')[1].split()[0]
                    current_duration = sum(float(x) * 1000 * 60 ** i for i, x in enumerate(reversed(time_str.split(":"))))

                    if current_duration>0:
                        percentage = int(current_duration*100/(int(float(total_duration))*1000))
                        if self.progress_callback:
                            self.progress_callback(info, media_file_display_name, percentage, start_time)

            if os.path.isfile(self.output_path):
                return self.output_path
            else:
                return None

        except KeyboardInterrupt:
            if self.error_messages_callback:
                self.error_messages_callback("Cancelling all tasks")
            else:
                print("Cancelling all tasks")
            return

        except Exception as e:
            if self.error_messages_callback:
                self.error_messages_callback(e)
            else:
                print(e)
            return


class MediaSubtitleEmbedder:
    @staticmethod
    def which(program):
        def is_exe(file_path):
            return os.path.isfile(file_path) and os.access(file_path, os.X_OK)
        fpath, _ = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file
        return None

    @staticmethod
    def ffmpeg_check():
        if MediaSubtitleEmbedder.which("ffmpeg"):
            return "ffmpeg"
        if MediaSubtitleEmbedder.which("ffmpeg.exe"):
            return "ffmpeg.exe"
        return None

    def __init__(self, subtitle_path=None, language=None, output_path=None, progress_callback=None, error_messages_callback=None):
        self.subtitle_path = subtitle_path
        self.language = language
        self.output_path = output_path
        self.progress_callback = progress_callback
        self.error_messages_callback = error_messages_callback

    def get_existing_subtitle_language(self, media_filepath):
        # Run ffprobe to get stream information
        if "\\" in media_filepath:
            media_filepath = media_filepath.replace("\\", "/")

        command = [
                    'ffprobe',
                    '-hide_banner',
                    '-v', 'error',
                    '-loglevel', 'error',
                    '-of', 'json',
                    '-show_entries',
                    'format:stream',
                    media_filepath
                  ]

        output = None
        if sys.platform == "win32":
            output = subprocess.run(command, stdin=open(os.devnull), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            output = subprocess.run(command, stdin=open(os.devnull), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        metadata = json.loads(output.stdout)
        streams = metadata['streams']

        # Find the subtitle stream with language metadata
        subtitle_languages = []
        for stream in streams:
            if stream['codec_type'] == 'subtitle' and 'tags' in stream and 'language' in stream['tags']:
                language = stream['tags']['language']
                subtitle_languages.append(language)

        return subtitle_languages

    def __call__(self, media_filepath):
        if "\\" in media_filepath:
            media_filepath = media_filepath.replace("\\", "/")

        if "\\" in self.subtitle_path:
            self.subtitle_path = self.subtitle_path.replace("\\", "/")

        if "\\" in self.output_path:
            self.output_path = self.output_path.replace("\\", "/")

        if not os.path.isfile(media_filepath):
            if self.error_messages_callback:
                self.error_messages_callback("The given file does not exist: {0}".format(media_filepath))
            else:
                print("The given file does not exist: {0}".format(media_filepath))
                raise Exception("Invalid file: {0}".format(media_filepath))
        if not self.ffmpeg_check():
            if self.error_messages_callback:
                self.error_messages_callback("ffmpeg: Executable not found on machine.")
            else:
                print("ffmpeg: Executable not found on machine.")
                raise Exception("Dependency not found: ffmpeg")

        try:
            existing_languages = self.get_existing_subtitle_language(media_filepath)
            if self.language in existing_languages:
                # THIS 'print' THINGS WILL MAKE progresbar screwed up!
                #msg = (f"'{self.language}' subtitle stream already existed in {media_filepath}")
                #if self.error_messages_callback:
                #    self.error_messages_callback(msg)
                #else:
                #    print(msg)
                return

            else:
                # Determine the next available subtitle index
                next_index = len(existing_languages)

                ffmpeg_command = [
                                    'ffmpeg',
                                    '-hide_banner',
                                    '-loglevel', 'error',
                                    '-v', 'error',
                                    '-y',
                                    '-i', media_filepath,
                                    '-sub_charenc', 'UTF-8',
                                    '-i', self.subtitle_path,
                                    '-c:v', 'copy',
                                    '-c:a', 'copy',
                                    '-scodec', 'mov_text',
                                    '-metadata:s:s:' + str(next_index), f'language={shlex.quote(self.language)}',
                                    '-map', '0',
                                    '-map', '1',
                                    '-progress', '-', '-nostats',
                                    self.output_path
                                 ]

                subtitle_file_display_name = os.path.basename(self.subtitle_path).split('/')[-1]
                media_file_display_name = os.path.basename(media_filepath).split('/')[-1]
                info = f"Embedding '{self.language}' subtitles file '{subtitle_file_display_name}' into '{media_file_display_name}'"
                start_time = time.time()

                ffprobe_command = [
                                    'ffprobe',
                                    '-hide_banner',
                                    '-v', 'error',
                                    '-loglevel', 'error',
                                    '-show_entries',
                                    'format=duration',
                                    '-of', 'default=noprint_wrappers=1:nokey=1',
                                    media_filepath
                                  ]

                ffprobe_process = None
                if sys.platform == "win32":
                    ffprobe_process = subprocess.check_output(ffprobe_command, stdin=open(os.devnull), universal_newlines=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    ffprobe_process = subprocess.check_output(ffprobe_command, stdin=open(os.devnull), universal_newlines=True)

                total_duration = float(ffprobe_process.strip())

                process = None
                if sys.platform == "win32":
                    process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

                while True:
                    if process.stdout is None:
                        continue

                    stderr_line = (process.stdout.readline().decode("utf-8", errors="replace").strip())
 
                    if stderr_line == '' and process.poll() is not None:
                        break

                    if "out_time=" in stderr_line:
                        time_str = stderr_line.split('time=')[1].split()[0]
                        current_duration = sum(float(x) * 1000 * 60 ** i for i, x in enumerate(reversed(time_str.split(":"))))

                        if current_duration>0:
                            percentage = int(current_duration*100/(int(float(total_duration))*1000))
                            if self.progress_callback:
                                self.progress_callback(info, media_file_display_name, percentage, start_time)

                if os.path.isfile(self.output_path):
                    return self.output_path
                else:
                    return None

                if os.path.isfile(self.output_path):
                    return self.output_path
                else:
                    return None

        except KeyboardInterrupt:
            if self.error_messages_callback:
                self.error_messages_callback("Cancelling all tasks")
            else:
                print("Cancelling all tasks")
            return

        except Exception as e:
            if self.error_messages_callback:
                self.error_messages_callback(e)
            else:
                print(e)
            return


class MediaSubtitleRemover:
    @staticmethod
    def which(program):
        def is_exe(file_path):
            return os.path.isfile(file_path) and os.access(file_path, os.X_OK)
        fpath, _ = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file
        return None

    @staticmethod
    def ffmpeg_check():
        if MediaSubtitleRemover.which("ffmpeg"):
            return "ffmpeg"
        if MediaSubtitleRemover.which("ffmpeg.exe"):
            return "ffmpeg.exe"
        return None

    def __init__(self, output_path=None, progress_callback=None, error_messages_callback=None):
        self.output_path = output_path
        self.progress_callback = progress_callback
        self.error_messages_callback = error_messages_callback

    def __call__(self, media_filepath):
        if "\\" in media_filepath:
            media_filepath = media_filepath.replace("\\", "/")

        if "\\" in self.output_path:
            self.output_path = self.output_path.replace("\\", "/")

        if not os.path.isfile(media_filepath):
            if self.error_messages_callback:
                self.error_messages_callback("The given file does not exist: {0}".format(media_filepath))
            else:
                print("The given file does not exist: {0}".format(media_filepath))
                raise Exception("Invalid file: {0}".format(media_filepath))
        if not self.ffmpeg_check():
            if self.error_messages_callback:
                self.error_messages_callback("ffmpeg: Executable not found on machine.")
            else:
                print("ffmpeg: Executable not found on machine.")
                raise Exception("Dependency not found: ffmpeg")

        try:
            ffmpeg_command = [
                                'ffmpeg',
                                '-hide_banner',
                                '-loglevel', 'error',
                                '-v', 'error',
                                '-y',
                                '-i', media_filepath,
                                '-c', 'copy',
                                '-sn',
                                '-progress', '-', '-nostats',
                                self.output_path
                             ]

            media_file_display_name = os.path.basename(media_filepath).split('/')[-1]
            info = f"Removing subtitle streams from '{media_file_display_name}'"
            start_time = time.time()

            ffprobe_command = [
                                'ffprobe',
                                '-hide_banner',
                                '-v', 'error',
                                '-loglevel', 'error',
                                '-show_entries',
                                'format=duration',
                                '-of', 'default=noprint_wrappers=1:nokey=1',
                                media_filepath
                              ]

            ffprobe_process = None
            if sys.platform == "win32":
                ffprobe_process = subprocess.check_output(ffprobe_command, stdin=open(os.devnull), universal_newlines=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                ffprobe_process = subprocess.check_output(ffprobe_command, stdin=open(os.devnull), universal_newlines=True)

            total_duration = float(ffprobe_process.strip())

            process = None
            if sys.platform == "win32":
                process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            while True:
                if process.stdout is None:
                    continue

                stderr_line = (process.stdout.readline().decode("utf-8", errors="replace").strip())
 
                if stderr_line == '' and process.poll() is not None:
                    break

                if "out_time=" in stderr_line:
                    time_str = stderr_line.split('time=')[1].split()[0]
                    current_duration = sum(float(x) * 1000 * 60 ** i for i, x in enumerate(reversed(time_str.split(":"))))

                    if current_duration>0:
                        percentage = int(current_duration*100/(int(float(total_duration))*1000))
                        if self.progress_callback:
                            self.progress_callback(info, media_file_display_name, percentage, start_time)

            if os.path.isfile(self.output_path):
                return self.output_path
            else:
                return None

            if os.path.isfile(self.output_path):
                return self.output_path
            else:
                return None

        except KeyboardInterrupt:
            if self.error_messages_callback:
                self.error_messages_callback("Cancelling all tasks")
            else:
                print("Cancelling all tasks")
            return

        except Exception as e:
            if self.error_messages_callback:
                self.error_messages_callback(e)
            else:
                print(e)
            return


#=======================================================================================================================================#

#----------------------------------------------------------- MISC FUNCTIONS -----------------------------------------------------------#


def stop_thread(thread):
    global main_window
    exc = ctypes.py_object(SystemExit)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread.ident), exc)
    if res == 0:
        main_window.write_event_value("-EXCEPTION-", "nonexistent thread id")
        #raise ValueError("nonexistent thread id")
    elif res > 1:
        # '''if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect'''
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)
        main_window.write_event_value("-EXCEPTION-", "PyThreadState_SetAsyncExc failed")
        #raise SystemError("PyThreadState_SetAsyncExc failed")


def popup_yes_no(text, title=None):
    layout = [
        [sg.Text(text, size=(24,1))],
        [sg.Push(), sg.Button('Yes', bind_return_key=True), sg.Button('No', bind_return_key=True, focus=True)],
    ]
    return sg.Window(title if title else text, layout, resizable=True, return_keyboard_events=True).read(close=True)


def move_center(window):
    screen_width, screen_height = window.get_screen_dimensions()
    win_width, win_height = window.size
    x, y = (screen_width-win_width)//2, ((screen_height-win_height)//2) - 30
    window.move(x, y)
    window.refresh()

def get_clipboard_text():
    try:
        clipboard_data = subprocess.check_output(['xclip', '-selection', 'clipboard', '-o'], universal_newlines=True)
        return clipboard_data.strip()
    except subprocess.CalledProcessError:
        # Handle the case when clipboard is empty or unsupported
        return None


def set_clipboard_text(text):
    try:
        subprocess.run(['xclip', '-selection', 'clipboard'], input=text.encode())
    except subprocess.CalledProcessError as e:
        show_error_messages(e)


def scroll_to_last_line(window, element):
    if isinstance(element.Widget, tk.Text):
        # Get the number of lines in the Text element
        num_lines = element.Widget.index('end-1c').split('.')[0]

        # Scroll to the last line
        element.Widget.see(f"{num_lines}.0")

    elif isinstance(element.Widget, tk.Label):
        # Scroll the Label text
        element.Widget.configure(text=element.get())
    
    # Update the window to show the scroll position
    window.refresh()


def set_right_click_menu(element, enabled):
    if enabled:
        #print("element = {}".format(element))
        #print("enabled = {}".format(enabled))

        if isinstance(element, sg.Input):
            widget = element.Widget
        elif isinstance(element, sg.Multiline):
            widget = element.Widget

        menu = tk.Menu(widget, tearoff=False)
        menu.add_command(label="Copy", command=lambda: element.Widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: element.Widget.event_generate("<<Paste>>"))
        widget.bind("<Button-3>", lambda event: menu.tk_popup(event.x_root, event.y_root))

    else:
        element.Widget.unbind("<Button-3>")
        element.Widget.bind("<Button-3>", lambda x: None)


class NoConsoleProcess(multiprocessing.Process):
    def __init__(self, *args, **kwargs):
        '''
        if hasattr(multiprocessing, 'get_all_start_methods') and 'spawn' in multiprocessing.get_all_start_methods():
            # If running on Windows
            kwargs['start_method'] = 'spawn'
        '''
        super().__init__(*args, **kwargs)
        self.queue = multiprocessing.Queue()

    def run(self):
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        try:
            super().run()
        except Exception as e:
            self.queue.put(('error', str(e)))
        else:
            self.queue.put(('done', None))


def is_streaming_url(url, error_messages_callback=None):

    streamlink = Streamlink()

    if is_valid_url(url):
        #print("is_valid_url(url) = {}".format(is_valid_url(url)))
        try:
            os.environ['STREAMLINK_DIR'] = './streamlink/'
            os.environ['STREAMLINK_PLUGINS'] = './streamlink/plugins/'
            os.environ['STREAMLINK_PLUGIN_DIR'] = './streamlink/plugins/'

            streams = streamlink.streams(url)
            if streams:
                #print("is_streams = {}".format(True))
                return True
            else:
                #print("is_streams = {}".format(False))
                return False

        except OSError:
            #print("is_streams = OSError")
            if error_messages_callback:
                error_messages_callback("OSError")
            return False
        except ValueError:
            #print("is_streams = ValueError")
            if error_messages_callback:
                error_messages_callback("ValueError")
            return False
        except KeyError:
            #print("is_streams = KeyError")
            if error_messages_callback:
                error_messages_callback("KeyError")
            return False
        except RuntimeError:
            #print("is_streams = RuntimeError")
            if error_messages_callback:
                error_messages_callback("RuntimeError")
            return False
        except NoPluginError:
            #print("is_streams = NoPluginError")
            if error_messages_callback:
                error_messages_callback("NoPluginError")
            return False
        except StreamlinkError:
            return False
            #print("is_streams = StreamlinkError")
            if error_messages_callback:
                error_messages_callback("StreamlinkError")
        except StreamError:
            return False
            #print("is_streams = StreamlinkError")
            if error_messages_callback:
                error_messages_callback("StreamError")
        except NotImplementedError:
            #print("is_streams = NotImplementedError")
            if error_messages_callback:
                error_messages_callback("NotImplementedError")
            return False
        except Exception as e:
            #print("is_streams = {}".format(e))
            if error_messages_callback:
                error_messages_callback(e)
            return False
    else:
        #print("is_valid_url(url) = {}".format(is_valid_url(url)))
        return False


def is_valid_url(url, error_messages_callback=None):
    try:
        response = httpx.head(url)
        response.raise_for_status()
        return True
    except (httpx.HTTPError, ValueError) as e:
        if error_messages_callback:
            error_messages_callback(e)
        else:
            print(e)
        return False
    except Exception as e:
        if error_messages_callback:
            error_messages_callback(e)
        else:
            print(e)
        return False


def record_streaming_windows(hls_url, media_filepath, error_messages_callback=None):
    global not_recording, main_window

    try:
        ffmpeg_cmd = [
                        'ffmpeg',
                        '-hide_banner',
                        '-loglevel', 'error',
                        '-v', 'error',
                        '-y',
                        '-i', hls_url,
                        '-movflags', '+frag_keyframe+separate_moof+omit_tfhd_offset+empty_moov',
                        '-fflags', 'nobuffer',
                        media_filepath
                     ]

        if sys.platform == "win32":
            process = subprocess.Popen(ffmpeg_cmd, shell=True, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            process = subprocess.Popen(ffmpeg_cmd, stderr=subprocess.PIPE)

        msg = "RECORDING"
        main_window.write_event_value('-EVENT-THREAD-RECORD-STREAMING-STATUS-', msg)

        while not not_recording:
            if not_recording:
                break

            for line in iter(process.stderr.readline, b''):
                line = line.decode('utf-8').rstrip()

                if 'time=' in line:
                    time_str = line.split('time=')[1].split()[0]
                    streaming_duration_recorded = datetime.strptime(time_str, "%H:%M:%S.%f") - datetime(1900, 1, 1)
                    main_window.write_event_value('-EVENT-STREAMING-DURATION-RECORDED-', streaming_duration_recorded)

        process.wait()

    except Exception as e:
        if error_messages_callback:
            error_messages_callback(e)
        else:
            print(e)


# subprocess.Popen(ffmpeg_cmd) THREAD BEHAVIOR IS DIFFERENT IN LINUX
def record_streaming_linux(url, output_file, error_messages_callback=None):
    global recognizing, ffmpeg_start_run_time, first_streaming_duration_recorded, main_window

    #ffmpeg_cmd = ['ffmpeg', '-y', '-i', url, '-c', 'copy', '-bsf:a', 'aac_adtstoasc', '-f', 'mp4', output_file]
    ffmpeg_cmd = [
                    'ffmpeg',
                    '-hide_banner',
                    '-loglevel', 'error',
                    '-v', 'error',
                    '-y',
                    '-i', f'{url}',
                    '-movflags',
                    '+frag_keyframe+separate_moof+omit_tfhd_offset+empty_moov',
                    '-fflags',
                    'nobuffer',
                    f'{output_file}'
                 ]

    ffmpeg_start_run_time = datetime.now()

    # Define a function to run the ffmpeg process in a separate thread
    def run_ffmpeg():
        try:
            i = 0
            line = None

            process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

            msg = "RECORDING"
            main_window.write_event_value('-EVENT-THREAD-RECORD-STREAMING-STATUS-', msg)

            # Set up a timer to periodically check for new output
            timeout = 1.0
            timer = Timer(timeout, lambda: None)
            timer.start()

            # Read output from ffmpeg process
            while not not_recording:
                # Check if the process has finished
                if process.poll() is not None:
                    break

                # Check if there is new output to read, special for linux
                rlist, _, _ = select.select([process.stderr], [], [], timeout)
                if not rlist:
                    continue

                # Read the new output and print it
                line = rlist[0].readline().strip()
                #print(line)

                # Search for the time information in the output and print it
                time_str = re.search(r'time=(\d+:\d+:\d+\.\d+)', line)

                if time_str:
                    time_value = time_str.group(1)
                    #print(f"Time: {time_value}")

                    if i == 0:
                        ffmpeg_start_write_time = datetime.now()
                        #print("ffmpeg_start_write_time = {}".format(ffmpeg_start_write_time))

                        first_streaming_duration_recorded = datetime.strptime(str(time_value), "%H:%M:%S.%f") - datetime(1900, 1, 1)
                        #print("first_streaming_duration_recorded = {}".format(first_streaming_duration_recorded))

                        # MAKE SURE THAT first_streaming_duration_recorded EXECUTED ONLY ONCE
                        i += 1

                        #print("writing time_value")
                        time_value_filename = "time_value"
                        time_value_filepath = os.path.join(tempfile.gettempdir(), time_value_filename)
                        time_value_file = open(time_value_filepath, "w")
                        time_value_file.write(str(time_value))
                        time_value_file.close()
                        #print("time_value = {}".format(time_value))

                    streaming_duration_recorded = datetime.strptime(str(time_value), "%H:%M:%S.%f") - datetime(1900, 1, 1)
                    #print("streaming_duration_recorded = {}".format(streaming_duration_recorded))
                    main_window.write_event_value('-EVENT-STREAMING-DURATION-RECORDED-', streaming_duration_recorded)

                # Restart the timer to check for new output
                timer.cancel()
                timer = Timer(timeout, lambda: None)
                if not not_recording: timer.start()

            # Close the ffmpeg process and print the return code
            process.stdout.close()
            process.stderr.close()

        except Exception as e:
            if error_messages_callback:
                error_messages_callback(e)
            else:
                print(e)

        # Start the thread to run ffmpeg
        thread = Thread(target=run_ffmpeg)
        if not not_recording: thread.start()

        # Return the thread object so that the caller can join it if needed
        return thread


def stop_record_streaming_windows():
    global main_window, thread_record_streaming

    if thread_record_streaming and thread_record_streaming.is_alive():
        # Use ctypes to call the TerminateThread() function from the Windows API
        # This forcibly terminates the thread, which can be unsafe in some cases
        kernel32 = ctypes.windll.kernel32
        thread_handle = kernel32.OpenThread(1, False, thread_record_streaming.ident)
        ret = kernel32.TerminateThread(thread_handle, 0)
        if ret == 0:
            msg = "TERMINATION ERROR!"
        else:
            msg = "TERMINATED"
            thread_record_streaming = None
        if main_window: main_window.write_event_value('-EVENT-THREAD-RECORD-STREAMING-STATUS-', msg)

        tasklist_output = subprocess.check_output(['tasklist'], creationflags=subprocess.CREATE_NO_WINDOW).decode('utf-8')
        ffmpeg_pid = None
        for line in tasklist_output.split('\n'):
            if "ffmpeg" in line:
                ffmpeg_pid = line.split()[1]
                break
        if ffmpeg_pid:
            devnull = open(os.devnull, 'w')
            subprocess.Popen(['taskkill', '/F', '/T', '/PID', ffmpeg_pid], stdout=devnull, stderr=devnull, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            msg = 'FFMPEG HAS TERMINATED'
            if main_window: main_window.write_event_value('-EVENT-THREAD-RECORD-STREAMING-STATUS-', msg)

    else:
        msg = "NOT RECORDING"
        main_window.write_event_value('-EVENT-THREAD-RECORD-STREAMING-STATUS-', msg)


def stop_record_streaming_linux():
    global main_window, thread_record_streaming

    if thread_record_streaming and thread_record_streaming.is_alive():
        print("thread_record_streaming.is_alive()")
        exc = ctypes.py_object(SystemExit)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_record_streaming.ident), exc)
        if res == 0:
            raise ValueError("nonexistent thread id")
        elif res > 1:
            # '''if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect'''
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_record_streaming.ident, None)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    msg = "TERMINATED"
    if main_window: main_window.write_event_value('-EVENT-THREAD-RECORD-STREAMING-STATUS-', msg)

    ffmpeg_pid = subprocess.check_output(['pgrep', '-f', 'ffmpeg']).strip()
    if ffmpeg_pid:
        subprocess.Popen(['kill', ffmpeg_pid])
    else:
        msg = 'FFMPEG HAS TERMINATED'
        if main_window: main_window.write_event_value('-EVENT-THREAD-RECORD-STREAMING-STATUS-', msg)


def show_progress(info, media_file_display_name, progress, start_time):
    global main_window
    total = 100
    percentage = f'{progress}%'
    if progress > 0:
        elapsed_time = time.time() - start_time
        eta_seconds = (elapsed_time / progress) * (total - progress)
    else:
        eta_seconds = 0
    eta_time = timedelta(seconds=int(eta_seconds))
    eta_str = str(eta_time)
    hour, minute, second = eta_str.split(":")
    main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (media_file_display_name, info, total, percentage, progress, hour.zfill(2), minute, second))
    if progress == total:
        elapsed_time_seconds = timedelta(seconds=int(elapsed_time))
        elapsed_time_str = str(elapsed_time_seconds)
        hour, minute, second = elapsed_time_str.split(":")
        main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (media_file_display_name, info, total, "100%", total, hour.zfill(2), minute, second))


def show_error_messages(messages):
    global main_window, not_transcribing
    not_transcribing = True
    main_window.write_event_value("-EXCEPTION-", messages)


def transcribe(src, dst, media_filepath, media_type, subtitle_format, embed_src, embed_dst, force_recognize):
    global main_window, language, thread_remove_subtitles, thread_transcribe, thread_transcribe_starter, not_transcribing, pool, \
            removed_media_filepaths, completed_tasks, start_time

    media_file_display_name = os.path.basename(media_filepath).split('/')[-1]

    results = []

    # CHECKING SUBTITLE STREAMS
    if force_recognize == False:

        #media_file_display_name = os.path.basename(media_filepath).split('/')[-1]
        src_subtitle_filepath = None
        dst_subtitle_filepath = None
        src_embedded_media_filepath = None
        dst_embedded_media_filepath = None
        ffmpeg_src_language_code = None
        ffmpeg_dst_language_code = None

        # NO TRANSLATE (src == dst)
        # CHECKING ffmpeg_src_language_code SUBTITLE STREAM ONLY, IF EXISTS WE PRINT IT AND EXTRACT IT
        if is_same_language(src, dst, error_messages_callback=show_error_messages):

            if not_transcribing: return

            ffmpeg_src_language_code = language.ffmpeg_code_of_code[src]

            subtitle_stream_parser = SubtitleStreamParser(error_messages_callback=show_error_messages)
            subtitle_streams_data = subtitle_stream_parser(media_filepath)

            window_key = '-PROGRESS-LOG-'
            msg = f"Checking '{media_file_display_name}'\n"
            append_flag = True
            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

            if not_transcribing: return

            if subtitle_streams_data and subtitle_streams_data != []:

                src_subtitle_stream_timed_subtitles = subtitle_stream_parser.timed_subtitles_of_language(ffmpeg_src_language_code)

                if ffmpeg_src_language_code in subtitle_stream_parser.languages():

                    if not_transcribing: return

                    window_key = '-PROGRESS-LOG-'
                    msg = f"Is '{media_file_display_name}' has '{ffmpeg_src_language_code}' subtitle stream : Yes\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    subtitle_stream_regions = []
                    subtitle_stream_transcripts = []
                    for entry in src_subtitle_stream_timed_subtitles:
                        subtitle_stream_regions.append(entry[0])
                        subtitle_stream_transcripts.append(entry[1])

                    base, ext = os.path.splitext(media_filepath)
                    src_subtitle_filepath = f"{base}.{src}.{subtitle_format}"
                    src_subtitle_file_display_name = os.path.basename(src_subtitle_filepath).split('/')[-1]

                    writer = SubtitleWriter(subtitle_stream_regions, subtitle_stream_transcripts, subtitle_format, error_messages_callback=show_error_messages)
                    writer.write(src_subtitle_filepath)

                    if os.path.isfile(src_subtitle_filepath) and src_subtitle_filepath not in results:
                        results.append(src_subtitle_filepath)

                    if not_transcribing: return

                    window_key = '-PROGRESS-LOG-'
                    msg = f"Extracting '{media_file_display_name}' '{ffmpeg_src_language_code}' subtitle stream as :\n  '{src_subtitle_filepath}'\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    if not_transcribing: return

                    # no translate process

                    # print overall results
                    if os.path.isfile(src_subtitle_filepath):

                        window_key = '-RESULTS-'
                        msg = f"Results for '{media_file_display_name}' :\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        for result in results:
                            window_key = '-RESULTS-'
                            msg = f"{result}\n"
                            append_flag = True
                            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        window_key = '-RESULTS-'
                        msg = "\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        # remove media_filepath from transcribe proceed_list
                        if force_recognize == False:
                            if media_filepath not in removed_media_filepaths:
                                removed_media_filepaths.append(media_filepath)

                        completed_tasks += 1
                        main_window.write_event_value('-EVENT-TRANSCRIBE-TASKS-COMPLETED-', completed_tasks)

                    if embed_src == True:
                        window_key = '-PROGRESS-LOG-'
                        msg = f"No need to embed '{ffmpeg_src_language_code}' subtitle into '{media_file_display_name}' because it's already existed\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                else:
                    window_key = '-PROGRESS-LOG-'
                    msg = f"Is '{media_file_display_name}' has '{ffmpeg_src_language_code}' subtitle stream : No\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    if not_transcribing: return

            if not_transcribing: return

        # DO TRANSLATE (src != dst)
        # CHECKING ffmpeg_src_language_code AND ffmpeg_dst_language_code SUBTITLE STREAMS, IF EXISTS WE PRINT IT AND EXTRACT IT
        # IF ONE OF THEM (ffmpeg_src_language_code OR ffmpeg_dst_language_code) NOT EXIST, WE TRANSLATE IT,
        # AND IF BOOLEAN VALUE FOR EMBED (FOR SRC OR DST LANGUAGE) IS TRUE THEN WE EMBED IT
        elif not is_same_language(src, dst, error_messages_callback=show_error_messages):

            if not_transcribing: return

            ffmpeg_src_language_code = language.ffmpeg_code_of_code[src]
            ffmpeg_dst_language_code = language.ffmpeg_code_of_code[dst]

            subtitle_stream_parser = SubtitleStreamParser(error_messages_callback=show_error_messages)
            subtitle_streams_data = subtitle_stream_parser(media_filepath)

            if not_transcribing: return

            window_key = '-PROGRESS-LOG-'
            msg = f"Checking '{media_file_display_name}'\n"
            append_flag = True
            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

            if subtitle_streams_data and subtitle_streams_data != []:

                if not_transcribing: return

                src_subtitle_stream_timed_subtitles = subtitle_stream_parser.timed_subtitles_of_language(ffmpeg_src_language_code)
                dst_subtitle_stream_timed_subtitles = subtitle_stream_parser.timed_subtitles_of_language(ffmpeg_dst_language_code)

                # ffmpeg_src_language_code subtitle stream exist, we print it and extract it
                if ffmpeg_src_language_code in subtitle_stream_parser.languages():

                    if not_transcribing: return

                    window_key = '-PROGRESS-LOG-'
                    msg = f"Is '{media_file_display_name}' has '{ffmpeg_src_language_code}' subtitle stream : Yes\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    subtitle_stream_regions = []
                    subtitle_stream_transcripts = []
                    for entry in src_subtitle_stream_timed_subtitles:
                        subtitle_stream_regions.append(entry[0])
                        subtitle_stream_transcripts.append(entry[1])
                        if not_transcribing: return

                    base, ext = os.path.splitext(media_filepath)
                    src_subtitle_filepath = f"{base}.{src}.{subtitle_format}"

                    writer = SubtitleWriter(subtitle_stream_regions, subtitle_stream_transcripts, subtitle_format, error_messages_callback=show_error_messages)
                    writer.write(src_subtitle_filepath)

                    if os.path.isfile(src_subtitle_filepath) and src_subtitle_filepath not in results:
                        results.append(src_subtitle_filepath)

                    window_key = '-PROGRESS-LOG-'
                    msg = f"Extracting '{media_file_display_name}' '{ffmpeg_src_language_code}' subtitle stream as :\n  '{src_subtitle_filepath}'\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    if not_transcribing: return

                    if embed_src == True:
                        window_key = '-PROGRESS-LOG-'
                        msg = f"No need to embed '{ffmpeg_src_language_code}' subtitle into '{media_file_display_name}' because it's already existed\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                # ffmpeg_src_language_code subtitle stream not exist, just print it
                else:
                    window_key = '-PROGRESS-LOG-'
                    msg = f"Is '{media_file_display_name}' has '{ffmpeg_src_language_code}' subtitle stream : No\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    if not_transcribing: return

                # ffmpeg_dst_language_code subtitle stream exist, so we print it and extract it
                if ffmpeg_dst_language_code in subtitle_stream_parser.languages():

                    if not_transcribing: return

                    window_key = '-PROGRESS-LOG-'
                    msg = f"Is '{media_file_display_name}' has '{ffmpeg_dst_language_code}' subtitle stream : Yes\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    subtitle_stream_regions = []
                    subtitle_stream_transcripts = []
                    for entry in dst_subtitle_stream_timed_subtitles:
                        subtitle_stream_regions.append(entry[0])
                        subtitle_stream_transcripts.append(entry[1])
                        if not_transcribing: return

                    base, ext = os.path.splitext(media_filepath)
                    dst_subtitle_filepath = f"{base}.{dst}.{subtitle_format}"
                    dst_subtitle_file_display_name = os.path.basename(dst_subtitle_filepath).split('/')[-1]

                    writer = SubtitleWriter(subtitle_stream_regions, subtitle_stream_transcripts, subtitle_format, error_messages_callback=show_error_messages)
                    writer.write(dst_subtitle_filepath)

                    if os.path.isfile(dst_subtitle_filepath) and dst_subtitle_filepath not in results:
                        results.append(dst_subtitle_filepath)

                    if not_transcribing: return

                    window_key = '-PROGRESS-LOG-'
                    msg = f"Extracting '{media_file_display_name}' '{ffmpeg_dst_language_code}' subtitle stream as :\n  '{dst_subtitle_filepath}'\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    if embed_dst == True:
                        window_key = '-PROGRESS-LOG-'
                        msg = f"No need to embed '{ffmpeg_dst_language_code}' subtitle into '{media_file_display_name}' because it's already existed\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    if not_transcribing: return

                # ffmpeg_dst_language_code subtitle stream not exist, just print it
                else:
                    window_key = '-PROGRESS-LOG-'
                    msg = f"Is '{media_file_display_name}' has '{ffmpeg_dst_language_code}' subtitle stream : No\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    if not_transcribing: return

                # ffmpeg_src_language_code subtitle stream = not exist,
                # ffmpeg_dst_language_code subtitle stream = exist
                # so we translate it from 'dst' to 'src'
                if ffmpeg_src_language_code not in subtitle_stream_parser.languages() and ffmpeg_dst_language_code in subtitle_stream_parser.languages():

                    if dst_subtitle_stream_timed_subtitles and dst_subtitle_stream_timed_subtitles != []:

                        if not_transcribing: return

                        window_key = '-PROGRESS-LOG-'
                        msg = f"Translating '{media_file_display_name}' subtitles from {language.name_of_code[dst]} ({dst}) to {language.name_of_code[src]} ({src})...\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        info = f"Translating '{media_file_display_name}' subtitles from {language.name_of_code[dst]} ({dst}) to {language.name_of_code[src]} ({src})"
                        total = 100
                        start_time = time.time()

                        transcript_translator = SentenceTranslator(src=dst, dst=src, error_messages_callback=show_error_messages)

                        if not_transcribing: return

                        translated_subtitle_stream_transcripts = []

                        for i, translated_subtitle_stream_transcript in enumerate(pool[media_filepath].imap(transcript_translator, subtitle_stream_transcripts)):

                            if not_transcribing:
                                if pool[media_filepath]:
                                    pool[media_filepath].terminate()
                                    pool[media_filepath].close()
                                    pool[media_filepath].join()
                                    pool[media_filepath] = None
                                return

                            translated_subtitle_stream_transcripts.append(translated_subtitle_stream_transcript)

                            progress = int(i*100/len(dst_subtitle_stream_timed_subtitles))
                            percentage = f'{progress}%'

                            if progress > 0:
                                elapsed_time = time.time() - start_time
                                eta_seconds = (elapsed_time / progress) * (total - progress)
                            else:
                                eta_seconds = 0
                            eta_time = timedelta(seconds=int(eta_seconds))
                            eta_str = str(eta_time)
                            hour, minute, second = eta_str.split(":")
                            main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (media_file_display_name, info, total, percentage, progress, hour.zfill(2), minute, second))

                        elapsed_time = time.time() - start_time
                        elapsed_time_seconds = timedelta(seconds=int(elapsed_time))
                        elapsed_time_str = str(elapsed_time_seconds)
                        hour, minute, second = elapsed_time_str.split(":")
                        main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (media_file_display_name, info, total, "100%", total, hour.zfill(2), minute, second))

                        if not_transcribing:
                            if pool[media_filepath]:
                                pool[media_filepath].terminate()
                                pool[media_filepath].close()
                                pool[media_filepath].join()
                                pool[media_filepath] = None
                            return

                        window_key = '-PROGRESS-LOG-'
                        msg = f"Writing '{media_file_display_name}' translated subtitles file...\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        base, ext = os.path.splitext(media_filepath)
                        src_subtitle_filepath = f"{base}.{src}.{subtitle_format}"
                        src_subtitle_file_display_name = os.path.basename(src_subtitle_filepath).split('/')[-1]

                        translation_writer = SubtitleWriter(subtitle_stream_regions, translated_subtitle_stream_transcripts, subtitle_format, error_messages_callback=show_error_messages)
                        translation_writer.write(src_subtitle_filepath)

                        if os.path.isfile(src_subtitle_filepath) and src_subtitle_filepath not in results:
                            results.append(src_subtitle_filepath)

                        if not_transcribing:
                            if pool[media_filepath]:
                                pool[media_filepath].terminate()
                                pool[media_filepath].close()
                                pool[media_filepath].join()
                                pool[media_filepath] = None
                            return

                        window_key = '-PROGRESS-LOG-'
                        msg = f"'{media_file_display_name}' translated subtitles file saved as :\n  '{src_subtitle_filepath}'\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        # if embed_src is True then we embed that translated srt (from dst to src) above into media_filepath
                        if embed_src == True:

                            if not_transcribing:
                                if pool[media_filepath]:
                                    pool[media_filepath].terminate()
                                    pool[media_filepath].close()
                                    pool[media_filepath].join()
                                    pool[media_filepath] = None
                                return

                            ffmpeg_src_language_code = language.ffmpeg_code_of_code[src]

                            base, ext = os.path.splitext(media_filepath)

                            src_tmp_embedded_media_filepath = f"{base}.{ffmpeg_src_language_code}.tmp.embedded.{ext[1:]}"
                            src_tmp_embedded_media_file_display_name = os.path.basename(src_tmp_embedded_media_filepath).split('/')[-1]

                            src_embedded_media_filepath = f"{base}.{ffmpeg_src_language_code}.embedded.{ext[1:]}"
                            src_embedded_media_file_display_name = os.path.basename(src_embedded_media_filepath).split('/')[-1]

                            window_key = '-PROGRESS-LOG-'
                            msg = f"Embedding '{ffmpeg_src_language_code}' subtitles file '{src_subtitle_file_display_name}' into '{media_file_display_name}'"
                            append_flag = True
                            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                            if not_transcribing:
                                if pool[media_filepath]:
                                    pool[media_filepath].terminate()
                                    pool[media_filepath].close()
                                    pool[media_filepath].join()
                                    pool[media_filepath] = None
                                return

                            try:
                                subtitle_embedder = MediaSubtitleEmbedder(subtitle_path=src_subtitle_filepath, language=ffmpeg_src_language_code, output_path=src_tmp_embedded_media_filepath, progress_callback=show_progress, error_messages_callback=show_error_messages)
                                src_tmp_output = subtitle_embedder(media_filepath)
                            except Exception as e:
                                not_transcribing = True
                                main_window.write_event_value("-EXCEPTION-", e)
                                return

                            if not_transcribing:
                                if pool[media_filepath]:
                                    pool[media_filepath].terminate()
                                    pool[media_filepath].close()
                                    pool[media_filepath].join()
                                    pool[media_filepath] = None
                                return

                            if os.path.isfile(src_tmp_output):
                                window_key = '-PROGRESS-LOG-'
                                msg = f"Copying '{src_tmp_embedded_media_file_display_name}' to {src_embedded_media_file_display_name}...\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                shutil.copy(src_tmp_output, src_embedded_media_filepath)
                                os.remove(src_tmp_output)

                                if src_embedded_media_filepath not in results:
                                    results.append(src_embedded_media_filepath)

                            if os.path.isfile(src_embedded_media_filepath):
                                window_key = '-PROGRESS-LOG-'
                                msg = f"'{media_file_display_name}' subtitles embedded {media_type} file saved as :\n  '{src_embedded_media_filepath}'\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                            else:
                                window_key = '-PROGRESS-LOG-'
                                msg = "Unknown error\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        # if args.embed_dst is True we can't embed it because dst subtitle stream already exist
                        if embed_dst == True:
                            window_key = '-PROGRESS-LOG-'
                            msg = f"No need to embed '{ffmpeg_dst_language_code}' subtitle into '{media_file_display_name}' because it's already existed\n"
                            append_flag = True
                            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        if not_transcribing:
                            if pool[media_filepath]:
                                pool[media_filepath].terminate()
                                pool[media_filepath].close()
                                pool[media_filepath].join()
                                pool[media_filepath] = None
                            return

                        if force_recognize == False:
                            if media_filepath not in removed_media_filepaths:
                                removed_media_filepaths.append(media_filepath)


                # ffmpeg_src_language_code subtitle stream = exist,
                # ffmpeg_dst_language_code subtitle stream = not exist
                # so we translate it from 'src' to 'dst'
                elif ffmpeg_src_language_code in subtitle_stream_parser.languages() and ffmpeg_dst_language_code not in subtitle_stream_parser.languages():

                    if src_subtitle_stream_timed_subtitles and src_subtitle_stream_timed_subtitles != []:

                        if not_transcribing: return

                        window_key = '-PROGRESS-LOG-'
                        msg = f"Translating '{media_file_display_name}' subtitles from {language.name_of_code[src]} ({src}) to {language.name_of_code[dst]} ({dst})...\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        info = f"Translating '{media_file_display_name}' subtitles from {language.name_of_code[src]} ({src}) to {language.name_of_code[dst]} ({dst})"
                        total = 100
                        start_time = time.time()

                        transcript_translator = SentenceTranslator(src=src, dst=dst, error_messages_callback=show_error_messages)

                        if not_transcribing: return

                        translated_subtitle_stream_transcripts = []
                        for i, translated_subtitle_stream_transcript in enumerate(pool[media_filepath].imap(transcript_translator, subtitle_stream_transcripts)):

                            if not_transcribing:
                                if pool[media_filepath]:
                                    pool[media_filepath].terminate()
                                    pool[media_filepath].close()
                                    pool[media_filepath].join()
                                    pool[media_filepath] = None
                                return

                            translated_subtitle_stream_transcripts.append(translated_subtitle_stream_transcript)

                            progress = int(i*100/len(src_subtitle_stream_timed_subtitles))
                            percentage = f'{progress}%'

                            if progress > 0:
                                elapsed_time = time.time() - start_time
                                eta_seconds = (elapsed_time / progress) * (total - progress)
                            else:
                                eta_seconds = 0
                            eta_time = timedelta(seconds=int(eta_seconds))
                            eta_str = str(eta_time)
                            hour, minute, second = eta_str.split(":")
                            main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (media_file_display_name, info, total, percentage, progress, hour.zfill(2), minute, second))

                        elapsed_time = time.time() - start_time
                        elapsed_time_seconds = timedelta(seconds=int(elapsed_time))
                        elapsed_time_str = str(elapsed_time_seconds)
                        hour, minute, second = elapsed_time_str.split(":")
                        main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (media_file_display_name, info, total, "100%", total, hour.zfill(2), minute, second))

                        if not_transcribing:
                            if pool[media_filepath]:
                                pool[media_filepath].terminate()
                                pool[media_filepath].close()
                                pool[media_filepath].join()
                                pool[media_filepath] = None
                            return

                        window_key = '-PROGRESS-LOG-'
                        msg = f"Writing '{media_file_display_name}' translated subtitles file...\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        base, ext = os.path.splitext(media_filepath)
                        dst_subtitle_filepath = f"{base}.{dst}.{subtitle_format}"
                        dst_subtitle_file_display_name = os.path.basename(dst_subtitle_filepath).split('/')[-1]

                        translation_writer = SubtitleWriter(subtitle_stream_regions, translated_subtitle_stream_transcripts, subtitle_format, error_messages_callback=show_error_messages)
                        translation_writer.write(dst_subtitle_filepath)

                        if os.path.isfile(dst_subtitle_filepath) and dst_subtitle_filepath not in results:
                            results.append(dst_subtitle_filepath)

                        window_key = '-PROGRESS-LOG-'
                        msg = f"'{media_file_display_name}' translated subtitles file saved as :\n  '{dst_subtitle_filepath}'\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        if force_recognize == False:
                            if media_filepath not in removed_media_filepaths:
                                removed_media_filepaths.append(media_filepath)

                        # if args.embed_src is True we can't embed it because src subtitle stream already exist
                        if embed_src == True:
                            window_key = '-PROGRESS-LOG-'
                            msg = f"No need to embed '{ffmpeg_src_language_code}' subtitle into '{media_file_display_name}' because it's already existed\n"
                            append_flag = True
                            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))


                        # if embed_dst is True we embed the translated srt (from src to dst) above into media_filepath
                        if embed_dst == True and src_subtitle_stream_timed_subtitles and src_subtitle_stream_timed_subtitles != []:

                            if not_transcribing:
                                if pool[media_filepath]:
                                    pool[media_filepath].terminate()
                                    pool[media_filepath].close()
                                    pool[media_filepath].join()
                                    pool[media_filepath] = None
                                return

                            ffmpeg_dst_language_code = language.ffmpeg_code_of_code[dst]

                            base, ext = os.path.splitext(media_filepath)

                            dst_tmp_embedded_media_filepath = f"{base}.{ffmpeg_dst_language_code}.tmp.embedded.{ext[1:]}"
                            dst_tmp_embedded_media_file_display_name = os.path.basename(dst_tmp_embedded_media_filepath).split('/')[-1]

                            dst_embedded_media_filepath = f"{base}.{ffmpeg_dst_language_code}.embedded.{ext[1:]}"
                            dst_embedded_media_file_display_name = os.path.basename(dst_embedded_media_filepath).split('/')[-1]

                            window_key = '-PROGRESS-LOG-'
                            msg = f"Embedding '{ffmpeg_dst_language_code}' subtitles file '{dst_subtitle_file_display_name}' into '{media_file_display_name}'"
                            append_flag = True
                            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                            if not_transcribing:
                                if pool[media_filepath]:
                                    pool[media_filepath].terminate()
                                    pool[media_filepath].close()
                                    pool[media_filepath].join()
                                    pool[media_filepath] = None
                                return

                            try:
                                subtitle_embedder = MediaSubtitleEmbedder(subtitle_path=dst_subtitle_filepath, language=ffmpeg_dst_language_code, output_path=dst_tmp_embedded_media_filepath, progress_callback=show_progress, error_messages_callback=show_error_messages)
                                dst_tmp_output = subtitle_embedder(media_filepath)
                            except Exception as e:
                                not_transcribing = True
                                main_window.write_event_value("-EXCEPTION-", e)
                                return

                            if not_transcribing:
                                if pool[media_filepath]:
                                    pool[media_filepath].terminate()
                                    pool[media_filepath].close()
                                    pool[media_filepath].join()
                                    pool[media_filepath] = None
                                return

                            if os.path.isfile(dst_tmp_output):
                                window_key = '-PROGRESS-LOG-'
                                msg = f"Copying '{dst_tmp_embedded_media_file_display_name}' to {dst_embedded_media_file_display_name}...\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                shutil.copy(dst_tmp_output, dst_embedded_media_filepath)
                                os.remove(dst_tmp_output)

                            if os.path.isfile(dst_embedded_media_filepath):
                                window_key = '-PROGRESS-LOG-'
                                msg = f"'{media_file_display_name}' subtitles embedded {media_type} file saved as :\n  '{dst_embedded_media_filepath}'\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                if dst_embedded_media_filepath not in results:
                                    results.append(dst_embedded_media_filepath)

                            else:
                                window_key = '-PROGRESS-LOG-'
                                msg = "Unknown error\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                if not_transcribing:
                    if pool[media_filepath]:
                        pool[media_filepath].terminate()
                        pool[media_filepath].close()
                        pool[media_filepath].join()
                        pool[media_filepath] = None
                    return

                # print overall results
                if (src_subtitle_filepath and os.path.isfile(src_subtitle_filepath)) or (dst_subtitle_filepath and os.path.isfile(dst_subtitle_filepath)):
                    window_key = '-RESULTS-'
                    msg = f"Results for '{media_file_display_name}' :\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    for result in results:
                        window_key = '-RESULTS-'
                        msg = f"{result}\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))
                
                    window_key = '-RESULTS-'
                    msg = "\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    if force_recognize == False:
                        if media_filepath not in removed_media_filepaths:
                            removed_media_filepaths.append(media_filepath)

                        completed_tasks += 1
                        main_window.write_event_value('-EVENT-TRANSCRIBE-TASKS-COMPLETED-', completed_tasks)

            if not_transcribing: return
            if not_transcribing:
                if pool[media_filepath]:
                    pool[media_filepath].terminate()
                    pool[media_filepath].close()
                    pool[media_filepath].join()
                    pool[media_filepath] = None
                return


    # TRANSCRIBE PART

    #print(f"removed_media_filepaths = {removed_media_filepaths}")
    #print(f"media_filepath not in removed_media_filepaths = {media_filepath not in removed_media_filepaths }")

    if media_filepath not in removed_media_filepaths:

        if not_transcribing: return

        language = Language()
        wav_filepath = None
        sample_rate = None

        base, ext = os.path.splitext(media_filepath)
        src_subtitle_filepath = f"{base}.{src}.{subtitle_format}"
        src_subtitle_file_display_name = os.path.basename(src_subtitle_filepath).split('/')[-1]
        if os.path.isfile(src_subtitle_filepath): os.remove(src_subtitle_filepath)

        dst_subtitle_filepath = None
        dst_subtitle_file_display_name = None

        if not is_same_language(src, dst, error_messages_callback=show_error_messages):
            base, ext = os.path.splitext(media_filepath)
            dst_subtitle_filepath = f"{base}.{dst}.{subtitle_format}"
            dst_subtitle_file_display_name = os.path.basename(dst_subtitle_filepath).split('/')[-1]
            if os.path.isfile(dst_subtitle_filepath): os.remove(dst_subtitle_filepath)

        regions = None

        window_key = '-PROGRESS-LOG-'
        msg = f"Processing '{media_file_display_name}' :\n"
        append_flag = True
        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

        window_key = '-PROGRESS-LOG-'
        msg = f"Converting '{media_file_display_name}' to a temporary WAV file...\n"
        append_flag = True
        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

        start_time = time.time()

        try:
            wav_converter = WavConverter(progress_callback=show_progress, error_messages_callback=show_error_messages)
            wav_filepath, sample_rate = wav_converter(media_filepath)
        except Exception as e:
            not_transcribing = True
            main_window.write_event_value("-EXCEPTION-", e)
            return

        if not_transcribing: return

        window_key = '-PROGRESS-LOG-'
        msg = f"'{media_file_display_name}' converted WAV file is :\n  {wav_filepath}\n"
        append_flag = True
        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

        window_key = '-PROGRESS-LOG-'
        msg = f"Finding speech regions of '{media_file_display_name}' WAV file...\n"
        append_flag = True
        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

        try:
            region_finder = SpeechRegionFinder(frame_width=4096, min_region_size=0.5, max_region_size=6, error_messages_callback=show_error_messages)
            regions = region_finder(wav_filepath)
            num = len(regions)
        except Exception as e:
            not_transcribing = True
            main_window.write_event_value("-EXCEPTION-", e)
            return

        window_key = '-PROGRESS-LOG-'
        msg = f"'{media_file_display_name}' speech regions found = {len(regions)}\n"
        append_flag = True

        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

        try:
            converter = FLACConverter(wav_filepath=wav_filepath, error_messages_callback=show_error_messages)
            recognizer = SpeechRecognizer(language=src, rate=sample_rate, error_messages_callback=show_error_messages)
        except Exception as e:
            not_transcribing = True
            main_window.write_event_value("-EXCEPTION-", e)
            return

        transcriptions = []
        translated_transcriptions = []

        if not_transcribing: return

        if regions:
            try:
                window_key = '-PROGRESS-LOG-'
                msg = f"Converting '{media_file_display_name}' speech regions to FLAC files...\n"
                append_flag = True
                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                media_file_display_name = os.path.basename(media_filepath).split('/')[-1]

                info = f"Converting '{media_file_display_name}' speech regions to FLAC files"
                total = 100

                start_time = time.time()

                extracted_regions = []

                for i, extracted_region in enumerate(pool[media_filepath].imap(converter, regions)):

                    if not_transcribing:
                        if pool[media_filepath]:
                            pool[media_filepath].terminate()
                            pool[media_filepath].close()
                            pool[media_filepath].join()
                            pool[media_filepath] = None
                        return

                    extracted_regions.append(extracted_region)

                    progress = int(i*100/len(regions))
                    percentage = f'{progress}%'

                    if progress > 0:
                        elapsed_time = time.time() - start_time
                        eta_seconds = (elapsed_time / progress) * (total - progress)
                    else:
                        eta_seconds = 0
                    eta_time = timedelta(seconds=int(eta_seconds))
                    eta_str = str(eta_time)
                    hour, minute, second = eta_str.split(":")
                    main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (media_file_display_name, info, total, percentage, progress, hour.zfill(2), minute, second))

                elapsed_time = time.time() - start_time
                elapsed_time_seconds = timedelta(seconds=int(elapsed_time))
                elapsed_time_str = str(elapsed_time_seconds)
                hour, minute, second = elapsed_time_str.split(":")
                main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (media_file_display_name, info, total, "100%", total, hour.zfill(2), minute, second))

                if not_transcribing:
                    if pool[media_filepath]:
                        pool[media_filepath].terminate()
                        pool[media_filepath].close()
                        pool[media_filepath].join()
                        pool[media_filepath] = None
                    return

                window_key = '-PROGRESS-LOG-'
                msg = f"Creating '{media_file_display_name}' transcriptions...\n"
                append_flag = True
                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                media_file_display_name = os.path.basename(media_filepath).split('/')[-1]

                info = f"Creating '{media_file_display_name}' transcriptions"
                total = 100

                start_time = time.time()

                for i, transcription in enumerate(pool[media_filepath].imap(recognizer, extracted_regions)):

                    if not_transcribing:
                        if pool[media_filepath]:
                            pool[media_filepath].terminate()
                            pool[media_filepath].close()
                            pool[media_filepath].join()
                            pool[media_filepath] = None
                        return

                    transcriptions.append(transcription)

                    progress = int(i*100/len(regions))
                    percentage = f'{progress}%'

                    if progress > 0:
                        elapsed_time = time.time() - start_time
                        eta_seconds = (elapsed_time / progress) * (total - progress)
                    else:
                        eta_seconds = 0
                    eta_time = timedelta(seconds=int(eta_seconds))
                    eta_str = str(eta_time)
                    hour, minute, second = eta_str.split(":")
                    main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (media_file_display_name, info, total, percentage, progress, hour.zfill(2), minute, second))

                elapsed_time = time.time() - start_time
                elapsed_time_seconds = timedelta(seconds=int(elapsed_time))
                elapsed_time_str = str(elapsed_time_seconds)
                hour, minute, second = elapsed_time_str.split(":")
                main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (media_file_display_name, info, total, "100%", total, hour.zfill(2), minute, second))

                if not_transcribing:
                    if pool[media_filepath]:
                        pool[media_filepath].terminate()
                        pool[media_filepath].close()
                        pool[media_filepath].join()
                        pool[media_filepath] = None
                    return

                window_key = '-PROGRESS-LOG-'
                msg = f"Writing '{media_file_display_name}' subtitles file...\n"
                append_flag = True
                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                writer = SubtitleWriter(regions, transcriptions, subtitle_format, error_messages_callback=show_error_messages)
                writer.write(src_subtitle_filepath)

                if os.path.isfile(src_subtitle_filepath) and src_subtitle_filepath not in results:
                    results.append(src_subtitle_filepath)

                if not_transcribing:
                    if pool[media_filepath]:
                        pool[media_filepath].terminate()
                        pool[media_filepath].close()
                        pool[media_filepath].join()
                        pool[media_filepath] = None
                    return

                if not is_same_language(src, dst, error_messages_callback=show_error_messages):
                    base, ext = os.path.splitext(media_filepath)
                    dst_subtitle_filepath = f"{base}.{dst}.{subtitle_format}"
                
                    if not_transcribing:
                        if pool[media_filepath]:
                            pool[media_filepath].terminate()
                            pool[media_filepath].close()
                            pool[media_filepath].join()
                            pool[media_filepath] = None
                        return

                    timed_subtitles = writer.timed_subtitles

                    created_regions = []
                    created_transcripts = []
                    for entry in timed_subtitles:
                        created_regions.append(entry[0])
                        created_transcripts.append(entry[1])

                    if not_transcribing:
                        if pool[media_filepath]:
                            pool[media_filepath].terminate()
                            pool[media_filepath].close()
                            pool[media_filepath].join()
                            pool[media_filepath] = None
                        return

                    window_key = '-PROGRESS-LOG-'
                    msg = f"Translating '{media_file_display_name}' subtitles from {language.name_of_code[src]} ({src}) to {language.name_of_code[dst]} ({dst})...\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    media_file_display_name = os.path.basename(media_filepath).split('/')[-1]

                    info = f"Translating '{media_file_display_name}' subtitles from {language.name_of_code[src]} ({src}) to {language.name_of_code[dst]} ({dst})"
                    total = 100

                    start_time = time.time()

                    transcript_translator = SentenceTranslator(src=src, dst=dst, error_messages_callback=show_error_messages)
                    translated_transcriptions = []

                    for i, translated_transcription in enumerate(pool[media_filepath].imap(transcript_translator, created_transcripts)):

                        if not_transcribing:
                            if pool[media_filepath]:
                                pool[media_filepath].terminate()
                                pool[media_filepath].close()
                                pool[media_filepath].join()
                                pool[media_filepath] = None
                            return

                        translated_transcriptions.append(translated_transcription)

                        progress = int(i*100/len(timed_subtitles))
                        percentage = f'{progress}%'

                        if progress > 0:
                            elapsed_time = time.time() - start_time
                            eta_seconds = (elapsed_time / progress) * (total - progress)
                        else:
                            eta_seconds = 0
                        eta_time = timedelta(seconds=int(eta_seconds))
                        eta_str = str(eta_time)
                        hour, minute, second = eta_str.split(":")
                        main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (media_file_display_name, info, total, percentage, progress, hour.zfill(2), minute, second))

                    elapsed_time = time.time() - start_time
                    elapsed_time_seconds = timedelta(seconds=int(elapsed_time))
                    elapsed_time_str = str(elapsed_time_seconds)
                    hour, minute, second = elapsed_time_str.split(":")
                    main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (media_file_display_name, info, total, "100%", total, hour.zfill(2), minute, second))

                    if not_transcribing:
                        if pool[media_filepath]:
                            pool[media_filepath].terminate()
                            pool[media_filepath].close()
                            pool[media_filepath].join()
                            pool[media_filepath] = None
                        return

                    window_key = '-PROGRESS-LOG-'
                    msg = f"Writing '{media_file_display_name}' translated subtitles file...\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    translation_writer = SubtitleWriter(created_regions, translated_transcriptions, subtitle_format, error_messages_callback=show_error_messages)
                    translation_writer.write(dst_subtitle_filepath)

                    if os.path.isfile(dst_subtitle_filepath) and dst_subtitle_filepath not in results:
                        results.append(dst_subtitle_filepath)

                    if not_transcribing:
                        if pool[media_filepath]:
                            pool[media_filepath].terminate()
                            pool[media_filepath].close()
                            pool[media_filepath].join()
                            pool[media_filepath] = None
                        return

                window_key = '-PROGRESS-LOG-'
                msg = f"'{media_file_display_name}' subtitles file saved as :\n  '{src_subtitle_filepath}'\n"
                append_flag = True
                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                if is_same_language(src, dst, error_messages_callback=show_error_messages) and embed_src == False:

                    window_key = '-RESULTS-'
                    msg = f"Results for '{media_file_display_name}' :\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    for result in results:
                        window_key = '-RESULTS-'
                        msg = f"{result}\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    window_key = '-RESULTS-'
                    msg = "\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    completed_tasks += 1
                    main_window.write_event_value('-EVENT-TRANSCRIBE-TASKS-COMPLETED-', completed_tasks)

                if not is_same_language(src, dst, error_messages_callback=show_error_messages):
                    window_key = '-PROGRESS-LOG-'
                    msg = f"'{media_file_display_name}' translated subtitles file saved as :\n  '{dst_subtitle_filepath}'\n"
                    append_flag = True
                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                    if embed_src == False and embed_dst == False:

                        window_key = '-RESULTS-'
                        msg = f"Results for '{media_file_display_name}' :\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        for result in results:
                            window_key = '-RESULTS-'
                            msg = f"{result}\n"
                            append_flag = True
                            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        window_key = '-RESULTS-'
                        msg = "\n"
                        append_flag = True
                        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        completed_tasks += 1
                        main_window.write_event_value('-EVENT-TRANSCRIBE-TASKS-COMPLETED-', completed_tasks)

                if not_transcribing:
                    if pool[media_filepath]:
                        pool[media_filepath].terminate()
                        pool[media_filepath].close()
                        pool[media_filepath].join()
                        pool[media_filepath] = None
                    return

                # EMBEDDING subtitles file
                ffmpeg_src_language_code = language.ffmpeg_code_of_code[src]
                ffmpeg_dst_language_code = language.ffmpeg_code_of_code[dst]

                base, ext = os.path.splitext(media_filepath)

                src_tmp_embedded_media_filepath = f"{base}.{ffmpeg_src_language_code}.tmp.embedded.{ext[1:]}"
                src_tmp_embedded_media_file_display_name = os.path.basename(src_tmp_embedded_media_filepath).split('/')[-1]

                dst_tmp_embedded_media_filepath = f"{base}.{ffmpeg_dst_language_code}.tmp.embedded.{ext[1:]}"
                dst_tmp_embedded_media_file_display_name = os.path.basename(dst_tmp_embedded_media_filepath).split('/')[-1]

                src_dst_tmp_embedded_media_filepath = f"{base}.{ffmpeg_src_language_code}.{ffmpeg_dst_language_code}.tmp.embedded.{ext[1:]}"
                src_dst_tmp_embedded_media_file_display_name = os.path.basename(src_dst_tmp_embedded_media_filepath).split('/')[-1]

                src_embedded_media_filepath = f"{base}.{ffmpeg_src_language_code}.embedded.{ext[1:]}"
                src_embedded_media_file_display_name = os.path.basename(src_embedded_media_filepath).split('/')[-1]

                dst_embedded_media_filepath = f"{base}.{ffmpeg_dst_language_code}.embedded.{ext[1:]}"
                dst_embedded_media_file_display_name = os.path.basename(dst_embedded_media_filepath).split('/')[-1]

                src_dst_embedded_media_filepath = f"{base}.{ffmpeg_src_language_code}.{ffmpeg_dst_language_code}.embedded.{ext[1:]}"
                src_dst_embedded_media_file_display_name = os.path.basename(src_dst_embedded_media_filepath).split('/')[-1]
                

                if is_same_language(src, dst, error_messages_callback=show_error_messages):

                    if embed_src == True:
                        try:
                            window_key = '-PROGRESS-LOG-'
                            msg = f"Embedding '{ffmpeg_src_language_code}' subtitles file '{src_subtitle_file_display_name}' into {media_file_display_name}...\n"
                            append_flag = True
                            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                            subtitle_embedder = MediaSubtitleEmbedder(subtitle_path=src_subtitle_filepath, language=ffmpeg_src_language_code, output_path=src_tmp_embedded_media_filepath, progress_callback=show_progress, error_messages_callback=show_error_messages)
                            src_tmp_output = subtitle_embedder(media_filepath)

                            if os.path.isfile(src_tmp_output):
                                window_key = '-PROGRESS-LOG-'
                                msg = f"Copying '{src_tmp_embedded_media_file_display_name}' to {src_embedded_media_file_display_name}...\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                shutil.copy(src_tmp_output, src_embedded_media_filepath)
                                os.remove(src_tmp_output)

                                if src_embedded_media_filepath not in results:
                                    results.append(src_embedded_media_filepath)

                            if os.path.isfile(src_embedded_media_filepath):
                                window_key = '-PROGRESS-LOG-'
                                msg = f"'{media_file_display_name}' subtitles embedded {media_type} file saved as :\n  '{src_embedded_media_filepath}'\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                window_key = '-RESULTS-'
                                msg = f"Results for '{media_file_display_name}' :\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                for result in results:
                                    window_key = '-RESULTS-'
                                    msg = f"{result}\n"
                                    append_flag = True
                                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                window_key = '-RESULTS-'
                                msg = "\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                completed_tasks += 1
                                main_window.write_event_value('-EVENT-TRANSCRIBE-TASKS-COMPLETED-', completed_tasks)

                            else:
                                window_key = '-PROGRESS-LOG-'
                                msg = "Unknown error\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))


                        except Exception as e:
                            not_transcribing = True
                            main_window.write_event_value("-EXCEPTION-", e)
                            return

                elif not is_same_language(src, dst, error_messages_callback=show_error_messages):

                    if embed_src == True and embed_dst == True:
                        try:
                            window_key = '-PROGRESS-LOG-'
                            msg = f"Embedding '{ffmpeg_src_language_code}' subtitles file '{src_subtitle_file_display_name}' into '{media_file_display_name}'...\n"
                            append_flag = True
                            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                            src_subtitle_embedder = MediaSubtitleEmbedder(subtitle_path=src_subtitle_filepath, language=ffmpeg_src_language_code, output_path=src_tmp_embedded_media_filepath, progress_callback=show_progress, error_messages_callback=show_error_messages)
                            src_tmp_output = src_subtitle_embedder(media_filepath)

                            if os.path.isfile(src_tmp_output) and os.path.isfile(dst_subtitle_filepath):
                                window_key = '-PROGRESS-LOG-'
                                msg = f"Embedding '{ffmpeg_dst_language_code}' subtitles file '{dst_subtitle_file_display_name}' into '{src_tmp_embedded_media_file_display_name}'...\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                src_dst_subtitle_embedder = MediaSubtitleEmbedder(subtitle_path=dst_subtitle_filepath, language=ffmpeg_dst_language_code, output_path=src_dst_tmp_embedded_media_filepath, progress_callback=show_progress, error_messages_callback=show_error_messages)
                                src_dst_tmp_output = src_dst_subtitle_embedder(src_tmp_output)

                            if os.path.isfile(src_dst_tmp_output):
                                window_key = '-PROGRESS-LOG-'
                                msg = f"Copying '{src_dst_tmp_embedded_media_file_display_name}' to {src_dst_embedded_media_file_display_name}...\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                shutil.copy(src_dst_tmp_output, src_dst_embedded_media_filepath)

                                if os.path.isfile(src_dst_tmp_output):
                                    os.remove(src_dst_tmp_output)
                                if os.path.isfile(src_tmp_output):
                                    os.remove(src_tmp_output)

                                if src_dst_embedded_media_filepath not in results:
                                    results.append(src_dst_embedded_media_filepath)

                            if os.path.isfile(src_dst_embedded_media_filepath):
                                window_key = '-PROGRESS-LOG-'
                                msg = f"'{media_file_display_name}' subtitles embedded {media_type} file saved as :\n  '{src_dst_embedded_media_filepath}'\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                window_key = '-RESULTS-'
                                msg = f"Results for '{media_file_display_name}' :\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                for result in results:
                                    window_key = '-RESULTS-'
                                    msg = f"{result}\n"
                                    append_flag = True
                                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                window_key = '-RESULTS-'
                                msg = "\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                completed_tasks += 1
                                main_window.write_event_value('-EVENT-TRANSCRIBE-TASKS-COMPLETED-', completed_tasks)

                            else:
                                window_key = '-PROGRESS-LOG-'
                                msg = "Unknown error\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        except Exception as e:
                            not_transcribing = True
                            main_window.write_event_value("-EXCEPTION-", e)
                            return

                        if not_transcribing: return

                    elif embed_src == True and embed_dst == False:
                        try:
                            window_key = '-PROGRESS-LOG-'
                            msg = f"Embedding '{ffmpeg_src_language_code}' subtitles file '{src_subtitle_file_display_name}' into '{media_file_display_name}'...\n"
                            append_flag = True
                            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                            src_subtitle_embedder = MediaSubtitleEmbedder(subtitle_path=src_subtitle_filepath, language=ffmpeg_src_language_code, output_path=src_tmp_embedded_media_filepath, progress_callback=show_progress, error_messages_callback=show_error_messages)
                            src_tmp_output = src_subtitle_embedder(media_filepath)

                            if os.path.isfile(src_tmp_output):
                                window_key = '-PROGRESS-LOG-'
                                msg = f"Copying '{src_tmp_embedded_media_file_display_name}' to {src_embedded_media_file_display_name}...\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                shutil.copy(src_tmp_output, src_embedded_media_filepath)
                                os.remove(src_tmp_output)

                                if src_embedded_media_filepath not in results:
                                    results.append(src_embedded_media_filepath)

                            if os.path.isfile(src_embedded_media_filepath):
                                window_key = '-PROGRESS-LOG-'
                                msg = f"'{media_file_display_name}' subtitles embedded {media_type} file saved as :\n  '{src_embedded_media_filepath}'\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                window_key = '-RESULTS-'
                                msg = f"Results for '{media_file_display_name}' :\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                for result in results:
                                    window_key = '-RESULTS-'
                                    msg = f"{result}\n"
                                    append_flag = True
                                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                window_key = '-RESULTS-'
                                msg = "\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                completed_tasks += 1
                                main_window.write_event_value('-EVENT-TRANSCRIBE-TASKS-COMPLETED-', completed_tasks)

                            else:
                                window_key = '-PROGRESS-LOG-'
                                msg = "Unknown error\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        except Exception as e:
                            not_transcribing = True
                            main_window.write_event_value("-EXCEPTION-", e)
                            return

                            if not_transcribing: return

                    elif embed_src == False and embed_dst == True:
                        try:
                            window_key = '-PROGRESS-LOG-'
                            msg = f"Embedding '{ffmpeg_dst_language_code}' subtitles file '{dst_subtitle_file_display_name}' into '{media_file_display_name}'...\n"
                            append_flag = True
                            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                            dst_subtitle_embedder = MediaSubtitleEmbedder(subtitle_path=dst_subtitle_filepath, language=ffmpeg_dst_language_code, output_path=src_tmp_embedded_media_filepath, progress_callback=show_progress, error_messages_callback=show_error_messages)
                            dst_tmp_output = dst_subtitle_embedder(media_filepath)

                            if os.path.isfile(dst_tmp_output):
                                window_key = '-PROGRESS-LOG-'
                                msg = f"Copying '{dst_tmp_embedded_media_file_display_name}' to {dst_embedded_media_file_display_name}...\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                shutil.copy(dst_tmp_output, dst_embedded_media_filepath)
                                os.remove(dst_tmp_output)

                                if dst_embedded_media_filepath not in results:
                                    results.append(dst_embedded_media_filepath)

                            if os.path.isfile(dst_embedded_media_filepath):
                                window_key = '-PROGRESS-LOG-'
                                msg = f"'{media_file_display_name}' subtitles embedded {media_type} file saved as :\n  '{dst_embedded_media_filepath}'\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                window_key = '-RESULTS-'
                                msg = f"Results for '{media_file_display_name}' :\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                for result in results:
                                    window_key = '-RESULTS-'
                                    msg = f"{result}\n"
                                    append_flag = True
                                    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                window_key = '-RESULTS-'
                                msg = "\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                                completed_tasks += 1
                                main_window.write_event_value('-EVENT-TRANSCRIBE-TASKS-COMPLETED-', completed_tasks)

                            else:
                                window_key = '-PROGRESS-LOG-'
                                msg = "Unknown error\n"
                                append_flag = True
                                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                        except Exception as e:
                            not_transcribing = True
                            main_window.write_event_value("-EXCEPTION-", e)
                            return

                            if not_transcribing: return

            except Exception as e:
                not_transcribing = True
                main_window.write_event_value("-EXCEPTION-", e)
                return

        if pool[media_filepath]:
            pool[media_filepath].close()
            pool[media_filepath].join()
            pool[media_filepath] = None


def start_transcription(media_filepaths, src, dst, subtitle_format, embed_src, embed_dst, force_recognize):
    global main_window, language, pool, thread_check_subtitle_stream, thread_transcribe, thread_transcribe_starter, \
            removed_media_filepaths, completed_tasks, proceed_list

    window_key = '-PROGRESS-LOG-'
    msg = ''
    append_flag = False
    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    window_key = '-RESULTS-'
    msg = ''
    append_flag = False
    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', ("...", "Progress info", 0, "0%", 0, "00", "00", "00"))

    removed_media_filepaths = []
    proceed_list = []

    for media_filepath in media_filepaths:

        media_file_display_name = os.path.basename(media_filepath).split('/')[-1]

        if force_recognize == True:
            base, ext = os.path.splitext(media_filepath)
            tmp_subtitle_removed_media_filepath = f"{base}.tmp.subtitles.removed.{ext[1:]}"
            subtitle_removed_media_filepath = f"{base}.force.recognize.{ext[1:]}"

            subtitle_remover = MediaSubtitleRemover(output_path=tmp_subtitle_removed_media_filepath, progress_callback=show_progress, error_messages_callback=show_error_messages)
            tmp_output = subtitle_remover(media_filepath)

            if os.path.isfile(tmp_output):
                shutil.copy(tmp_output, subtitle_removed_media_filepath)
                os.remove(tmp_output)

                proceed_list.append(subtitle_removed_media_filepath)

                window_key = '-PROGRESS-LOG-'
                msg = f"Removing all subtitle streams from '{media_file_display_name}' and save as :\n  '{subtitle_removed_media_filepath}'\n"
                append_flag = True
                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

        else:
            proceed_list = media_filepaths


    if proceed_list:

        pool = {media_filepath: multiprocessing.Pool(16, initializer=NoConsoleProcess) for media_filepath in proceed_list}
        media_types = {media_filepath: check_file_type(media_filepath, error_messages_callback=show_error_messages) for media_filepath in proceed_list}
        
        for media_filepath in proceed_list:

            if os.path.isfile(media_filepath):
                thread_transcribe = Thread(target=transcribe, args=(src, dst, media_filepath, media_types[media_filepath], subtitle_format, embed_src, embed_dst, force_recognize), daemon=True)
                thread_transcribe.start()


#------------------------------------------------------------ MAIN FUNCTION ------------------------------------------------------------#


def main():
    global language, not_transcribing, thread_transcribe, thread_transcribe_starter, pool, removed_media_filepaths, \
        completed_tasks, not_recording, thread_record_streaming, main_window

    transcribe_start_time = None
    transcribe_end_time = None
    transcribe_elapsed_time = None

    video_file_types = [
        ('MP4 Files', '*.mp4'),
    ]

    language = Language()

    if sys.platform == "win32":
        stop_ffmpeg_windows()
    else:
        stop_ffmpeg_linux()

    last_selected_src = None
    last_selected_dst = None

    src_filename = "src_code"
    src_filepath = os.path.join(tempfile.gettempdir(), src_filename)
    if os.path.isfile(src_filepath):
        src_file = open(src_filepath, "r")
        last_selected_src = src_file.read()

    dst_filename = "dst_code"
    dst_filepath = os.path.join(tempfile.gettempdir(), dst_filename)
    if os.path.isfile(dst_filepath):
        dst_file = open(dst_filepath, "r")
        last_selected_dst = dst_file.read()

    tmp_recorded_streaming_filename = "record.mp4"
    tmp_recorded_streaming_filepath = os.path.join(tempfile.gettempdir(), tmp_recorded_streaming_filename)
    if os.path.isfile(tmp_recorded_streaming_filepath): os.remove(tmp_recorded_streaming_filepath)

    saved_recorded_streaming_filename = None

    thread_transcribe = None
    thread_check_subtitle_stream = None
    thread_transcribe_starter = None
    completed_tasks = 0

    parser = argparse.ArgumentParser()
    parser.add_argument('source_path', help="Path to the video or audio files to generate subtitle (use wildcard for multiple files or separate them with a space character e.g. \"file 1.mp4\" \"file 2.mp4\")", nargs='*', default='')

    if last_selected_src:
        parser.add_argument('-S', '--src-language', help="Language code of the audio language spoken in video/audio source_path", default=last_selected_src)
    else:
        parser.add_argument('-S', '--src-language', help="Language code of the audio language spoken in video/audio source_path", default="en")

    if last_selected_dst:
        parser.add_argument('-D', '--dst-language', help="Desired translation language code for the subtitles", default=last_selected_dst)
    else:
        parser.add_argument('-D', '--dst-language', help="Desired translation language code for the subtitles", default="id")

    parser.add_argument('-ll', '--list-languages', help="List all supported languages", action='store_true')
    parser.add_argument('-F', '--format', help="Desired subtitle format", default="srt")
    parser.add_argument('-lf', '--list-formats', help="List all supported subtitle formats", action='store_true')
    parser.add_argument('-es', '--embed-src', help="Boolean value (True or False) for embed_src subtitles file into video file", type=bool, default=False)
    parser.add_argument('-ed', '--embed-dst', help="Boolean value (True or False) for embed_src subtitles file into video file", type=bool, default=False)
    parser.add_argument('-fr', '--force-recognize', help="Boolean value (True or False) for re-recognize media file event if it's already has subtitles stream", type=bool, default=False)
    parser.add_argument('-v', '--version', action='version', version=VERSION)

    args = parser.parse_args()

    if args.list_formats:
        print("Supported subtitle formats :")
        for subtitle_format in SubtitleFormatter.supported_formats:
            print("{format}".format(format=subtitle_format))
        parser.exit(0)

    if args.list_languages:
        print("Supported languages :")
        for code, language in sorted(language.name_of_code.items()):
            print("%-8s : %s" %(code, language))
        parser.exit(0)

    browsed_files = []
    filepaths = []
    input_string = ""
    sg_listbox_values = []
    invalid_media_filepaths = []
    not_exist_filepaths = []
    argpath = None

    media_type = None
    embed_src = False
    embed_dst = False
    force_recognize = False
    src_subtitle_filepath = None
    dst_subtitle_filepath = None
    ffmpeg_src_language_code = None
    ffmpeg_dst_language_code = None
    embedded_media_filepath = None
    subtitle_format = args.format
    removed_media_filepaths = []

    if args.source_path:

        args_source_path = args.source_path

        if sys.platform == "win32":

            for i in range(len(args.source_path)):

                if ("[" or "]") in args.source_path[i]:
                    placeholder = "#TEMP#"
                    args_source_path[i] = args.source_path[i].replace("[", placeholder)
                    args_source_path[i] = args_source_path[i].replace("]", "[]]")
                    args_source_path[i] = args_source_path[i].replace(placeholder, "[[]")

        for arg in args_source_path:
            if not os.sep in arg:
                argpath = os.path.join(os.getcwd(),arg)
            else:
                argpath = arg

            argpath = argpath.replace("\\", "/")

            if (not os.path.isfile(argpath)) and (not "*" in argpath) and (not "?" in argpath):
                not_exist_filepaths.append(argpath)

            if not sys.platform == "win32" :
                argpath = escape(argpath)

            filepaths += glob(argpath)

        if sys.platform == "win32":
            for i in range(len(filepaths)):
                if "\\" in filepaths[i]:
                    filepaths[i] = filepaths[i].replace("\\", "/")
                    input_string = input_string + filepaths[i] + ";"

        if filepaths:
            for argpath in filepaths:
                argpath = argpath.replace("\\", "/")
                if os.path.isfile(argpath):
                    if check_file_type(argpath, error_messages_callback=show_error_messages) == 'video':
                        sg_listbox_values.append(argpath)
                        media_type = "video"
                    elif check_file_type(argpath, error_messages_callback=show_error_messages) == 'audio':
                        sg_listbox_values.append(argpath)
                        media_type = "audio"
                    else:
                        invalid_media_filepaths.append(argpath)
                        media_type = None
                    input_string = input_string[:-1]
                else:
                    not_exist_filepaths.append(argpath)
                    media_type = None

            if invalid_media_filepaths:
                msg = ""
                for invalid_media_filepath in invalid_media_filepaths:
                    msg = msg + f"{invalid_media_filepath} is not valid video or audio files\n"
                sg.Popup(msg, title="Info", line_width=100, any_key_closes=True)

        if not_exist_filepaths:
            msg = ""
            for not_exist_filepath in not_exist_filepaths:
                msg = msg + f"{not_exist_filepath} is not exist\n"
            sg.Popup(msg, title="Info", line_width=100, any_key_closes=True)

        elif not filepaths and not not_exist_filepaths:
            msg = "No any files matching filenames you typed"
            sg.Popup(msg, title="Info", line_width=100, any_key_closes=True)


    if args.src_language:
        if args.src_language not in language.name_of_code.keys():
            msg = "Voice language you typed is not supported\nPlease select one from combobox"
            sg.Popup(msg, title="Info", line_width=50, any_key_closes=True)
            sg_combo_src_values = language.name_of_code["en"]
        elif args.src_language in language.name_of_code.keys():
            src = args.src_language
            sg_combo_src_values = language.name_of_code[src]
            last_selected_src = src
            src_file = open(src_filepath, "w")
            src_file.write(src)
            src_file.close()


    if args.dst_language:
        if args.dst_language not in language.name_of_code.keys():
            msg = "Translation language you typed is not supported\nPlease select one from combobox"
            sg.Popup(msg, title="Info", line_width=50, any_key_closes=True)
            sg_combo_dst_values = language.name_of_code["id"]
        elif args.dst_language in language.name_of_code.keys():
            dst = args.dst_language
            sg_combo_dst_values = language.name_of_code[dst]
            last_selected_dst = dst
            dst_file = open(dst_filepath, "w")
            dst_file.write(dst)
            dst_file.close()

    if args.format:
        if args.format not in SubtitleFormatter.supported_formats:
            msg = "Subtitle format you typed is not supported\nPlease select one from combobox"
            sg.Popup(msg, title="Info", line_width=50, any_key_closes=True)
        else:
            subtitle_format = args.format
            sg_combo_subtitle_format_values = subtitle_format


#------------------------------------------------------------- MAIN WINDOW -------------------------------------------------------------#


    not_transcribing = True
    subtitle_format = None
    FONT=('Helvetica', 10)

    layout = [
                [
                    sg.Text('Voice language', size=(18,1)),
                    sg.Combo(list(language.code_of_name), default_value=sg_combo_src_values, enable_events=True, key='-SRC-'),
                    sg.Checkbox("Embed subtitles file into media file", default=embed_src, key='-EMBED-SRC-SUBTITLE-')

                ],
                [
                    sg.Text('Translation language', size=(18,1)),
                    sg.Combo(list(language.code_of_name), default_value=sg_combo_dst_values, enable_events=True, key='-DST-'),
                    sg.Checkbox("Embed translated subtitles file into media file", default=embed_dst, key='-EMBED-DST-SUBTITLE-')
                ],
                [
                    sg.Text('Subtitle format', size=(18,1)),
                    sg.Combo(list(SubtitleFormatter.supported_formats), default_value=sg_combo_subtitle_format_values, enable_events=True, key='-SUBTITLE-FORMAT-'),
                    sg.Checkbox("Force recognize", default=force_recognize, key='-FORCE-RECOGNIZE-')
                ],
                [
                    sg.Text('URL', size=(18,1)),
                    sg.Input(size=(58, 1), expand_x=True, expand_y=True, key='-URL-', enable_events=True, right_click_menu=['&Edit', ['&Copy','&Paste',]]),
                    sg.Button("Start Record Streaming", size=(22,1), key='-RECORD-STREAMING-')
                ],
                [
                    sg.Text('Thread status', size=(18,1)),
                    sg.Text('NOT RECORDING', size=(20, 1), background_color='green1', text_color='black', expand_x=True, expand_y=True, key='-RECORD-STREAMING-STATUS-'),
                    sg.Text('Duration recorded', size=(18, 1)),
                    sg.Text('0:00:00.000000', size=(14, 1), background_color='green1', text_color='black', expand_x=True, expand_y=True, key='-STREAMING-DURATION-RECORDED-'),
                    sg.Text('', size=(8,1)),
                    sg.Button("Save Recorded Streaming", size=(22,1), key='-SAVE-RECORDED-STREAMING-')

                ],
                [
                    sg.Text("Browsed Files", size=(18,1)),
                    sg.Input(input_string, size=(32,1), expand_x=True, expand_y=True, key='-INPUT-', enable_events=True, right_click_menu=['&Edit', ['&Copy','&Paste',]],),
                    sg.Button("", size=(10,1), button_color=(sg.theme_background_color(), sg.theme_background_color()), border_width=0, key='-DUMMY-')
                ],
                [
                    sg.Text("File List", size=(18,1)),
                    sg.Listbox(sg_listbox_values, size=(32,1), expand_x=True, expand_y=True, key='-LIST-', enable_events=True, select_mode=sg.LISTBOX_SELECT_MODE_EXTENDED, horizontal_scroll=True),
                    sg.Column(
                                [
                                    [sg.FilesBrowse("Add", size=(8,1), target='-INPUT-', file_types=(("All Files", "*.*"),), enable_events=True, key="-ADD-")],
                                    [sg.Button("Remove", key="-REMOVE-", size=(8,1), expand_x=True, expand_y=False,)],
                                    [sg.Button("Clear", key="-CLEAR-", size=(8,1), expand_x=True, expand_y=False,)],
                                ],
                                element_justification='c'
                             )
                ],
                [sg.Text("File to procees", size=(110,1), expand_x=False, expand_y=False, key='-FILE-DISPLAY-NAME-')],
                [sg.Text("Progress info", size=(110,1), expand_x=False, expand_y=False, key='-INFO-')],
                [
                    sg.ProgressBar(100, size=(56,1), orientation='h', expand_x=True, expand_y=True, key='-PROGRESS-'),
                    sg.Text("0%", size=(5,1), expand_x=False, expand_y=False, key='-PERCENTAGE-'),
                    sg.Text(f"ETA  : 00:00:00", size=(14, 1), expand_x=False, expand_y=False, key='-ETA-', justification='r')
                ],
                [sg.Text('Progress log', expand_x=False, expand_y=False)],
                [sg.Multiline(size=(50, 6), expand_x=True, expand_y=True, horizontal_scroll=True, enable_events=True, right_click_menu=['&Edit', ['&Copy','&Paste',]], key='-PROGRESS-LOG-')],
                [sg.Text('Results', expand_x=False, expand_y=False)],
                [sg.Multiline(size=(50, 4), expand_x=True, expand_y=True, horizontal_scroll=True, enable_events=True, right_click_menu=['&Edit', ['&Copy','&Paste',]], key='-RESULTS-')],
                [sg.Button('Start', expand_x=True, expand_y=True, key='-START-'),sg.Button('Exit', expand_x=True, expand_y=True)]
            ]

    main_window = sg.Window('PyAutoSRT-'+VERSION, layout, font=FONT, resizable=True, keep_on_top=True, return_keyboard_events=True, finalize=True)
    sg.set_options(font=FONT)
    main_window['-SRC-'].block_focus()

    main_window['-URL-'].bind("<FocusIn>", "FocusIn")
    main_window['-PROGRESS-LOG-'].bind("<FocusIn>", "FocusIn")
    main_window['-RESULTS-'].bind("<FocusIn>", "FocusIn")
    main_window.bind("<Button-3>", "right_click")

    browsed_files = []
    filepaths = []
    invalid_media_filepaths = []
    not_exist_filepaths = []

    if (sys.platform == "win32"):
        main_window.TKroot.attributes('-topmost', True)
        main_window.TKroot.attributes('-topmost', False)

    if not (sys.platform == "win32"):
        main_window.TKroot.attributes('-topmost', 1)
        main_window.TKroot.attributes('-topmost', 0)

    src = language.code_of_name[str(main_window['-SRC-'].get())]
    last_selected_src = src
    src_file = open(src_filepath, "w")
    src_file.write(src)
    src_file.close()

    dst = language.code_of_name[str(main_window['-DST-'].get())]
    last_selected_dst = dst
    dst_file = open(dst_filepath, "w")
    dst_file.write(dst)
    dst_file.close()

    not_recording = True

    tmp_recorded_streaming_filename = "record.mp4"
    tmp_recorded_streaming_filepath = os.path.join(tempfile.gettempdir(), tmp_recorded_streaming_filename)

    saved_recorded_streaming_filename = None


#-------------------------------------------------------------- MAIN LOOP -------------------------------------------------------------#


    move_center(main_window)

    if is_same_language(src, dst, error_messages_callback=show_error_messages):
        main_window['-EMBED-DST-SUBTITLE-'].update(disabled=True)
    else:
        main_window['-EMBED-DST-SUBTITLE-'].update(disabled=False)

    while True:

        event, values = main_window.read()

        if event == 'right_click':

            x, y = main_window.TKroot.winfo_pointerxy()
            widget = main_window.TKroot.winfo_containing(x, y)
            widget.focus_set()


        if event == 'Copy':

            key = main_window.find_element_with_focus().Key
            widget = main_window[key].Widget
            selected_text = None
            try:
                selected_text = widget.selection_get()
            except:
                pass
            if sys.platform == "win32":
                if selected_text:
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardText(selected_text)
                    win32clipboard.CloseClipboard()
            elif sys.platform == "linux":
                if selected_text:
                    set_clipboard_text(selected_text)


        elif event == 'Paste':

            key = main_window.find_element_with_focus().Key
            current_value = values[key]
            text_elem = main_window[key]
            element_type = type(text_elem)
            strings = str(text_elem.Widget.index('insert'))
            cursor_position_strings = ""
            if "Input" in str(element_type):
                cursor_position_strings = strings
            elif "Multiline" in str(element_type):
                cursor_position_strings = strings[2:]
            cursor_position = int(cursor_position_strings)
            clipboard_data = None
            if sys.platform == "win32":
                try:
                    win32clipboard.OpenClipboard()
                    clipboard_data = win32clipboard.GetClipboardData()
                except Exception as e:
                    #show_error_messages(e)
                    pass
            elif sys.platform == "linux":
                try:
                    clipboard_data = get_clipboard_text()
                except:
                    pass
            if clipboard_data:
                new_value = current_value[:cursor_position] + clipboard_data + current_value[cursor_position:]
                main_window[key].update(new_value)
                cursor_position += len(clipboard_data)
                if "Multiline" in str(element_type):
                    text_elem.Widget.mark_set('insert', f'1.{cursor_position}')
                    text_elem.Widget.see(f'1.{cursor_position}')
                elif "Input" in str(element_type):
                    text_elem.Widget.icursor(cursor_position)
                    text_elem.Widget.xview_moveto(1.0)


        if event == 'Exit' or event == sg.WIN_CLOSED:

            if not not_transcribing:

                answer = popup_yes_no('Are you sure?', title='Confirm')

                if 'Yes' in answer:

                    not_transcribing = True
                    main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))

                    if thread_transcribe and thread_transcribe.is_alive():
                        stop_thread(thread_transcribe)

                    if thread_transcribe_starter and thread_transcribe_starter.is_alive():
                        stop_thread(thread_transcribe_starter)

                    main_window['-PROGRESS-LOG-'].update("\n--- Canceling all tasks ---\n", append=True)
                    scroll_to_last_line(main_window, main_window['-PROGRESS-LOG-'])
                    break

            else:
                break


        elif event == '-SRC-':

            src = language.code_of_name[str(main_window['-SRC-'].get())]
            last_selected_src = src
            src_file = open(src_filepath, "w")
            src_file.write(src)
            src_file.close()

            if is_same_language(src, dst, error_messages_callback=show_error_messages):
                main_window['-EMBED-DST-SUBTITLE-'].update(disabled=True)
            else:
                main_window['-EMBED-DST-SUBTITLE-'].update(disabled=False)


        elif event == '-DST-':

            dst = language.code_of_name[str(main_window['-DST-'].get())]
            last_selected_dst = dst
            dst_file = open(dst_filepath, "w")
            dst_file.write(dst)
            dst_file.close()

            if is_same_language(src, dst, error_messages_callback=show_error_messages):
                main_window['-EMBED-DST-SUBTITLE-'].update(disabled=True)
            else:
                main_window['-EMBED-DST-SUBTITLE-'].update(disabled=False)


        elif event == '-INPUT-':

            browsed_files = []
            browsed_files += str(main_window['-INPUT-'].get()).split(';')
            args_source_path = [len(browsed_files)]
            invalid_media_filepaths = []

            if browsed_files != [''] or browsed_files != []:

                if sys.platform == "win32":
                    for i in range(len(browsed_files)):

                        if ("[" or "]") in browsed_files[i]:
                            placeholder = "#TEMP#"
                            browsed_files[i] = browsed_files[i].replace("[", placeholder)
                            browsed_files[i] = browsed_files[i].replace("]", "[]]")
                            browsed_files[i] = browsed_files[i].replace(placeholder, "[[]")

                for file in browsed_files:
                    if not os.sep in file:
                        filepath = os.path.join(os.getcwd(),file)
                    else:
                        filepath = file

                    filepath = filepath.replace("\\", "/")

                    if (not os.path.isfile(filepath)) and (not "*" in filepath) and (not "?" in filepath):
                        not_exist_filepaths.append(filepath)

                    if not sys.platform == "win32" :
                        filepath = escape(filepath)

                    filepaths += glob(filepath)

                if sys.platform == "win32":
                    for i in range(len(filepaths)):
                        if "\\" in filepaths[i]:
                            filepaths[i] = filepaths[i].replace("\\", "/")

                if filepaths:
                    for file in filepaths:
                        file = file.replace("\\", "/")
                        if file not in sg_listbox_values:
                            if check_file_type(file, error_messages_callback=show_error_messages) == 'video':
                                sg_listbox_values.append(file)
                                media_type = "video"
                            elif check_file_type(file, error_messages_callback=show_error_messages) == 'audio':
                                sg_listbox_values.append(file)
                                media_type = "audio"
                            else:
                                invalid_media_filepaths.append(file)
                                media_type = None
                            input_string = input_string[:-1]
                        else:
                            media_type = None

                    if invalid_media_filepaths:
                        if len(invalid_media_filepaths) == 1:
                            msg = f"{invalid_media_filepaths[0]} is not a valid video or audio file"
                        else:
                            msg = ""
                            for invalid_media_filepath in invalid_media_filepaths:
                                msg = msg + f"{invalid_media_filepath} is not a valid video or audio file\n"
                        sg.Popup(msg, title="Info", line_width=100, any_key_closes=False)

                else:
                    msg = "Invalid filename or file is not exist"
                    sg.Popup(msg, title="Info", line_width=50, any_key_closes=False)

                main_window['-LIST-'].update(sg_listbox_values)

                browsed_files = []
                filepaths = []
                invalid_media_filepaths = []
                not_exist_filepaths = []


        elif event == '-REMOVE-FILE-FROM-LIST-':

            removed_file_list = values[event]
            if removed_file_list:
                main_window['-LIST-'].update(sg_listbox_values)


        elif event == '-REMOVE-':

            listbox_selection = values['-LIST-']
            if listbox_selection:
                for index in listbox_selection[::-1]:
                    sg_listbox_values.remove(index)
                main_window['-LIST-'].update(sg_listbox_values)


        elif 'Delete' in event and values['-LIST-']:

            listbox_selection = values['-LIST-']
            if listbox_selection:
                for index in listbox_selection[::-1]:
                    sg_listbox_values.remove(index)
                main_window['-LIST-'].update(sg_listbox_values)


        elif event == '-CLEAR-':

            main_window['-INPUT-'].update('')
            sg_listbox_values = []
            browsed_files = []
            main_window['-INPUT-'].update('')
            main_window['-LIST-'].update(sg_listbox_values)
            main_window['-INFO-'].update('Progress')
            main_window['-PROGRESS-'].update(0)
            main_window['-PERCENTAGE-'].update('0%')
            main_window['-ETA-'].update('ETA  : 00:00:00')
            main_window['-PROGRESS-LOG-'].update('')
            main_window['-RESULTS-'].update('')


        elif event == '-START-':

            src = language.code_of_name[str(main_window['-SRC-'].get())]
            dst = language.code_of_name[str(main_window['-DST-'].get())]
            subtitle_format = values['-SUBTITLE-FORMAT-']
            main_window['-RESULTS-'].update('', append=False)

            transcribe_start_time = time.time()

            # RUN A THREADS FOR EACH MEDIA FILES IN PARALEL
            sg_listbox_values = main_window['-LIST-'].Values
            #print(f"sg_listbox_values = {sg_listbox_values}")
            if len(sg_listbox_values)>0 and src and dst and subtitle_format:
                not_transcribing = not not_transcribing

                if not not_transcribing:
                    completed_tasks = 0
                    pool = None
                    main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))
                    embed_src = main_window['-EMBED-SRC-SUBTITLE-'].get()
                    embed_dst = main_window['-EMBED-DST-SUBTITLE-'].get()
                    force_recognize = main_window['-FORCE-RECOGNIZE-'].get()
                    thread_transcribe_starter = Thread(target=start_transcription, args=(sg_listbox_values, src, dst, subtitle_format, embed_src, embed_dst, force_recognize), daemon=True)
                    thread_transcribe_starter.start()

                else:
                    not_transcribing = not not_transcribing
                    answer = popup_yes_no('Are you sure?', title='Confirm')
                    if 'Yes' in answer:
                        not_transcribing = True
                        main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))

                        if thread_transcribe and thread_transcribe.is_alive():
                            stop_thread(thread_transcribe)

                        if thread_transcribe_starter and thread_transcribe_starter.is_alive():
                            stop_thread(thread_transcribe_starter)

                        main_window['-PROGRESS-LOG-'].update("\n--- Canceling all tasks ---\n", append=True)
                        scroll_to_last_line(main_window, main_window['-PROGRESS-LOG-'])

            else:
                msg = "You should pick a file first"
                sg.Popup(msg, title="Info", line_width=50, any_key_closes=True)


        elif event == '-EVENT-TRANSCRIBE-MESSAGES-':

            if not not_transcribing:
                m = values[event]
                window_key = m[0]
                msg = m[1]
                append_flag = m[2]
                main_window[window_key].update(msg, append=append_flag)
                scroll_to_last_line(main_window, main_window[window_key])


        elif event == '-EVENT-UPDATE-PROGRESS-BAR-':

            if not not_transcribing:
                pb = values[event]
                media_file_display_name = pb[0]
                info = pb[1]
                total = pb[2]
                percentage = pb[3]
                progress = pb[4]
                time_str = None
                if progress > 0 and progress < total:
                    time_str = "ETA  : " + pb[5] + ":" + pb[6] + ":" + pb[7] 
                if progress == total:
                    time_str = "Time : " + pb[5] + ":" + pb[6] + ":" + pb[7] 
                processing_string = ""
                if media_file_display_name == "...":
                    processing_string = "File to process"
                else:
                    processing_string = f"Processing '{media_file_display_name}'"
                main_window['-FILE-DISPLAY-NAME-'].update(processing_string)
                main_window['-INFO-'].update(info)
                main_window['-PERCENTAGE-'].update(percentage)
                main_window['-PROGRESS-'].update(progress)
                main_window['-ETA-'].update(time_str)


        elif event == '-EVENT-TRANSCRIBE-TASKS-COMPLETED-':

            completed_tasks = values[event]

            #print(f"completed_tasks = {completed_tasks}")
            #print(f"len(sg_listbox_values) = {len(sg_listbox_values)}")

            if completed_tasks == len(sg_listbox_values):
                not_transcribing = True
                main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))
                transcribe_end_time = time.time()
                transcribe_elapsed_time = transcribe_end_time - transcribe_start_time
                transcribe_elapsed_time_seconds = timedelta(seconds=int(transcribe_elapsed_time))
                transcribe_elapsed_time_str = str(transcribe_elapsed_time_seconds)
                hour, minute, second = transcribe_elapsed_time_str.split(":")
                ##msg = "Total running time : %s:%s:%s" %(hour.zfill(2), minute, second)
                msg = f"Total running time : {hour.zfill(2)}:{minute}:{second}"
                main_window['-PROGRESS-LOG-'].update("\n", append=True)
                main_window['-PROGRESS-LOG-'].update(msg, append=True)
                scroll_to_last_line(main_window, main_window['-PROGRESS-LOG-'])


        elif event == '-EXCEPTION-':

            e = str(values[event]).strip()

            w = 50
            if len(e) > 50:
                w = 100
            else:
                w = 50

            sg.Popup(e, title="Info", line_width=w, any_key_closes=False)

            main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))
            main_window['-PROGRESS-LOG-'].update('', append=False)


        elif event == '-EVENT-STREAMING-DURATION-RECORDED-':

            record_duration = str(values[event]).strip()
            main_window['-STREAMING-DURATION-RECORDED-'].update(record_duration)


        elif event == '-EVENT-THREAD-RECORD-STREAMING-STATUS-':

            msg = str(values[event]).strip()
            main_window['-RECORD-STREAMING-STATUS-'].update(msg)

            if "RECORDING" in msg:
                main_window['-RECORD-STREAMING-STATUS-'].update(text_color='white', background_color='red')
                main_window['-STREAMING-DURATION-RECORDED-'].update(text_color='white', background_color='red')
            else:
                main_window['-RECORD-STREAMING-STATUS-'].update(text_color='black', background_color='green1')
                main_window['-STREAMING-DURATION-RECORDED-'].update(text_color='black', background_color='green1')


        elif event == '-RECORD-STREAMING-':

            if str(values['-URL-']).strip() == "":
                msg = "Invalid URL, please enter a valid URL"
                sg.Popup(msg, title="Info", line_width=50, any_key_closes=True)
                not_recording = True
                main_window['-RECORD-STREAMING-'].update(('Stop Record Streaming','Start Record Streaming')[not_recording], button_color=(('white', ('red', '#283b5b')[not_recording])))

            else:
                if not_recording == True:
                    is_valid_url_streaming = is_streaming_url(str(values['-URL-']).strip(), error_messages_callback=show_error_messages)

                if not is_valid_url_streaming:
                    msg = "Invalid URL, please enter a valid URL"
                    sg.Popup(msg, title="Info", line_width=50, any_key_closes=True)
                    main_window['-URL-'].update('')

                else:
                    not_recording = not not_recording
                    main_window['-RECORD-STREAMING-'].update(('Stop Record Streaming','Start Record Streaming')[not_recording], button_color=(('white', ('red', '#283b5b')[not_recording])))

                    if (main_window['-URL-'].get() != None or main_window['-URL-'].get() != '') and not_recording == False:
                        if is_valid_url_streaming:

                            url = values['-URL-']

                            #NEEDED FOR streamlink MODULE WHEN RUN AS PYINSTALLER COMPILED BINARY
                            os.environ['STREAMLINK_DIR'] = './streamlink/'
                            os.environ['STREAMLINK_PLUGINS'] = './streamlink/plugins/'
                            os.environ['STREAMLINK_PLUGIN_DIR'] = './streamlink/plugins/'

                            streamlink = Streamlink()
                            streams = streamlink.streams(url)
                            stream_url = streams['360p']

                            # WINDOWS AND LINUX HAS DIFFERENT BEHAVIOR WHEN RECORDING FFMPEG AS THREAD
                            # EVEN thread_record_streaming WAS DECLARED FIRST, IT ALWAYS GET LOADED AT LAST
                            if sys.platform == "win32":
                                thread_record_streaming = Thread(target=record_streaming_windows, args=(stream_url.url, tmp_recorded_streaming_filepath, show_error_messages), daemon=True)
                                thread_record_streaming.start()

                            elif sys.platform == "linux":
                                thread_record_streaming = Thread(target=record_streaming_linux, args=(stream_url.url, tmp_recorded_streaming_filepath))
                                thread_record_streaming.start()

                        else:
                            msg = "Invalid URL, please enter a valid URL"
                            sg.Popup(msg, title="Info", line_width=50, any_key_closes=True)
                            not_recording = True
                            main_window['-RECORD-STREAMING-'].update(('Stop Record Streaming','Start Record Streaming')[not_recording], button_color=(('white', ('red', '#283b5b')[not_recording])))

                    else:
                        if sys.platform == "win32":
                            #print("thread_record_streaming.is_alive() = {}".format(thread_record_streaming.is_alive()))
                            stop_record_streaming_windows()

                        elif sys.platform == "linux":
                            #print("thread_record_streaming.is_alive() = {}".format(thread_record_streaming.is_alive()))
                            stop_record_streaming_linux()


        elif event == '-SAVE-RECORDED-STREAMING-':

            tmp_recorded_streaming_filename = "record.mp4"
            tmp_recorded_streaming_filepath = os.path.join(tempfile.gettempdir(), tmp_recorded_streaming_filename)

            if os.path.isfile(tmp_recorded_streaming_filepath):

                saved_recorded_streaming_filename = sg.popup_get_file('', no_window=True, save_as=True, font=FONT, default_path=saved_recorded_streaming_filename, file_types=video_file_types)

                if saved_recorded_streaming_filename:
                    shutil.copy(tmp_recorded_streaming_filepath, saved_recorded_streaming_filename)

            else:
                sg.set_options(font=FONT)
                msg = "No streaming was recorded"
                sg.Popup(msg, title="Info", line_width=50, any_key_closes=True)


        #print("event = {}".format(event))
        #print("values = {}".format(values))

    if thread_transcribe and thread_transcribe.is_alive():
        stop_thread(thread_transcribe)

    if thread_transcribe_starter and thread_transcribe_starter.is_alive():
        stop_thread(thread_transcribe_starter)

    if sys.platform == "win32":
        stop_ffmpeg_windows()
    else:
        stop_ffmpeg_linux()

    remove_temp_files("wav")
    remove_temp_files("flac")
    remove_temp_files("mp4")

    main_window.close()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
