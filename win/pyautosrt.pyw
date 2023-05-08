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
from threading import Timer, Thread
import PySimpleGUI as sg
import tkinter as tk
import httpx
from glob import glob
import ctypes
if sys.platform == "win32":
    import win32clipboard
from streamlink import Streamlink
from streamlink.exceptions import NoPluginError, StreamlinkError, StreamError
from datetime import datetime, timedelta
import shutil
import select
import magic

#import warnings
#warnings.filterwarnings("ignore", category=DeprecationWarning)
#warnings.filterwarnings("ignore", category=RuntimeWarning)

#sys.tracebacklimit = 0


#======================================================== ffmpeg_progress_yield ========================================================#


import re
#import subprocess
from typing import Any, Callable, Iterator, List, Optional, Union


def to_ms(**kwargs: Union[float, int, str]) -> int:
    hour = int(kwargs.get("hour", 0))
    minute = int(kwargs.get("min", 0))
    sec = int(kwargs.get("sec", 0))
    ms = int(kwargs.get("ms", 0))

    return (hour * 60 * 60 * 1000) + (minute * 60 * 1000) + (sec * 1000) + ms


def _probe_duration(cmd: List[str]) -> Optional[int]:
    '''
    Get the duration via ffprobe from input media file
    in case ffmpeg was run with loglevel=error.

    Args:
        cmd (List[str]): A list of command line elements, e.g. ["ffmpeg", "-i", ...]

    Returns:
        Optional[int]: The duration in milliseconds.
    '''

    def _get_file_name(cmd: List[str]) -> Optional[str]:
        try:
            idx = cmd.index("-i")
            return cmd[idx + 1]
        except ValueError:
            return None

    file_name = _get_file_name(cmd)
    if file_name is None:
        return None

    try:
        if sys.platform == "win32":
            output = subprocess.check_output(
                [
                    "ffprobe",
                    "-loglevel",
                    "-1",
                    "-hide_banner",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    file_name,
                ],
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            output = subprocess.check_output(
                [
                    "ffprobe",
                    "-loglevel",
                    "-1",
                    "-hide_banner",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    file_name,
                ],
                universal_newlines=True,
            )

        return int(float(output.strip()) * 1000)
    except Exception:
        # TODO: add logging
        return None


def _uses_error_loglevel(cmd: List[str]) -> bool:
    try:
        idx = cmd.index("-loglevel")
        if cmd[idx + 1] == "error":
            return True
        else:
            return False
    except ValueError:
        return False


class FfmpegProgress:
    DUR_REGEX = re.compile(
        r"Duration: (?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})"
    )
    TIME_REGEX = re.compile(
        r"out_time=(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})"
    )

    def __init__(self, cmd: List[str], dry_run: bool = False) -> None:
        '''Initialize the FfmpegProgress class.

        Args:
            cmd (List[str]): A list of command line elements, e.g. ["ffmpeg", "-i", ...]
            dry_run (bool, optional): Only show what would be done. Defaults to False.
        '''
        self.cmd = cmd
        self.stderr: Union[str, None] = None
        self.dry_run = dry_run
        self.process: Any = None
        self.stderr_callback: Union[Callable[[str], None], None] = None
        if sys.platform == "win32":
            self.base_popen_kwargs = {
                "stdin": subprocess.PIPE,  # Apply stdin isolation by creating separate pipe.
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "universal_newlines": False,
                "shell": True,
            }
        else:
            self.base_popen_kwargs = {
                "stdin": subprocess.PIPE,  # Apply stdin isolation by creating separate pipe.
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "universal_newlines": False,
            }

    def set_stderr_callback(self, callback: Callable[[str], None]) -> None:
        '''
        Set a callback function to be called on stderr output.
        The callback function must accept a single string argument.
        Note that this is called on every line of stderr output, so it can be called a lot.
        Also note that stdout/stderr are joined into one stream, so you might get stdout output in the callback.

        Args:
            callback (Callable[[str], None]): A callback function that accepts a single string argument.
        '''
        if not callable(callback) or len(callback.__code__.co_varnames) != 1:
            raise ValueError(
                "Callback must be a function that accepts only one argument"
            )

        self.stderr_callback = callback

    def run_command_with_progress(
        self, popen_kwargs=None, duration_override: Union[float, None] = None
    ) -> Iterator[int]:
        '''
        Run an ffmpeg command, trying to capture the process output and calculate
        the duration / progress.
        Yields the progress in percent.

        Args:
            popen_kwargs (dict, optional): A dict to specify extra arguments to the popen call, e.g. { creationflags: CREATE_NO_WINDOW }
            duration_override (float, optional): The duration in seconds. If not specified, it will be calculated from the ffmpeg output.

        Raises:
            RuntimeError: If the command fails, an exception is raised.

        Yields:
            Iterator[int]: A generator that yields the progress in percent.
        '''
        if self.dry_run:
            return self.cmd

        total_dur: Union[None, int] = None
        if _uses_error_loglevel(self.cmd):
            total_dur = _probe_duration(self.cmd)

        cmd_with_progress = (
            [self.cmd[0]] + ["-progress", "-", "-nostats"] + self.cmd[1:]
        )

        stderr = []
        base_popen_kwargs = self.base_popen_kwargs.copy()
        if popen_kwargs is not None:
            base_popen_kwargs.update(popen_kwargs)

        if sys.platform == "wind32":
            self.process = subprocess.Popen(
                cmd_with_progress,
                **base_popen_kwargs,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )  # type: ignore
        else:
            self.process = subprocess.Popen(
                cmd_with_progress,
                **base_popen_kwargs,
            )  # type: ignore

        yield 0

        while True:
            if self.process.stdout is None:
                continue

            stderr_line = (
                self.process.stdout.readline().decode("utf-8", errors="replace").strip()
            )

            if self.stderr_callback:
                self.stderr_callback(stderr_line)

            if stderr_line == '' and self.process.poll() is not None:
                break

            stderr.append(stderr_line.strip())

            self.stderr = "\n".join(stderr)

            if total_dur is None:
                total_dur_match = self.DUR_REGEX.search(stderr_line)
                if total_dur_match:
                    total_dur = to_ms(**total_dur_match.groupdict())
                    continue
                elif duration_override is not None:
                    # use the override (should apply in the first loop)
                    total_dur = int(duration_override * 1000)
                    continue

            if total_dur:
                progress_time = FfmpegProgress.TIME_REGEX.search(stderr_line)
                if progress_time:
                    elapsed_time = to_ms(**progress_time.groupdict())
                    yield int(elapsed_time * 100/ total_dur)

        if self.process is None or self.process.returncode != 0:
            #print(self.process)
            #print(self.process.returncode)
            _pretty_stderr = "\n".join(stderr)
            raise RuntimeError(f"Error running command {self.cmd}: {_pretty_stderr}")

        yield 100
        self.process = None

    def quit_gracefully(self) -> None:
        '''
        Quit the ffmpeg process by sending 'q'

        Raises:
            RuntimeError: If no process is found.
        '''
        if self.process is None:
            raise RuntimeError("No process found. Did you run the command?")

        self.process.communicate(input=b"q")
        self.process.kill()
        self.process = None

    def quit(self) -> None:
        '''
        Quit the ffmpeg process by sending SIGKILL.

        Raises:
            RuntimeError: If no process is found.
        '''
        if self.process is None:
            raise RuntimeError("No process found. Did you run the command?")

        self.process.kill()
        self.process = None


#=============================================================== autosrt ===============================================================#


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


def is_video_file(file_path, error_messages_callback=None):
    try:
        mime_type = magic.from_file(file_path, mime=True)
        return mime_type.startswith('video/')
    except Exception as e:
        if error_messages_callback:
            error_messages_callback(e)
        else:
            print(e)
        return


def is_audio_file(file_path, error_messages_callback=None):
    try:
        mime_type = magic.from_file(file_path, mime=True)
        return mime_type.startswith('audio/')
    except Exception as e:
        if error_messages_callback:
            error_messages_callback(e)
        else:
            print(e)
        return


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

        self.code_of_name = dict(zip(self.list_names, self.list_codes))
        self.name_of_code = dict(zip(self.list_codes, self.list_names))

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

    def get_name(self, get_code):
        return self.dict.get(get_code.lower(), "")

    def get_code(self, language):
        for get_code, lang in self.dict.items():
            if lang.lower() == language.lower():
                return get_code
        return ""


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

        command = [
                    "ffmpeg",
                    "-y",
                    "-i", media_filepath,
                    "-ac", str(self.channels),
                    "-ar", str(self.rate),
                    "-loglevel", "error",
                    "-hide_banner",
                    temp.name
                  ]

        try:
            # RUNNING ffmpeg WITHOUT SHOWING PROGRESSS
            #use_shell = True if os.name == "nt" else False
            #subprocess.check_output(command, stdin=open(os.devnull), shell=use_shell)

            # RUNNING ffmpeg WITH PROGRESSS
            ff = FfmpegProgress(command)
            percentage = 0
            for progress in ff.run_command_with_progress():
                percentage = progress
                if self.progress_callback:
                    self.progress_callback(media_filepath, percentage)
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
                self.error_messages_callback(e)
            else:
                print(e)
            return

        if sys.platform == "win32":
            subprocess.check_output(command, stdin=open(os.devnull), creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.check_output(command, stdin=open(os.devnull))


# DEFINE progress_callback FUNCTION TO SHOW ffmpeg PROGRESS
# IF WE'RE IN pysimplegui ENVIRONMENT WE CAN DO :
#def show_progress(percentage):
    #global main_window
    #main_window.write_event_value('-UPDATE-PROGRESS-', percentage) AND HANDLE THAT EVENT IN pysimplegui MAIN LOOP
# IF WE'RE IN console ENVIRONMENT WE CAN DO :
#def show_progress(percentage):
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
            start, end = region
            start = max(0, start - self.include_before)
            end += self.include_after
            temp = tempfile.NamedTemporaryFile(suffix='.flac', delete=False)
            command = [
                        "ffmpeg",
                        "-ss", str(start),
                        "-t", str(end - start),
                        "-y",
                        "-i", self.wav_filepath,
                        "-loglevel", "error",
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
            Read SRT formatted subtitle file and return subtitles as list of tuples
            """
            timed_subtitles = []
            with open(srt_file_path, 'r') as srt_file:
                lines = srt_file.readlines()
                # Split the subtitle file into subtitle blocks
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


#=======================================================================================================================================#

#----------------------------------------------------------- MISC FUNCTIONS -----------------------------------------------------------#


VERSION = "0.1.17"

'''
from autosrt import Language, WavConverter,  SpeechRegionFinder, FLACConverter, SpeechRecognizer, SentenceTranslator, \
    SubtitleFormatter,  SubtitleWriter, \
    stop_ffmpeg_windows, stop_ffmpeg_linux, remove_temp_files, is_same_language, is_video_file, is_audio_file
'''

def show_progress(media_filepath, progress):
    global main_window
    file_display_name = os.path.basename(media_filepath).split('/')[-1]
    info = 'Converting {} to a temporary WAV file'.format(file_display_name)
    total = 100
    percentage = f'{int(progress*100/100)}%'
    main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (info, total, percentage, progress))


def show_error_messages(messages):
    global main_window, not_transcribing
    not_transcribing = True
    main_window.write_event_value("-EXCEPTION-", messages)


# RUN A THREAD FOR EACH MEDIA FILE IN PARALEL
def transcribe(src, dst, media_filepath, subtitle_format, event, n_media_filepaths):
    global thread_transcribe, thread_transcribe_starter, not_transcribing, pool, main_window, completed_tasks

    if not_transcribing: return

    window_key = '-PROGRESS-LOG-'
    msg = ''
    append_flag = False
    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    window_key = '-RESULTS-'
    msg = ''
    append_flag = False
    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    if not_transcribing: return

    language = Language()
    wav_filepath = None
    sample_rate = None

    base, ext = os.path.splitext(media_filepath)
    subtitle_filepath = "{base}.{format}".format(base=base, format=subtitle_format)
    if os.path.isfile(subtitle_filepath): os.remove(subtitle_filepath)

    if not is_same_language(src, dst, error_messages_callback=show_error_messages):
        translated_subtitle_filepath = subtitle_filepath[ :-4] + '.translated.' + subtitle_format
        if os.path.isfile(translated_subtitle_filepath): os.remove(translated_subtitle_filepath)

    regions = None
    file_display_name = os.path.basename(media_filepath).split('/')[-1]

    window_key = '-PROGRESS-LOG-'
    msg = "Processing {} :\n".format(file_display_name)
    append_flag = True
    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    window_key = '-PROGRESS-LOG-'
    msg = "Converting {} to a temporary WAV file...\n".format(file_display_name)
    append_flag = True
    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    try:
        wav_converter = WavConverter(progress_callback=show_progress, error_messages_callback=show_error_messages)
        wav_filepath, sample_rate = wav_converter(media_filepath)
    except Exception as e:
        not_transcribing = True
        main_window.write_event_value("-EXCEPTION-", e)
        return

    if not_transcribing: return

    window_key = '-PROGRESS-LOG-'
    msg = "{} converted WAV file is : {}\n".format(file_display_name, wav_filepath)
    append_flag = True
    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    window_key = '-PROGRESS-LOG-'
    msg = "Finding speech regions of {} WAV file...\n".format(file_display_name)
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
    msg = "{} speech regions found = {}\n".format(file_display_name, len(regions))
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
            msg = 'Converting {} speech regions to FLAC files...\n'.format(file_display_name)
            append_flag = True
            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

            extracted_regions = []
            info = 'Converting {} speech regions to FLAC files'.format(file_display_name)
            total = 100

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
                main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (info, total, percentage, progress))
            main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (info, total, "100%", total))

            if not_transcribing:
                if pool[media_filepath]:
                    pool[media_filepath].terminate()
                    pool[media_filepath].close()
                    pool[media_filepath].join()
                    pool[media_filepath] = None
                return

            window_key = '-PROGRESS-LOG-'
            msg = 'Creating {} transcriptions...\n'.format(file_display_name)
            append_flag = True
            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

            info = 'Creating {} transcriptions'.format(file_display_name)
            total = 100

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
                main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (info, total, percentage, progress))
            main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (info, total, "100%", total))

            if not_transcribing:
                if pool[media_filepath]:
                    pool[media_filepath].terminate()
                    pool[media_filepath].close()
                    pool[media_filepath].join()
                    pool[media_filepath] = None
                return

            window_key = '-PROGRESS-LOG-'
            msg = "Writing subtitle file for {}\n".format(file_display_name)
            append_flag = True
            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

            writer = SubtitleWriter(regions, transcriptions, subtitle_format, error_messages_callback=show_error_messages)
            writer.write(subtitle_filepath)

            if not_transcribing:
                if pool[media_filepath]:
                    pool[media_filepath].terminate()
                    pool[media_filepath].close()
                    pool[media_filepath].join()
                    pool[media_filepath] = None
                return

            if not is_same_language(src, dst, error_messages_callback=show_error_messages):
                translated_subtitle_filepath = subtitle_filepath[ :-4] + '.translated.' + subtitle_format

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
                msg = 'Translating {} subtitles from {} ({}) to {} ({})...\n'.format(file_display_name, language.name_of_code[src], src, language.name_of_code[dst], dst)
                append_flag = True
                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                info = 'Translating {} subtitles from {} ({}) to {} ({})'.format(file_display_name, language.name_of_code[src], src, language.name_of_code[dst], dst)
                total = 100

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
                    main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (info, total, percentage, progress))
                main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (info, total, "100%", total))

                if not_transcribing:
                    if pool[media_filepath]:
                        pool[media_filepath].terminate()
                        pool[media_filepath].close()
                        pool[media_filepath].join()
                        pool[media_filepath] = None
                    return

                window_key = '-PROGRESS-LOG-'
                msg = "Writing translated subtitle file for {}\n".format(file_display_name)
                append_flag = True
                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                translation_writer = SubtitleWriter(created_regions, translated_transcriptions, subtitle_format, error_messages_callback=show_error_messages)
                translation_writer.write(translated_subtitle_filepath)

                if not_transcribing:
                    if pool[media_filepath]:
                        pool[media_filepath].terminate()
                        pool[media_filepath].close()
                        pool[media_filepath].join()
                        pool[media_filepath] = None
                    return

            window_key = '-PROGRESS-LOG-'
            msg = "{} subtitles file created at :\n  {}\n".format(file_display_name, subtitle_filepath)
            append_flag = True
            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

            window_key = '-RESULTS-'
            msg = "Results for {} :\n".format(file_display_name)
            append_flag = True
            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

            window_key = '-RESULTS-'
            msg = "{}\n".format(subtitle_filepath)
            append_flag = True
            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

            if not is_same_language(src, dst, error_messages_callback=show_error_messages):
                window_key = '-PROGRESS-LOG-'
                msg = "{} translated subtitles file created at :\n  {}\n" .format(file_display_name, translated_subtitle_filepath)
                append_flag = True
                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

                window_key = '-RESULTS-'
                msg = "{}\n\n" .format(translated_subtitle_filepath)
                append_flag = True
                main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

            event.set()
            completed_tasks += 1
            main_window.write_event_value('-EVENT-TRANSCRIBE-TASKS-COMPLETED-', completed_tasks)

        except Exception as e:
            not_transcribing = True
            main_window.write_event_value("-EXCEPTION-", e)
            return

        if pool[media_filepath]:
            pool[media_filepath].close()
            pool[media_filepath].join()
            pool[media_filepath] = None


def start_transcription(media_filepaths, src, dst, subtitle_format):
    global pool, thread_transcribe, thread_transcribe_starter, completed_tasks, main_window

    n_media_filepaths = len(media_filepaths)
    completion_events = {}  # Dictionary to store completion events
    pool = {media_filepath: multiprocessing.Pool(16, initializer=NoConsoleProcess) for media_filepath in media_filepaths}

    # Create completion events for each media file
    for media_filepath in media_filepaths:
        completion_events[media_filepath] = threading.Event()

    for file in media_filepaths:
        thread_transcribe = Thread(target=transcribe, args=(src, dst, file, subtitle_format, completion_events[media_filepath], n_media_filepaths), daemon=True)
        thread_transcribe.start()

    # Wait for all threads to complete
    for completion_event in completion_events.values():
        completion_event.wait()


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
        [sg.Push(), sg.Button('Yes'), sg.Button('No')],
    ]
    return sg.Window(title if title else text, layout, resizable=True).read(close=True)


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


def is_streaming_url(url):

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
            return False
        except ValueError:
            #print("is_streams = ValueError")
            return False
        except KeyError:
            #print("is_streams = KeyError")
            return False
        except RuntimeError:
            #print("is_streams = RuntimeError")
            return False
        except NoPluginError:
            #print("is_streams = NoPluginError")
            return False
        except StreamlinkError:
            return False
            #print("is_streams = StreamlinkError")
        except StreamError:
            return False
            #print("is_streams = StreamlinkError")
        except NotImplementedError:
            #print("is_streams = NotImplementedError")
            return False
        except Exception as e:
            #print("is_streams = {}".format(e))
            return False
    else:
        #print("is_valid_url(url) = {}".format(is_valid_url(url)))
        return False


def is_valid_url(url):
    try:
        response = httpx.head(url)
        response.raise_for_status()
        return True
    except (httpx.HTTPError, ValueError):
        return False


def record_streaming_windows(hls_url, media_filepath):
    global not_recording, main_window

    ffmpeg_cmd = ['ffmpeg', '-y', '-i', hls_url,  '-movflags', '+frag_keyframe+separate_moof+omit_tfhd_offset+empty_moov', '-fflags', 'nobuffer', media_filepath]
    process = subprocess.Popen(ffmpeg_cmd, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
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


# subprocess.Popen(ffmpeg_cmd) THREAD BEHAVIOR IS DIFFERENT IN LINUX
def record_streaming_linux(url, output_file):
    global recognizing, ffmpeg_start_run_time, first_streaming_duration_recorded, main_window

    #ffmpeg_cmd = ['ffmpeg', '-y', '-i', url, '-c', 'copy', '-bsf:a', 'aac_adtstoasc', '-f', 'mp4', output_file]
    ffmpeg_cmd = ['ffmpeg', '-y', '-i', f'{url}',  '-movflags', '+frag_keyframe+separate_moof+omit_tfhd_offset+empty_moov', '-fflags', 'nobuffer', f'{output_file}']

    ffmpeg_start_run_time = datetime.now()

    # Define a function to run the ffmpeg process in a separate thread
    def run_ffmpeg():
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


def update_media_file_list():
    browsed_files = []
    browsed_files += str(main_window['-INPUT-'].get()).split(';')
    invalid_media_filepath = []

    if browsed_files != ['']:
        for arg in browsed_files:
            if not os.sep in arg:
                argpath = os.path.join(os.getcwd(),arg)
            else:
                argpath = arg
            argpath = argpath.replace("\\", "/")
            filepaths += glob(argpath)

        for file in filepaths:
            file = file.replace("\\", "/")
            if os.path.isfile(file):
                if file not in sg_listbox_values:
                    if is_video_file(file, error_messages_callback=show_error_messages) or is_audio_file(file, error_messages_callback=show_error_messages):
                        sg_listbox_values.append(file)
                    else:
                        invalid_media_filepath.append(file)
            else:
                not_exist_filepath.append(argpath)

        if invalid_media_filepath:
            if len(invalid_media_filepath) == 1:
                msg = "{} is not a valid video or audio file".format(invalid_media_filepath)
            else:
                msg = "{} are not a valid video or audio file".format(invalid_media_filepath)
            sg.Popup(msg, title="Info", line_width=50)

        if not_exist_filepath:
            if len(not_exist_filepath) == 1:
                msg = "{} is not exist".format(not_exist_filepath)
            else:
                msg = "{} are not exist".format(not_exist_filepath)
            sg.Popup(msg, title="Info", line_width=50)

        main_window['-LIST-'].update(sg_listbox_values)

        browsed_files = []
        filepaths = []
        invalid_media_filepath = []
        not_exist_filepath = []


#------------------------------------------------------------ MAIN FUNCTION ------------------------------------------------------------#


def main():
    global not_transcribing, thread_transcribe, thread_transcribe_starter, pool, completed_tasks, not_recording, thread_record_streaming, main_window

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
            print("%8s : %s" %(code, language))
        parser.exit(0)

    browsed_files = []
    filepaths = []
    input_string = ''
    sg_listbox_values = []
    invalid_media_filepath = []
    not_exist_filepath = []

    if args.source_path:

        if "*" in str(args.source_path) or len(args.source_path)>1:

            for arg in args.source_path:
                if not os.sep in arg:
                    argpath = os.path.join(os.getcwd(),arg)
                else:
                    argpath = arg
                argpath = argpath.replace("\\", "/")
                filepaths += glob(argpath)

            for file in filepaths:
                file = file.replace("\\", "/")
                if os.path.isfile(file):
                    if is_video_file(file, error_messages_callback=show_error_messages) or is_audio_file(file, error_messages_callback=show_error_messages):
                        sg_listbox_values.append(file)
                        input_string = input_string + file + ";"

                    else:
                        invalid_media_filepath.append(file)

                else:
                    not_exist_filepath.append(file)

            input_string = input_string[:-1]

        else:

            if not os.sep in args.source_path[0]:
                filepath = os.path.join(os.getcwd(),args.source_path[0])
            else:
                filepath = args.source_path[0]
            filepath = filepath.replace("\\", "/")

            if os.path.isfile(filepath):
                if is_video_file(filepath, error_messages_callback=show_error_messages) or is_audio_file(filepath, error_messages_callback=show_error_messages):
                    sg_listbox_values.append(filepath)
                    input_string = filepath

                else:
                    invalid_media_filepath.append(filepath)

            else:
                not_exist_filepath.append(filepath)

        if invalid_media_filepath:
            if len(invalid_media_filepath) == 1:
                msg = "{} is not a valid video or audio file".format(invalid_media_filepath[0])
            else:
                msg = "{} are not a valid video or audio file".format(invalid_media_filepath)
            sg.Popup(msg, title="Info", line_width=50)

        if not_exist_filepath:
            if len(not_exist_filepath) == 1:
                msg = "{} is not exist".format(not_exist_filepath[0])
            else:
                msg = "{} are not exist".format(not_exist_filepath)
            sg.Popup(msg, title="Info", line_width=50)

    if args.src_language:
        if args.src_language not in language.name_of_code.keys():
            msg = "Voice language you typed is not supported\nPlease select one from combobox"
            show_error_messages(msg)
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
            show_error_messages(msg)
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
            show_error_messages(msg)
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
                    sg.Combo(list(language.code_of_name), default_value=sg_combo_src_values, enable_events=True, key='-SRC-')
                ],
                [
                    sg.Text('Translation language', size=(18,1)),
                    sg.Combo(list(language.code_of_name), default_value=sg_combo_dst_values, enable_events=True, key='-DST-')
                ],
                [
                    sg.Text('Subtitle format', size=(18,1)),
                    sg.Combo(list(SubtitleFormatter.supported_formats), default_value=sg_combo_subtitle_format_values, enable_events=True, key='-SUBTITLE-FORMAT-')
                ],
                [
                    sg.Text('URL', size=(18,1)),
                    sg.Input(size=(58, 1), expand_x=True, expand_y=True, key='-URL-', enable_events=True, right_click_menu=['&Edit', ['&Copy','&Paste',]]),
                    sg.Button("Start Record Streaming", size=(22,1), key='-RECORD-STREAMING-')
                ],
                [
                    sg.Text('Thread status', size=(18,1)),
                    sg.Text('NOT RECORDING', size=(20, 1), background_color='green1', text_color='black', expand_x=True, expand_y=True, key='-RECORD-STREAMING-STATUS-'),
                    sg.Text('Duration recorded', size=(16, 1)),
                    sg.Text('0:00:00.000000', size=(14, 1), background_color='green1', text_color='black', expand_x=True, expand_y=True, key='-STREAMING-DURATION-RECORDED-'),
                    sg.Text('', size=(8,1)),
                    sg.Button("Save Recorded Streaming", size=(22,1), key='-SAVE-RECORDED-STREAMING-')

                ],
                [
                    sg.Text("Browsed Files", size=(18,1)),
                    sg.Input(input_string, size=(32,1), expand_x=True, expand_y=True, key='-INPUT-', enable_events=True, right_click_menu=['&Edit', ['&Copy','&Paste',]],),
                    sg.Button("", size=(9,1), button_color=(sg.theme_background_color(), sg.theme_background_color()), border_width=0, key='-DUMMY-')
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
                [sg.Text("Progress", key='-INFO-')],
                [
                    sg.ProgressBar(100, size=(66,1), orientation='h', expand_x=True, expand_y=True, key='-PROGRESS-'),
                    sg.Text("100%", size=(4,1), expand_x=True, expand_y=True, key='-PERCENTAGE-', justification='r')
                ],
                [sg.Text('Progress log')],
                [sg.Multiline(size=(70, 6), expand_x=True, expand_y=True, enable_events=True, right_click_menu=['&Edit', ['&Copy','&Paste',]], key='-PROGRESS-LOG-')],
                [sg.Text('Results')],
                [sg.Multiline(size=(70, 4), expand_x=True, expand_y=True, enable_events=True, right_click_menu=['&Edit', ['&Copy','&Paste',]], key='-RESULTS-')],
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
    invalid_media_filepath = []
    not_exist_filepath = []

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


        elif event == '-DST-':

            dst = language.code_of_name[str(main_window['-DST-'].get())]
            last_selected_dst = dst
            dst_file = open(dst_filepath, "w")
            dst_file.write(dst)
            dst_file.close()


        elif event == '-INPUT-':

            browsed_files = []
            browsed_files += str(main_window['-INPUT-'].get()).split(';')
            invalid_media_filepath = []

            if browsed_files != ['']:
                for arg in browsed_files:
                    if not os.sep in arg:
                        argpath = os.path.join(os.getcwd(),arg)
                    else:
                        argpath = arg
                    argpath = argpath.replace("\\", "/")
                    filepaths += glob(argpath)

                for file in filepaths:
                    file = file.replace("\\", "/")
                    if os.path.isfile(file):
                        if file not in sg_listbox_values:
                            if is_video_file(file, error_messages_callback=show_error_messages) or is_audio_file(file, error_messages_callback=show_error_messages):
                                sg_listbox_values.append(file)
                            else:
                                invalid_media_filepath.append(file)
                    else:
                        not_exist_filepath.append(argpath)

                if invalid_media_filepath:
                    if len(invalid_media_filepath) == 1:
                        msg = "{} is not a valid video or audio file".format(invalid_media_filepath[0])
                    else:
                        msg = "{} are not a valid video or audio file".format(invalid_media_filepath)
                    sg.Popup(msg, title="Info", line_width=50)

                if not_exist_filepath:
                    if len(not_exist_filepath) == 1:
                        msg = "{} is not exist".format(not_exist_filepath[0])
                    else:
                        msg = "{} are not exist".format(not_exist_filepath)
                    sg.Popup(msg, title="Info", line_width=50)

                main_window['-LIST-'].update(sg_listbox_values)

                browsed_files = []
                filepaths = []
                invalid_media_filepath = []
                not_exist_filepath = []


        elif event == '-REMOVE-':

            listbox_selection = values['-LIST-']
            if listbox_selection:
                for index in listbox_selection[::-1]:
                    sg_listbox_values.remove(index)
                main_window['-LIST-'].update(sg_listbox_values)


        elif event == 'Delete:46' and values['-LIST-']:

            listbox_selection = values['-LIST-']
            if listbox_selection:
                for index in listbox_selection[::-1]:
                    sg_listbox_values.remove(index)
                main_window['-LIST-'].update(sg_listbox_values)


        elif event == '-CLEAR-':

            main_window['-INPUT-'].update('')
            sg_listbox_values = []
            browsed_files = []
            main_window['-LIST-'].update(sg_listbox_values)
            main_window['-PROGRESS-LOG-'].update('')
            main_window['-RESULTS-'].update('')


        elif event == '-START-':

            src = language.code_of_name[str(main_window['-SRC-'].get())]
            dst = language.code_of_name[str(main_window['-DST-'].get())]
            subtitle_format = values['-SUBTITLE-FORMAT-']
            main_window['-RESULTS-'].update('', append=False)

            # RUN A THREADS FOR EACH MEDIA FILES IN PARALEL
            if len(sg_listbox_values)>0 and src and dst and subtitle_format:
                not_transcribing = not not_transcribing

                if not not_transcribing:
                    completed_tasks = 0
                    pool = None
                    main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))
                    thread_transcribe_starter = Thread(target=start_transcription, args=(sg_listbox_values, src, dst, subtitle_format), daemon=True)
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
                sg.Popup(msg, title="Info", line_width=50)


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
                info = pb[0]
                total = pb[1]
                percentage = pb[2]
                progress = pb[3]

                main_window['-INFO-'].update(info)
                main_window['-PERCENTAGE-'].update(percentage)
                main_window['-PROGRESS-'].update(progress)


        elif event == '-EVENT-TRANSCRIBE-TASKS-COMPLETED-':

            completed_tasks = values[event]
            if completed_tasks == len(sg_listbox_values):
                not_transcribing = True
                main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))


        elif event == '-EXCEPTION-':

            e = str(values[event]).strip()
            sg.Popup(e, title="Info", line_width=50)
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

            if not_recording == True:
                is_valid_url_streaming = is_streaming_url(str(values['-URL-']).strip())

            if not is_valid_url_streaming:
                msg = "Invalid URL, please enter a valid URL"
                sg.Popup(msg, title="Info", line_width=50)
                main_window['-URL-'].update('')

            else:
                not_recording = not not_recording
                main_window['-RECORD-STREAMING-'].update(('Stop Record Streaming','Start Record Streaming')[not_recording], button_color=(('white', ('red', '#283b5b')[not_recording])))

                if main_window['-URL-'].get() != (None or '') and not_recording == False:

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
                            thread_record_streaming = Thread(target=record_streaming_windows, args=(stream_url.url, tmp_recorded_streaming_filepath), daemon=True)
                            thread_record_streaming.start()

                        elif sys.platform == "linux":
                            thread_record_streaming = Thread(target=record_streaming_linux, args=(stream_url.url, tmp_recorded_streaming_filepath))
                            thread_record_streaming.start()

                    else:
                        msg = "Invalid URL, please enter a valid URL"
                        sg.Popup(msg, title="Info", line_width=50)
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
                sg.Popup(msg, title="Info", line_width=50)


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
