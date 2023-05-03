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
from threading import Timer, Thread
import PySimpleGUI as sg
import tkinter as tk
import httpx
from glob import glob
import ctypes
import ctypes.wintypes
from streamlink import Streamlink
from streamlink.exceptions import NoPluginError, StreamlinkError, StreamError
from datetime import datetime, timedelta
import shutil
import select

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


#=======================================================================================================================================#


'''
# CLOSE CONSOLE WINDOW
import sys
if sys.platform == 'win32':
    # Disable console window
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    ctypes.windll.kernel32.SetConsoleTitleW("My Application")
'''

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)]


not_transcribing = True
filepath = None
wav_filename = None
converter = None
recognizer = None
extracted_regions = None
transcription = None
subtitle_file = None
translated_subtitle_file = None
pool = None
all_threads = []


#-------------------------------------------------------------- CONSTANTS --------------------------------------------------------------#

VERSION = "0.1.14"

GOOGLE_SPEECH_API_KEY = "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw"
GOOGLE_SPEECH_API_URL = "http://www.google.com/speech-api/v2/recognize?client=chromium&lang={lang}&key={key}" # pylint: disable=line-too-long

arraylist_language_code = []
arraylist_language_code.append("af")
arraylist_language_code.append("sq")
arraylist_language_code.append("am")
arraylist_language_code.append("ar")
arraylist_language_code.append("hy")
arraylist_language_code.append("as")
arraylist_language_code.append("ay")
arraylist_language_code.append("az")
arraylist_language_code.append("bm")
arraylist_language_code.append("eu")
arraylist_language_code.append("be")
arraylist_language_code.append("bn")
arraylist_language_code.append("bho")
arraylist_language_code.append("bs")
arraylist_language_code.append("bg")
arraylist_language_code.append("ca")
arraylist_language_code.append("ceb")
arraylist_language_code.append("ny")
arraylist_language_code.append("zh-CN")
arraylist_language_code.append("zh-TW")
arraylist_language_code.append("co")
arraylist_language_code.append("hr")
arraylist_language_code.append("cs")
arraylist_language_code.append("da")
arraylist_language_code.append("dv")
arraylist_language_code.append("doi")
arraylist_language_code.append("nl")
arraylist_language_code.append("en")
arraylist_language_code.append("eo")
arraylist_language_code.append("et")
arraylist_language_code.append("ee")
arraylist_language_code.append("fil")
arraylist_language_code.append("fi")
arraylist_language_code.append("fr")
arraylist_language_code.append("fy")
arraylist_language_code.append("gl")
arraylist_language_code.append("ka")
arraylist_language_code.append("de")
arraylist_language_code.append("el")
arraylist_language_code.append("gn")
arraylist_language_code.append("gu")
arraylist_language_code.append("ht")
arraylist_language_code.append("ha")
arraylist_language_code.append("haw")
arraylist_language_code.append("he")
arraylist_language_code.append("hi")
arraylist_language_code.append("hmn")
arraylist_language_code.append("hu")
arraylist_language_code.append("is")
arraylist_language_code.append("ig")
arraylist_language_code.append("ilo")
arraylist_language_code.append("id")
arraylist_language_code.append("ga")
arraylist_language_code.append("it")
arraylist_language_code.append("ja")
arraylist_language_code.append("jv")
arraylist_language_code.append("kn")
arraylist_language_code.append("kk")
arraylist_language_code.append("km")
arraylist_language_code.append("rw")
arraylist_language_code.append("gom")
arraylist_language_code.append("ko")
arraylist_language_code.append("kri")
arraylist_language_code.append("kmr")
arraylist_language_code.append("ckb")
arraylist_language_code.append("ky")
arraylist_language_code.append("lo")
arraylist_language_code.append("la")
arraylist_language_code.append("lv")
arraylist_language_code.append("ln")
arraylist_language_code.append("lt")
arraylist_language_code.append("lg")
arraylist_language_code.append("lb")
arraylist_language_code.append("mk")
arraylist_language_code.append("mg")
arraylist_language_code.append("ms")
arraylist_language_code.append("ml")
arraylist_language_code.append("mt")
arraylist_language_code.append("mi")
arraylist_language_code.append("mr")
arraylist_language_code.append("mni-Mtei")
arraylist_language_code.append("lus")
arraylist_language_code.append("mn")
arraylist_language_code.append("my")
arraylist_language_code.append("ne")
arraylist_language_code.append("no")
arraylist_language_code.append("or")
arraylist_language_code.append("om")
arraylist_language_code.append("ps")
arraylist_language_code.append("fa")
arraylist_language_code.append("pl")
arraylist_language_code.append("pt")
arraylist_language_code.append("pa")
arraylist_language_code.append("qu")
arraylist_language_code.append("ro")
arraylist_language_code.append("ru")
arraylist_language_code.append("sm")
arraylist_language_code.append("sa")
arraylist_language_code.append("gd")
arraylist_language_code.append("nso")
arraylist_language_code.append("sr")
arraylist_language_code.append("st")
arraylist_language_code.append("sn")
arraylist_language_code.append("sd")
arraylist_language_code.append("si")
arraylist_language_code.append("sk")
arraylist_language_code.append("sl")
arraylist_language_code.append("so")
arraylist_language_code.append("es")
arraylist_language_code.append("su")
arraylist_language_code.append("sw")
arraylist_language_code.append("sv")
arraylist_language_code.append("tg")
arraylist_language_code.append("ta")
arraylist_language_code.append("tt")
arraylist_language_code.append("te")
arraylist_language_code.append("th")
arraylist_language_code.append("ti")
arraylist_language_code.append("ts")
arraylist_language_code.append("tr")
arraylist_language_code.append("tk")
arraylist_language_code.append("tw")
arraylist_language_code.append("uk")
arraylist_language_code.append("ur")
arraylist_language_code.append("ug")
arraylist_language_code.append("uz")
arraylist_language_code.append("vi")
arraylist_language_code.append("cy")
arraylist_language_code.append("xh")
arraylist_language_code.append("yi")
arraylist_language_code.append("yo")
arraylist_language_code.append("zu")

arraylist_language = []
arraylist_language.append("Afrikaans");
arraylist_language.append("Albanian");
arraylist_language.append("Amharic");
arraylist_language.append("Arabic");
arraylist_language.append("Armenian");
arraylist_language.append("Assamese");
arraylist_language.append("Aymara");
arraylist_language.append("Azerbaijani");
arraylist_language.append("Bambara");
arraylist_language.append("Basque");
arraylist_language.append("Belarusian");
arraylist_language.append("Bengali");
arraylist_language.append("Bhojpuri");
arraylist_language.append("Bosnian");
arraylist_language.append("Bulgarian");
arraylist_language.append("Catalan");
arraylist_language.append("Cebuano");
arraylist_language.append("Chichewa");
arraylist_language.append("Chinese (Simplified)");
arraylist_language.append("Chinese (Traditional)");
arraylist_language.append("Corsican");
arraylist_language.append("Croatian");
arraylist_language.append("Czech");
arraylist_language.append("Danish");
arraylist_language.append("Dhivehi");
arraylist_language.append("Dogri");
arraylist_language.append("Dutch");
arraylist_language.append("English");
arraylist_language.append("Esperanto");
arraylist_language.append("Estonian");
arraylist_language.append("Ewe");
arraylist_language.append("Filipino");
arraylist_language.append("Finnish");
arraylist_language.append("French");
arraylist_language.append("Frisian");
arraylist_language.append("Galician");
arraylist_language.append("Georgian");
arraylist_language.append("German");
arraylist_language.append("Greek");
arraylist_language.append("Guarani");
arraylist_language.append("Gujarati");
arraylist_language.append("Haitian Creole");
arraylist_language.append("Hausa");
arraylist_language.append("Hawaiian");
arraylist_language.append("Hebrew");
arraylist_language.append("Hindi");
arraylist_language.append("Hmong");
arraylist_language.append("Hungarian");
arraylist_language.append("Icelandic");
arraylist_language.append("Igbo");
arraylist_language.append("Ilocano");
arraylist_language.append("Indonesian");
arraylist_language.append("Irish");
arraylist_language.append("Italian");
arraylist_language.append("Japanese");
arraylist_language.append("Javanese");
arraylist_language.append("Kannada");
arraylist_language.append("Kazakh");
arraylist_language.append("Khmer");
arraylist_language.append("Kinyarwanda");
arraylist_language.append("Konkani");
arraylist_language.append("Korean");
arraylist_language.append("Krio");
arraylist_language.append("Kurdish (Kurmanji)");
arraylist_language.append("Kurdish (Sorani)");
arraylist_language.append("Kyrgyz");
arraylist_language.append("Lao");
arraylist_language.append("Latin");
arraylist_language.append("Latvian");
arraylist_language.append("Lingala");
arraylist_language.append("Lithuanian");
arraylist_language.append("Luganda");
arraylist_language.append("Luxembourgish");
arraylist_language.append("Macedonian");
arraylist_language.append("Malagasy");
arraylist_language.append("Malay");
arraylist_language.append("Malayalam");
arraylist_language.append("Maltese");
arraylist_language.append("Maori");
arraylist_language.append("Marathi");
arraylist_language.append("Meiteilon (Manipuri)");
arraylist_language.append("Mizo");
arraylist_language.append("Mongolian");
arraylist_language.append("Myanmar (Burmese)");
arraylist_language.append("Nepali");
arraylist_language.append("Norwegian");
arraylist_language.append("Odiya (Oriya)");
arraylist_language.append("Oromo");
arraylist_language.append("Pashto");
arraylist_language.append("Persian");
arraylist_language.append("Polish");
arraylist_language.append("Portuguese");
arraylist_language.append("Punjabi");
arraylist_language.append("Quechua");
arraylist_language.append("Romanian");
arraylist_language.append("Russian");
arraylist_language.append("Samoan");
arraylist_language.append("Sanskrit");
arraylist_language.append("Scots Gaelic");
arraylist_language.append("Sepedi");
arraylist_language.append("Serbian");
arraylist_language.append("Sesotho");
arraylist_language.append("Shona");
arraylist_language.append("Sindhi");
arraylist_language.append("Sinhala");
arraylist_language.append("Slovak");
arraylist_language.append("Slovenian");
arraylist_language.append("Somali");
arraylist_language.append("Spanish");
arraylist_language.append("Sundanese");
arraylist_language.append("Swahili");
arraylist_language.append("Swedish");
arraylist_language.append("Tajik");
arraylist_language.append("Tamil");
arraylist_language.append("Tatar");
arraylist_language.append("Telugu");
arraylist_language.append("Thai");
arraylist_language.append("Tigrinya");
arraylist_language.append("Tsonga");
arraylist_language.append("Turkish");
arraylist_language.append("Turkmen");
arraylist_language.append("Twi (Akan)");
arraylist_language.append("Ukrainian");
arraylist_language.append("Urdu");
arraylist_language.append("Uyghur");
arraylist_language.append("Uzbek");
arraylist_language.append("Vietnamese");
arraylist_language.append("Welsh");
arraylist_language.append("Xhosa");
arraylist_language.append("Yiddish");
arraylist_language.append("Yoruba");
arraylist_language.append("Zulu");

map_code_of_language = dict(zip(arraylist_language, arraylist_language_code))
map_language_of_code = dict(zip(arraylist_language_code, arraylist_language))

arraylist_subtitle_format = []
arraylist_subtitle_format.append("srt");
arraylist_subtitle_format.append("vtt");
arraylist_subtitle_format.append("json");
arraylist_subtitle_format.append("raw");


#------------------------------------------------------------MISC FUNCTIONS------------------------------------------------------------#


def srt_formatter(subtitles, padding_before=0, padding_after=0):
    '''
    Serialize a list of subtitles according to the SRT format, with optional time padding.
    '''
    sub_rip_file = pysrt.SubRipFile()
    for i, ((start, end), text) in enumerate(subtitles, start=1):
        item = pysrt.SubRipItem()
        item.index = i
        item.text = six.text_type(text)
        item.start.seconds = max(0, start - padding_before)
        item.end.seconds = end + padding_after
        sub_rip_file.append(item)
    return '\n'.join(six.text_type(item) for item in sub_rip_file)


def vtt_formatter(subtitles, padding_before=0, padding_after=0):
    '''
    Serialize a list of subtitles according to the VTT format, with optional time padding.
    '''
    text = srt_formatter(subtitles, padding_before, padding_after)
    text = 'WEBVTT\n\n' + text.replace(',', '.')
    return text


def json_formatter(subtitles):
    '''
    Serialize a list of subtitles as a JSON blob.
    '''
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


def raw_formatter(subtitles):
    '''
    Serialize a list of subtitles as a newline-delimited string.
    '''
    return ' '.join(text for (_rng, text) in subtitles)


FORMATTERS = {
    'srt': srt_formatter,
    'vtt': vtt_formatter,
    'json': json_formatter,
    'raw': raw_formatter,
}

video_file_types = [
    ('MP4 Files', '*.mp4'),
]


def percentile(arr, percent):
    arr = sorted(arr)
    k = (len(arr) - 1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c: return arr[int(k)]
    d0 = arr[int(f)] * (c - k)
    d1 = arr[int(c)] * (k - f)
    return d0 + d1


def is_same_language(lang1, lang2):
    return lang1.split("-")[0] == lang2.split("-")[0]


class FLACConverter(object):
    def __init__(self, source_path, include_before=0.25, include_after=0.25):
        self.source_path = source_path
        self.include_before = include_before
        self.include_after = include_after

    def __call__(self, region):
        try:
            start, end = region
            start = max(0, start - self.include_before)
            end += self.include_after
            temp = tempfile.NamedTemporaryFile(suffix='.flac', delete=False)
            command = ["ffmpeg","-ss", str(start), "-t", str(end - start), "-y", "-i", self.source_path, "-loglevel", "-1", temp.name]
            if sys.platform == "win32":
                subprocess.check_output(command, stdin=open(os.devnull), creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.check_output(command, stdin=open(os.devnull))

            return temp.read()

        except KeyboardInterrupt:
            return

        except Exception as e:
            not_transcribing = True
            sg.Popup(e, title="Info")
            #main_window.write_event_value('-EXCEPTION-', e)


class SpeechRecognizer(object):
    def __init__(self, language="en", rate=44100, retries=3, api_key=GOOGLE_SPEECH_API_KEY):
        self.language = language
        self.rate = rate
        self.api_key = api_key
        self.retries = retries

    def __call__(self, data):
        try:
            for i in range(self.retries):
                url = GOOGLE_SPEECH_API_URL.format(lang=self.language, key=self.api_key)
                headers = {"Content-Type": "audio/x-flac rate=%d" % self.rate}

                try:
                    resp = requests.post(url, data=data, headers=headers)
                except requests.exceptions.ConnectionError:
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
            return

        except Exception as e:
            not_transcribing = True
            #sg.Popup(e, title="Info")
            main_window.write_event_value('-EXCEPTION-', e)


def which(program):
    '''
    Return the path for a given executable.
    '''
    def is_exe(file_path):
        '''
        Checks whether a file is executable.
        '''
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


def ffmpeg_check():
    '''
    Return the ffmpeg executable name. "None" returned when no executable exists.
    '''
    if which("ffmpeg"):
        return "ffmpeg"
    if which("ffmpeg.exe"):
        return "ffmpeg.exe"
    return None


def extract_audio(filename, main_window, channels=1, rate=16000):
    global not_transcribing

    if not_transcribing: return

    temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)

    if not os.path.isfile(filename):
        #print("The given file does not exist: {0}".format(filename))
        #raise Exception("Invalid filepath: {0}".format(filename))
        not_transcribing=True
        main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))
        #main_window['-OUTPUT-MESSAGES-'].update('The given file does not exist: {0}".format(filename)')
        window_key = '-OUTPUT-MESSAGES-'
        msg = "The given file does not exist: {0}".format(filename)
        append_flag = False
        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    if not ffmpeg_check():
        #print("ffmpeg: Executable not found on machine.")
        #raise Exception("Dependency not found: ffmpeg")
        not_transcribing=True
        main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))
        #main_window['-OUTPUT-MESSAGES-'].update('ffmpeg executable not found on machine')
        window_key = '-OUTPUT-MESSAGES-'
        msg = 'ffmpeg executable not found on machine'
        append_flag = False
        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    #command = ["ffmpeg", "-y", "-i", filename, "-ac", str(channels), "-ar", str(rate), "-loglevel", "-1", temp.name]
    command = ["ffmpeg", "-y", "-i", filename, "-ac", str(channels), "-ar", str(rate), "-loglevel", "error", temp.name]
    ff = FfmpegProgress(command)
    file_display_name = os.path.basename(filename).split('/')[-1]

    try:
        for progress in ff.run_command_with_progress():
            info = 'Converting {} to a temporary WAV file'.format(file_display_name)
            total = 100
            percentage = f'{int(progress*100/100)}%'
            main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (info, 100, percentage, progress))
        main_window.write_event_value("-EVENT-UPDATE-PROGRESS-BAR-", (info, 100, '100%', 100))
    except Exception as e:
        not_transcribing = True
        #sg.Popup(e, title="Info")
        main_window.write_event_value('-EXCEPTION-', e)

    if not_transcribing: return

    if sys.platform == "win32":
        subprocess.check_output(command, stdin=open(os.devnull), creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        subprocess.check_output(command, stdin=open(os.devnull))

    return temp.name, rate


#def find_speech_regions(filename, frame_width=4096, min_region_size=0.5, max_region_size=6):
def find_speech_regions(filename, frame_width=4096, min_region_size=0.3, max_region_size=8):
    global thread_transcribe, not_transcribing

    if not_transcribing: return

    try:
        reader = wave.open(filename)
        sample_width = reader.getsampwidth()
        rate = reader.getframerate()
        n_channels = reader.getnchannels()
    except Exception as e:
        main_window.write_event_value('-EXCEPTION-', e)

    total_duration = reader.getnframes() / rate
    chunk_duration = float(frame_width) / rate
    n_chunks = int(total_duration / chunk_duration)

    if not_transcribing: return

    energies = []
    for i in range(n_chunks):

        if not_transcribing: return

        chunk = reader.readframes(frame_width)
        energies.append(audioop.rms(chunk, sample_width * n_channels))

    threshold = percentile(energies, 0.2)
    elapsed_time = 0
    regions = []
    region_start = None

    i=0
    for energy in energies:

        if not_transcribing: return

        is_silence = energy <= threshold
        max_exceeded = region_start and elapsed_time - region_start >= max_region_size
        if (max_exceeded or is_silence) and region_start:
            if elapsed_time - region_start >= min_region_size:
                regions.append((region_start, elapsed_time))
                region_start = None
        elif (not region_start) and (not is_silence):
            region_start = elapsed_time
        elapsed_time += chunk_duration
        i=i+1
    return regions

'''
def GoogleTranslate(text, src, dst):
    url = 'https://translate.googleapis.com/translate_a/'
    params = 'single?client=gtx&sl='+src+'&tl='+dst+'&dt=t&q='+text;
    with httpx.Client(http2=True) as client:
        client.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': 'https://translate.google.com',})
        response = client.get(url+params)
        #print('response.status_code = {}'.format(response.status_code))
        if response.status_code == 200:
            response_json = response.json()[0]
            #print('response_json = {}'.format(response_json))
            length = len(response_json)
            #print('length = {}'.format(length))
            translation = ''
            for i in range(length):
                #print("{} {}".format(i, response_json[i][0]))
                translation = translation + response_json[i][0]
            return translation
        return
'''

def GoogleTranslate(text, src, dst):
    url = 'https://translate.googleapis.com/translate_a/'
    params = 'single?client=gtx&sl='+src+'&tl='+dst+'&dt=t&q='+text;
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': 'https://translate.google.com',}
    response = requests.get(url+params, headers=headers)
    if response.status_code == 200:
        response_json = response.json()[0]
        length = len(response_json)
        translation = ""
        for i in range(length):
            translation = translation + response_json[i][0]
        return translation
    return


class SentenceTranslator(object):
    def __init__(self, src, dst, patience=-1):
        self.src = src
        self.dst = dst
        self.patience = patience

    def __call__(self, sentence):
        translated_sentence = []
        # handle the special case: empty string.
        if not sentence:
            return None

        translated_sentence = GoogleTranslate(sentence, src=self.src, dst=self.dst)

        fail_to_translate = translated_sentence[-1] == '\n'
        while fail_to_translate and patience:
            translated_sentence = translator.translate(translated_sentence, src=self.src, dst=self.dst).text
            if translated_sentence[-1] == '\n':
                if patience == -1:
                    continue
                patience -= 1
            else:
                fail_to_translate = False
        return translated_sentence


def transcribe(src, dst, filename, subtitle_format, main_window):
    global all_threads, thread_transcribe, not_transcribing, pool

    if not_transcribing: return

    pool = multiprocessing.Pool(10, initializer=NoConsoleProcess)
    wav_filename = None
    audio_rate = None
    subtitle_file = None
    translated_subtitle_file = None
    file_display_name = os.path.basename(filename).split('/')[-1]
    regions = None

    if not_transcribing: return

    window_key = '-OUTPUT-MESSAGES-'
    msg = ''
    append_flag = False
    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    window_key = '-OUTPUT-MESSAGES-'
    msg = "Processing {} :\n".format(file_display_name)
    append_flag = True
    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    window_key = '-OUTPUT-MESSAGES-'
    msg = "Converting {} to a temporary WAV file...\n".format(file_display_name)
    append_flag = True
    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    try:
        wav_filename, audio_rate = extract_audio(filename, main_window)
    except:
        return

    window_key = '-OUTPUT-MESSAGES-'
    msg = "{} converted WAV file is : {}\n".format(file_display_name, wav_filename)
    append_flag = True
    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    if not_transcribing: return

    window_key = '-OUTPUT-MESSAGES-'
    msg = "Finding speech regions of {} WAV file...\n".format(file_display_name)
    append_flag = True
    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    try:
        regions = find_speech_regions(wav_filename)
        num = len(regions)
    except:
        return

    window_key = '-OUTPUT-MESSAGES-'
    msg = "{} speech regions found = {}\n".format(file_display_name, len(regions))
    append_flag = True
    main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

    if not_transcribing: return

    try:
        converter = FLACConverter(source_path=wav_filename)
        recognizer = SpeechRecognizer(language=src, rate=audio_rate, api_key=GOOGLE_SPEECH_API_KEY)
    except:
        return

    transcriptions = []
    translated_transcriptions = []

    if not_transcribing: return

    if regions:
        window_key = '-OUTPUT-MESSAGES-'
        msg = 'Converting {} speech regions to FLAC files...\n'.format(file_display_name)
        append_flag = True
        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

        extracted_regions = []
        info = 'Converting {} speech regions to FLAC files'.format(file_display_name)
        total = 100

        for i, extracted_region in enumerate(pool.imap(converter, regions)):

            if not_transcribing:
                pool.close()
                pool.join()
                pool = None
                return

            extracted_regions.append(extracted_region)

            progress = int(i*100/len(regions))
            percentage = f'{progress}%'
            main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (info, total, percentage, progress))
        main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (info, total, "100%", total))

        if not_transcribing: return

        window_key = '-OUTPUT-MESSAGES-'
        msg = 'Creating {} transcriptions...\n'.format(file_display_name)
        append_flag = True
        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

        info = 'Creating {} transcriptions'.format(file_display_name)
        total = 100

        for i, transcription in enumerate(pool.imap(recognizer, extracted_regions)):

            if not_transcribing:
                pool.close()
                pool.join()
                pool = None
                return
            transcriptions.append(transcription)

            progress = int(i*100/len(regions))
            percentage = f'{progress}%'
            main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (info, total, percentage, progress))
        main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (info, total, "100%", total))

        if not_transcribing: return

        timed_subtitles = [(r, t) for r, t in zip(regions, transcriptions) if t]
        formatter = FORMATTERS.get(subtitle_format)
        formatted_subtitles = formatter(timed_subtitles)

        base, ext = os.path.splitext(filename)
        subtitle_file = "{base}.{format}".format(base=base, format=subtitle_format)

        if not_transcribing: return

        window_key = '-OUTPUT-MESSAGES-'
        msg = "Writing subtitle file for {}\n".format(file_display_name)
        append_flag = True
        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

        with open(subtitle_file, 'wb') as f:
            f.write(formatted_subtitles.encode("utf-8"))
            f.close()

        with open(subtitle_file, 'a') as f:
            f.write("\n")
            f.close()

        if not_transcribing: return

        if (not is_same_language(src, dst)):
            translated_subtitle_file = subtitle_file[ :-4] + '.translated.' + subtitle_format

            if not_transcribing: return

            created_regions = []
            created_transcripts = []
            for entry in timed_subtitles:
                created_regions.append(entry[0])
                created_transcripts.append(entry[1])

            if not_transcribing: return

            window_key = '-OUTPUT-MESSAGES-'
            msg = 'Translating {} subtitles from {} ({}) to {} ({})...\n'.format(file_display_name, map_language_of_code[src], src, map_language_of_code[dst], dst)
            append_flag = True
            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

            info = 'Translating {} subtitles from {} ({}) to {} ({})'.format(file_display_name, map_language_of_code[src], src, map_language_of_code[dst], dst)
            total = 100
            transcript_translator = SentenceTranslator(src=src, dst=dst)
            translated_transcriptions = []

            for i, translated_transcription in enumerate(pool.imap(transcript_translator, created_transcripts)):

                if not_transcribing:
                    pool.close()
                    pool.join()
                    pool = None
                    return

                translated_transcriptions.append(translated_transcription)

                progress = int(i*100/len(timed_subtitles))
                percentage = f'{progress}%'
                main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (info, total, percentage, progress))
            main_window.write_event_value('-EVENT-UPDATE-PROGRESS-BAR-', (info, total, "100%", total))

            if not_transcribing: return

            timed_translated_subtitles = [(r, t) for r, t in zip(created_regions, translated_transcriptions) if t]
            formatter = FORMATTERS.get(subtitle_format)
            formatted_translated_subtitles = formatter(timed_translated_subtitles)

            if not_transcribing: return

            with open(translated_subtitle_file, 'wb') as f:
                f.write(formatted_translated_subtitles.encode("utf-8"))
            with open(translated_subtitle_file, 'a') as f:
                f.write("\n")

            if not_transcribing: return

        window_key = '-OUTPUT-MESSAGES-'
        msg = "{} subtitles file created at :\n  {}\n".format(file_display_name, subtitle_file)
        append_flag = True
        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

        window_key = '-RESULTS-'
        msg = "{}\n".format(subtitle_file)
        append_flag = True
        main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

        if (not is_same_language(src, dst)):
            window_key = '-OUTPUT-MESSAGES-'
            msg = "{} translated subtitles file created at :\n  {}\n" .format(file_display_name, translated_subtitle_file)
            append_flag = True
            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

            window_key = '-RESULTS-'
            msg = "{}\n\n" .format(translated_subtitle_file)
            append_flag = True
            main_window.write_event_value('-EVENT-TRANSCRIBE-MESSAGES-', (window_key, msg, append_flag))

        if not_transcribing: return

    if len(all_threads) > 1:
        for t in all_threads:
            if t.is_alive():
                all_tasks_completed = False
            else:
                all_tasks_completed = True
                pool.close()
                pool.join()
                pool = None
                t.join()
                not_transcribing = True
                main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))
    else:
        pool.close()
        pool.join()
        pool = None
        not_transcribing = True
        main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))

    #remove_temp_files("wav")
    #remove_temp_files("flac")
    #remove_temp_files("mp4")


def remove_temp_files(extension):
    temp_dir = tempfile.gettempdir()
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.endswith("." + extension):
                os.remove(os.path.join(root, file))


def stop_thread(thread):
    exc = ctypes.py_object(SystemExit)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread.ident), exc)
    if res == 0:
        main_window.write_event_value("-EXCEPTION-", "nonexistent thread id")
        raise ValueError("nonexistent thread id")
    elif res > 1:
        # '''if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect'''
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)
        main_window.write_event_value("-EXCEPTION-", "PyThreadState_SetAsyncExc failed")
        raise SystemError("PyThreadState_SetAsyncExc failed")


def pBar(count_value, total, prefix, main_window):
    bar_length = 10
    filled_up_Length = int(round(bar_length*count_value/(total)))
    percentage = round(100.0 * count_value/(total),1)
    #bar = '#' * filled_up_Length + '=' * (bar_length - filled_up_Length)
    bar = '█' * filled_up_Length + '-' * (bar_length - filled_up_Length)
    #text = str('%s[%s] %s%s\r' %(prefix, bar, int(percentage), '%'))
    text = str('%s|%s| %s%s\r' %(prefix, bar, int(percentage), '%'))
    main_window['-OUTPUT-MESSAGES-'].update(text, append = False)


def popup_yes_no(text, title=None):
    layout = [
        [sg.Text(text)],
        [sg.Push(), sg.Button('Yes'), sg.Button('No')],
    ]
    return sg.Window(title if title else text, layout, resizable=True).read(close=True)


def move_center(window):
    screen_width, screen_height = window.get_screen_dimensions()
    win_width, win_height = window.size
    x, y = (screen_width-win_width)//2, ((screen_height-win_height)//2) - 30
    window.move(x, y)


def get_clipboard_text():
    try:
        output = subprocess.check_output(['xclip', '-selection', 'clipboard', '-out'], stderr=subprocess.PIPE).decode()
        if output:
            return output.strip()
        else:
            return None
    except subprocess.CalledProcessError:
        return None


def set_clipboard_text(text):
    subprocess.run(['xclip', '-selection', 'clipboard'], input=text.encode())


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


def record_streaming_windows(hls_url, filename):
    global not_recording, main_window

    ffmpeg_cmd = ['ffmpeg', '-y', '-i', hls_url,  '-movflags', '+frag_keyframe+separate_moof+omit_tfhd_offset+empty_moov', '-fflags', 'nobuffer', filename]
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


def stop_ffmpeg_windows():

    tasklist_output = subprocess.check_output(['tasklist'], creationflags=subprocess.CREATE_NO_WINDOW).decode('utf-8')
    ffmpeg_pid = None
    for line in tasklist_output.split('\n'):
        if "ffmpeg" in line:
            ffmpeg_pid = line.split()[1]
            break
    if ffmpeg_pid:
        devnull = open(os.devnull, 'w')
        #subprocess.Popen(['taskkill', '/F', '/T', '/PID', ffmpeg_pid], stdout=devnull, stderr=devnull, creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.Popen(['taskkill', '/F', '/T', '/PID', ffmpeg_pid], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)


def stop_ffmpeg_linux():

    process_name = 'ffmpeg'
    try:
        output = subprocess.check_output(['ps', '-ef'])
        pid = [line.split()[1] for line in output.decode('utf-8').split('\n') if process_name in line][0]
        subprocess.call(['kill', '-9', str(pid)])
        #print(f"{process_name} has been killed")
    except IndexError:
        #print(f"{process_name} is not running")
        pass


#--------------------------------------------------------------MAIN FUNCTIONS------------------------------------------------------------#


def main():
    global all_threads, thread_transcribe, not_transcribing, pool, not_recording, thread_record_streaming, main_window

    if sys.platform == "win32":
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        kernel32.GlobalLock.argtypes = [ctypes.wintypes.HGLOBAL]
        kernel32.GlobalLock.restype = ctypes.wintypes.LPVOID
        kernel32.GlobalSize.argtypes = [ctypes.wintypes.HGLOBAL]
        kernel32.GlobalSize.restype = ctypes.c_size_t
        user32.OpenClipboard.argtypes = [ctypes.wintypes.HWND]
        user32.OpenClipboard.restype = ctypes.wintypes.BOOL
        user32.CloseClipboard.argtypes = []
        user32.CloseClipboard.restype = ctypes.wintypes.BOOL
        user32.GetClipboardData.argtypes = [ctypes.wintypes.UINT]
        user32.GetClipboardData.restype = ctypes.wintypes.HANDLE

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

    parser = argparse.ArgumentParser()
    parser.add_argument('source_path', help="Path to the video or audio files to generate subtitle (use wildcard for multiple files or separate them with space eg. \"file 1.mp4\" \"file 2.mp4\")", nargs='*', default='')

    if last_selected_src:
        parser.add_argument('-S', '--src-language', help="Spoken language", default=last_selected_src)
    else:
        parser.add_argument('-S', '--src-language', help="Spoken language", default="en")

    if last_selected_dst:
        parser.add_argument('-D', '--dst-language', help="Desired language for translation", default=last_selected_dst)
    else:
        parser.add_argument('-D', '--dst-language', help="Desired language for translation", default="id")

    parser.add_argument('-ll', '--list-languages', help="List all available source/translation languages", action='store_true')
    parser.add_argument('-F', '--format', help="Desired subtitle format", default="srt")
    parser.add_argument('-lf', '--list-formats', help="List all available subtitle formats", action='store_true')
    parser.add_argument('-v', '--version', action='version', version=VERSION)

    args = parser.parse_args()

    if args.list_formats:
        print("Supported subtitle formats :")
        for subtitle_format in FORMATTERS.keys():
            print("{format}".format(format=subtitle_format))
        parser.exit(0)

    if args.list_languages:
        print("Supported languages :")
        for code, language in sorted(map_language_of_code.items()):
            print("{code}\t{language}".format(code=code, language=language))
        parser.exit(0)


#------------------------------------------------------------- MAIN WINDOW -------------------------------------------------------------#


    not_transcribing = True
    filepath = None
    browsed_files = []
    filelist = []
    input_string = ''
    subtitle_format = None
    xmax,ymax=sg.Window.get_screen_size()
    wsizex=int(0.75*xmax)
    wsizey=int(0.4*ymax)
    mlszx=int(0.1*wsizex)
    mlszy=int(0.03*wsizey)
    wx=int((xmax-wsizex)/2)
    wy=int((ymax-wsizey)/2)

    font=('Helvetica', 9)

    layout = [
                [
                    sg.Text('Voice language', size=(18,1)),
                    sg.Combo(list(map_code_of_language), default_value='English', enable_events=True, key='-SRC-')
                ],
                [
                    sg.Text('Translation language', size=(18,1)),
                    sg.Combo(list(map_code_of_language), default_value='Indonesian', enable_events=True, key='-DST-')
                ],
                [
                    sg.Text('Subtitle format', size=(18,1)),
                    sg.Combo(list(arraylist_subtitle_format), default_value='srt', enable_events=True, key='-SUBTITLE-FORMAT-')
                ],
                [
                    sg.Text('URL', size=(18,1)), sg.Input(size=(12, 1), expand_x=True, expand_y=True, key='-URL-', enable_events=True, right_click_menu=['&Edit', ['&Paste',]]),
                    sg.Button("Start Record Streaming", size=(24,1), key='-RECORD-STREAMING-')
                ],
                [
                    sg.Text('Thread status', size=(18,1)),
                    sg.Text('NOT RECORDING', size=(20, 1), background_color='green1', text_color='black', expand_x=True, expand_y=True, key='-RECORD-STREAMING-STATUS-'),
                    sg.Text('Duration recorded', size=(16, 1)),
                    sg.Text('0:00:00.000000', size=(6, 1), background_color='green1', text_color='black', expand_x=True, expand_y=True, key='-STREAMING-DURATION-RECORDED-'),
                    sg.Text('', size=(8,1)),
                    sg.Button("Save Recorded Streaming", size=(24,1), key='-SAVE-RECORDED-STREAMING-')

                ],
                [
                    sg.Text("Browsed Files", size=(18,1)),
                    sg.Input(key='-INPUT-', enable_events=True, size=(80,10), expand_x=True, expand_y=True,),
                    sg.Text('', size=(12,1)),
                ],
                [
                    sg.Text("File List", size=(18,1)),
                    sg.Listbox(values=[], key='-LIST-', enable_events=True, size=(80,1), expand_x=True, select_mode=sg.LISTBOX_SELECT_MODE_EXTENDED, expand_y=True, horizontal_scroll=True),
                    sg.Column(
                            [
                                [sg.FilesBrowse("Add", size=(10,1), target='-INPUT-', file_types=(("All Files", "*.*"),), enable_events=True, key="-ADD-")],
                                [sg.Button("Remove", key="-REMOVE-", size=(10,1), expand_x=True, expand_y=False,)],
                                [sg.Button("Clear", key="-CLEAR-", size=(10,1), expand_x=True, expand_y=False,)],
                            ],
                            element_justification='c'
                         )
                ],
                [sg.Text("Progress", key='-INFO-')],
                [
                    sg.ProgressBar(100, orientation='h', size=(88, 1), expand_x=True, expand_y=True, key='-PROGRESS-'),
                    sg.Text("0%", size=(5,1), expand_x=True, expand_y=True, key='-PERCENTAGE-', justification='r')
                ],
                [sg.Text('Progress log')],
                [sg.Multiline(size=(mlszx, mlszy), expand_x=True, expand_y=True, key='-OUTPUT-MESSAGES-')],
                [sg.Text('Results')],
                [sg.Multiline(size=(mlszx, 0.5*mlszy), expand_x=True, expand_y=True, key='-RESULTS-')],
                [sg.Button('Start', expand_x=True, expand_y=True, key='-START-'),sg.Button('Exit', expand_x=True, expand_y=True)]
            ]

    main_window = sg.Window('PyAutoSRT-'+VERSION, layout, font=font, resizable=True, keep_on_top=True, finalize=True)
    main_window['-SRC-'].block_focus()
    FONT_TYPE = "Arial"
    FONT_SIZE = 9
    sg.set_options(font=(FONT_TYPE, FONT_SIZE))

    if args.source_path:
        if "*" in str(args.source_path) or len(args.source_path)>1:
            for arg in args.source_path:
                filelist += glob(arg)
            for file in filelist:
                if os.path.isfile(file):
                    filepath = os.path.join(os.getcwd(), file)
                    input_string = input_string + filepath + ";"
                    main_window['-INPUT-'].update(input_string)
                else:
                    filepath = None
                    main_window['-OUTPUT-MESSAGES-'].update('File path you typed is not exist, please browse it\n')

            input_string = input_string[:-1]
            main_window['-INPUT-'].update(input_string)

        else:
            if not os.sep in args.source_path[0]:
                filepath = os.path.join(os.getcwd(),args.source_path[0])
            else:
                filepath = args.source_path[0]

            if os.path.isfile(filepath):
                main_window['-INPUT-'].update(filepath)
            else:
                main_window['-INPUT-'].update('')
                main_window['-OUTPUT-MESSAGES-'].update('File path you typed is not exist, please browse it\n\n')

    if args.src_language:
        if args.src_language not in map_language_of_code.keys():
            main_window['-OUTPUT-MESSAGES-'].update('Source language you typed is not supported\nPlease select one from combobox\n\n', append=True)
        elif args.src_language in map_language_of_code.keys():
            src = args.src_language
            main_window['-SRC-'].update(map_language_of_code[src])
            last_selected_src = src
            src_file = open(src_filepath, "w")
            src_file.write(src)
            src_file.close()

    if args.dst_language:
        if args.dst_language not in map_language_of_code.keys():
            main_window['-OUTPUT-MESSAGES-'].update('Translation language you typed is not supported\nPlease select one from combobox\n\n', append=True)
        elif args.dst_language in map_language_of_code.keys():
            dst = args.dst_language
            main_window['-DST-'].update(map_language_of_code[dst])
            last_selected_dst = dst
            dst_file = open(dst_filepath, "w")
            dst_file.write(dst)
            dst_file.close()

    if args.format:
        if args.format not in FORMATTERS.keys():
            main_window['-OUTPUT-MESSAGES-'].update('Subtitle format you typed is not supported\nPlease select one from combobox', append=True)
        else:
            subtitle_format = args.format
            main_window['-SUBTITLE-FORMAT-'].update(subtitle_format)

    if not args.format:
        subtitle_format = 'srt'
        main_window['-SUBTITLE-FORMAT-'].update(subtitle_format)


    if (sys.platform == "win32"):
        main_window.TKroot.attributes('-topmost', True)
        main_window.TKroot.attributes('-topmost', False)

    if not (sys.platform == "win32"):
        main_window.TKroot.attributes('-topmost', 1)
        main_window.TKroot.attributes('-topmost', 0)

    src_name = str(main_window['-SRC-'].get())
    if src_name:
        src = map_code_of_language[src_name]
    else:
        src_name = "English"
        src = map_code_of_language[src_name]
    last_selected_src = src
    src_file = open(src_filepath, "w")
    src_file.write(src)
    src_file.close()

    dst_name = str(main_window['-DST-'].get())
    if dst_name:
        dst = map_code_of_language[dst_name]
    else:
        dst_name = "Indonesian"
        dst = map_code_of_language[dst_name]
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

        src = map_code_of_language[str(main_window['-SRC-'].get())]
        last_selected_src = src
        src_file = open(src_filepath, "w")
        src_file.write(src)
        src_file.close()

        dst = map_code_of_language[str(main_window['-DST-'].get())]
        last_selected_dst = dst
        dst_file = open(dst_filepath, "w")
        dst_file.write(dst)
        dst_file.close()


        if (event == 'Exit') or (event == sg.WIN_CLOSED):

            if not not_transcribing:
                answer = popup_yes_no('             Are you sure?              ', title='Confirm')
                if 'Yes' in answer:
                    break
            else:
                break


        elif event == '-INPUT-':

            n = 0
            browsed_files += values['-INPUT-'].split(';')
            #print("browsed_files = {}".format(browsed_files))

            if browsed_files != ['']:
                if len(filelist) == 0:
                    filelist += browsed_files
                else:
                    for file in browsed_files:
                        if file not in filelist and os.path.isfile(file):
                            filelist.append(file)

            main_window['-LIST-'].update(filelist)
            browsed_files = []


        elif event == '-REMOVE-':

            listbox_selection = values['-LIST-']
            if listbox_selection:
                for index in listbox_selection[::-1]:
                    filelist.remove(index)
                main_window['-LIST-'].update(filelist)


        elif event == 'Delete:46' and values['-LIST-']:

            listbox_selection = values['-LIST-']
            if listbox_selection:
                for index in listbox_selection[::-1]:
                    filelist.remove(index)
                main_window['-LIST-'].update(filelist)


        elif event == '-CLEAR-':

            main_window['-INPUT-'].update('')
            filelist = []
            main_window['-LIST-'].update(filelist)
            main_window['-OUTPUT-MESSAGES-'].update('')
            main_window['-RESULTS-'].update('')


        elif event == '-START-':

            src = map_code_of_language[str(main_window['-SRC-'].get())]
            dst = map_code_of_language[str(main_window['-DST-'].get())]
            #filelist += values['-INPUT-'].split(';')
            subtitle_format = values['-SUBTITLE-FORMAT-']
            thread_transcribe = None
            all_threads = []
            main_window['-RESULTS-'].update('', append=False)

            if len(filelist)>0 and src and dst and subtitle_format:
                not_transcribing = not not_transcribing

                if not not_transcribing:
                    main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))
                    for file in filelist:
                        if os.path.isfile(file):
                            filepath = os.path.join(os.getcwd(), file)
                            thread_transcribe = Thread(target=transcribe, args=(src, dst, filepath, subtitle_format, main_window), daemon=True)
                            thread_transcribe.start()
                            all_threads.append(thread_transcribe)
                        else:
                            filepath = None
                            main_window['-OUTPUT-MESSAGES-'].update('File path you typed is not exist, please browse it\n\n')

                else:
                    not_transcribing = not not_transcribing
                    answer = popup_yes_no('             Are you sure?              ', title='Confirm')
                    if 'Yes' in answer:
                        not_transcribing = True
                        main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))
                        for t in all_threads:
                            t.join()
                        main_window['-OUTPUT-MESSAGES-'].update('', append=False)
                        main_window['-OUTPUT-MESSAGES-'].update("All tasks has been canceled", append=False)

            else:
                main_window['-OUTPUT-MESSAGES-'].update("You should pick a file first")


        elif event == '-EVENT-TRANSCRIBE-MESSAGES-':

            m = values[event]
            window_key = m[0]
            msg = m[1]
            append_flag = m[2]
            main_window[window_key].update(msg, append=append_flag)
            scroll_to_last_line(main_window, main_window[window_key])


        elif event == '-EVENT-UPDATE-PROGRESS-BAR-':

            pb = values[event]
            info = pb[0]
            total = pb[1]
            percentage = pb[2]
            progress = pb[3]

            main_window['-INFO-'].update(info)
            main_window['-PERCENTAGE-'].update(percentage)
            main_window['-PROGRESS-'].update(progress)


        elif event == '-EXCEPTION-':

            e = str(values[event]).strip()
            #sg.Popup("File format is not supported", title="Info", line_width=50)
            sg.Popup(e, title="Info", line_width=50)
            main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))
            main_window['-OUTPUT-MESSAGES-'].update('', append=False)


        elif event.endswith('+R') and values['-URL-']:

            if sys.platform == "win32":
                user32.OpenClipboard(None)
                clipboard_data = user32.GetClipboardData(1)  # 1 is CF_TEXT
                if clipboard_data:
                    data = ctypes.c_char_p(clipboard_data)
                    main_window['-URL-'].update(data.value.decode('utf-8'))
                user32.CloseClipboard()
            elif sys.platform == "linux":
                text = get_clipboard_text()
                if text:
                    main_window['-URL-'].update(text.strip())


        elif event == 'Paste':

            if sys.platform == "win32":
                user32.OpenClipboard(None)
                clipboard_data = user32.GetClipboardData(1)  # 1 is CF_TEXT
                if clipboard_data:
                    data = ctypes.c_char_p(clipboard_data)
                    main_window['-URL-'].update(data.value.decode('utf-8'))
                user32.CloseClipboard()
            elif sys.platform == "linux":
                text = get_clipboard_text()
                if text:
                    main_window['-URL-'].update(text.strip())


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
                sg.set_options(font=("Helvetica", 9))
                sg.Popup('Invalid URL, please enter a valid URL.                   ', title="Info", line_width=50)
                main_window['-URL-'].update('')

            else:
                not_recording = not not_recording
                main_window['-RECORD-STREAMING-'].update(('Stop Record Streaming','Start Record Streaming')[not_recording], button_color=(('white', ('red', '#283b5b')[not_recording])))

                #if tmp_recorded_streaming_filepath and os.path.isfile(tmp_recorded_streaming_filepath): os.remove(tmp_recorded_streaming_filepath)

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
                        sg.Popup('Invalid URL, please enter a valid URL.                   ', title="Info", line_width=50)
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

            '''
            if not args.video_filename:
                tmp_recorded_streaming_filename = "record.mp4"
            else:
                tmp_recorded_streaming_filename = args.video_filename
            '''

            tmp_recorded_streaming_filename = "record.mp4"
            tmp_recorded_streaming_filepath = os.path.join(tempfile.gettempdir(), tmp_recorded_streaming_filename)

            if os.path.isfile(tmp_recorded_streaming_filepath):

                saved_recorded_streaming_filename = sg.popup_get_file('', no_window=True, save_as=True, font=(FONT_TYPE, FONT_SIZE), default_path=saved_recorded_streaming_filename, file_types=video_file_types)

                if saved_recorded_streaming_filename:
                    shutil.copy(tmp_recorded_streaming_filepath, saved_recorded_streaming_filename)

            else:
                FONT_TYPE = "Helvetica"
                FONT_SIZE = 9
                sg.set_options(font=(FONT_TYPE, FONT_SIZE))
                sg.Popup("No streaming was recorded.                             ", title="Info", line_width=50)


    if thread_transcribe and thread_transcribe.is_alive():
        stop_thread(thread_transcribe)

    if sys.platform == "win32":
        stop_ffmpeg_windows()
    else:
        stop_ffmpeg_linux()

    remove_temp_files("wav")
    remove_temp_files("flac")
    remove_temp_files("mp4")

    main_window.close()
    sys.exit(0)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
