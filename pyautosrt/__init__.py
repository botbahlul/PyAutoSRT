#!/usr/bin/env python
from __future__ import absolute_import, print_function, unicode_literals

import audioop
import math
import multiprocessing
import subprocess
import threading
import io, sys, os, time, datetime, signal
import argparse
import tempfile
import wave
import json
import requests
try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

from progressbar import ProgressBar, Percentage, Bar, ETA
from googletrans import Translator
import pysrt
import six
import ntpath
from pathlib import Path
from threading import Timer, Thread
import PySimpleGUI as sg
import contextlib
from contextlib import suppress

not_transcribing = True
canceled = False
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

GOOGLE_SPEECH_API_KEY = "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw"
GOOGLE_SPEECH_API_URL = "http://www.google.com/speech-api/v2/recognize?client=chromium&lang={lang}&key={key}" # pylint: disable=line-too-long
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0 Win64 x64)'


#---------------------------------------------------------------CONSTANTS---------------------------------------------------------------#


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


def my_exchandler(type, value, traceback):
    print("")


sys.excepthook = my_exchandler


def srt_formatter(subtitles, padding_before=0, padding_after=0):
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


def vtt_formatter(subtitles, padding_before=0, padding_after=0):
    """
    Serialize a list of subtitles according to the VTT format, with optional time padding.
    """
    text = srt_formatter(subtitles, padding_before, padding_after)
    text = 'WEBVTT\n\n' + text.replace(',', '.')
    return text


def json_formatter(subtitles):
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


def raw_formatter(subtitles):
    """
    Serialize a list of subtitles as a newline-delimited string.
    """
    return ' '.join(text for (_rng, text) in subtitles)


FORMATTERS = {
    'srt': srt_formatter,
    'vtt': vtt_formatter,
    'json': json_formatter,
    'raw': raw_formatter,
}


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


class ThreadWithResult(Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, *, daemon=None):
        def function():
            self.result = target(*args, **kwargs)
        super().__init__(group=group, target=function, name=name, daemon=daemon)

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
            command = ["ffmpeg","-ss", str(start), "-t", str(end - start), "-y", "-i", self.source_path, "-loglevel", "error", temp.name]
            subprocess.check_output(command, stdin=open(os.devnull))
            return temp.read()

        except KeyboardInterrupt:
            return


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


def which(program):
    """
    Return the path for a given executable.
    """
    def is_exe(file_path):
        """
        Checks whether a file is executable.
        """
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
    """
    Return the ffmpeg executable name. "None" returned when no executable exists.
    """
    if which("ffmpeg"):
        return "ffmpeg"
    if which("ffmpeg.exe"):
        return "ffmpeg.exe"
    return None


def extract_audio(filename, channels=1, rate=16000):
    temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    if not os.path.isfile(filename):
        #print("The given file does not exist: {0}".format(filename))
        raise Exception("Invalid filepath: {0}".format(filename))
    if not ffmpeg_check():
        #print("ffmpeg: Executable not found on machine.")
        raise Exception("Dependency not found: ffmpeg")
    command = ["ffmpeg", "-y", "-i", filename, "-ac", str(channels), "-ar", str(rate), "-loglevel", "error", temp.name]
    subprocess.check_output(command, stdin=open(os.devnull))
    return temp.name, rate


#def find_speech_regions(filename, frame_width=4096, min_region_size=0.5, max_region_size=6):
def find_speech_regions(filename, frame_width=4096, min_region_size=0.3, max_region_size=8):
    global pool, wav_filename, subtitle_file, translated_subtitle_file, converter, recognizer, extracted_regions, transcriptions

    reader = wave.open(filename)
    sample_width = reader.getsampwidth()
    rate = reader.getframerate()
    n_channels = reader.getnchannels()

    total_duration = reader.getnframes() / rate
    chunk_duration = float(frame_width) / rate
    n_chunks = int(total_duration / chunk_duration)

    energies = []

    for i in range(n_chunks):
        chunk = reader.readframes(frame_width)
        energies.append(audioop.rms(chunk, sample_width * n_channels))

    threshold = percentile(energies, 0.2)

    elapsed_time = 0

    regions = []
    region_start = None

    i=0
    for energy in energies:
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


class TranscriptionTranslator(object):
    def __init__(self, src, dest, patience=-1):
        self.src = src
        self.dest = dest
        self.patience = patience

    def __call__(self, sentence):
        translator = Translator()
        translated_sentence = []

        # handle the special case: empty string.
        if not sentence:
            return None
        translated_sentence = translator.translate(sentence, src=self.src, dest=self.dest).text
        fail_to_translate = translated_sentence[-1] == '\n'
        while fail_to_translate and patience:
            translated_sentence = translator.translate(translated_sentence, src=self.src, dest=self.dest).text
            if translated_sentence[-1] == '\n':
                if patience == -1:
                    continue
                patience -= 1
            else:
                fail_to_translate = False
        return translated_sentence


class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


def transcribe(src, dest, filename, subtitle_format, main_window):
    global thread_transcribe, not_transcribing, canceled, pool, wav_filename, subtitle_file, translated_subtitle_file, subtitle_folder_name, converter, recognizer, extracted_regions, transcriptions

    pool = multiprocessing.Pool(10)
    wav_filename = None
    subtitle_file = None
    translated_subtitle_file = None
    file_display_name = os.path.basename(filename).split('/')[-1]
    regions = None

    with contextlib.suppress(Exception):
        main_window['-ML1-'].update("")
        main_window['-ML1-'].update("Converting {} to a temporary WAV file\n".format(file_display_name), append=True)
        wav_filename, audio_rate = extract_audio(filename)
        main_window['-ML1-'].update("Converted WAV file is : {}\n\n".format(wav_filename), append=True)
        time.sleep(2)

    with contextlib.suppress(Exception):
        main_window['-ML1-'].update("Finding speech regions of WAV file\n", append=True)
        regions = find_speech_regions(wav_filename)
        num = len(regions)
        main_window['-ML1-'].update("Speech regions found = {}\n\n".format(len(regions)) , append=True)
        time.sleep(2)

    converter = FLACConverter(source_path=wav_filename)
    recognizer = SpeechRecognizer(language=src, rate=audio_rate, api_key=GOOGLE_SPEECH_API_KEY)
    transcriptions = []
    translated_transcriptions = []

    if regions:
        with contextlib.suppress(Exception):
            extracted_regions = []
            for i, extracted_region in enumerate(pool.imap(converter, regions)):
                extracted_regions.append(extracted_region)
                pBar(i, len(regions), 'Converting speech regions to FLAC files : ', main_window)
            pBar(len(regions), len(regions), 'Converting speech regions to FLAC files : ', main_window)
        
            for i, transcription in enumerate(pool.imap(recognizer, extracted_regions)):
                transcriptions.append(transcription)
                pBar(i, len(regions), 'Creating transcriptions                 : ', main_window)
            pBar(len(regions), len(regions), 'Creating transcriptions                 : ', main_window)
 
            timed_subtitles = [(r, t) for r, t in zip(regions, transcriptions) if t]
            formatter = FORMATTERS.get(subtitle_format)
            formatted_subtitles = formatter(timed_subtitles)

            base, ext = os.path.splitext(filename)
            subtitle_file = "{base}.{format}".format(base=base, format=subtitle_format)

            with open(subtitle_file, 'wb') as f:
                f.write(formatted_subtitles.encode("utf-8"))
                f.close()

            with open(subtitle_file, 'a') as f:
                f.write("\n")
                f.close()

            if (not is_same_language(src, dest)):
                translated_subtitle_file = subtitle_file[ :-4] + '_translated.' + subtitle_format
                transcript_translator = TranscriptionTranslator(src=src, dest=dest)
                translated_transcriptions = []
                for i, translated_transcription in enumerate(pool.imap(transcript_translator, transcriptions)):
                    translated_transcriptions.append(translated_transcription)
                    pBar(i, len(transcriptions), 'Translating from %5s to %5s         : ' %(src, dest), main_window)
                pBar(len(transcriptions), len(transcriptions), 'Translating from %5s to %5s         : ' %(src, dest), main_window)

                timed_translated_subtitles = [(r, t) for r, t in zip(regions, translated_transcriptions) if t]
                formatter = FORMATTERS.get(subtitle_format)
                formatted_translated_subtitles = formatter(timed_translated_subtitles)

                with open(translated_subtitle_file, 'wb') as f:
                    f.write(formatted_translated_subtitles.encode("utf-8"))
                with open(translated_subtitle_file, 'a') as f:
                    f.write("\n")

            main_window['-ML1-'].update('\n\nDone.\n\n', append = True)
            main_window['-ML1-'].update("Subtitles file created at               : {}\n".format(subtitle_file), append = True)
            if (not is_same_language(src, dest)):
                main_window['-ML1-'].update("\nTranslated subtitles file created at    : {}\n" .format(translated_subtitle_file), append = True)

    pool.close()
    pool.join()
    pool = None
    os.remove(wav_filename)
    not_transcribing = True
    main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))

    return subtitle_file


def progressbar(count_value, total, prefix='', suffix=''):
    bar_length = 50
    filled_up_Length = int(round(bar_length* count_value / float(total)))
    percentage = round(100.0 * count_value/float(total),1)
    bar = '#' * filled_up_Length + '-' * (bar_length - filled_up_Length)
    sys.stdout.write('%s [%s] %s%s %s\r' %(prefix, bar, percentage, '%', suffix))
    sys.stdout.flush()


def pBar(count_value, total, prefix, main_window):
    bar_length = 10
    filled_up_Length = int(round(bar_length*count_value/(total)))
    percentage = round(100.0 * count_value/(total),1)
    bar = '#' * filled_up_Length + '=' * (bar_length - filled_up_Length)
    text = str('%s [%s] %s%s\r' %(prefix, bar, int(percentage), '%'))
    main_window['-ML1-'].update(text, append = False)


def check_cancel_status(main_window):
    global not_transcribing, canceled, pool, wav_filename, subtitle_file, translated_subtitle_file, subtitle_folder_name, converter, recognizer, extracted_regions, transcriptions

    while True:
        if canceled:
            main_window['-ML1-'].print("")
            main_window['-ML1-'].print("Canceling all tasks")
            if pool:
                pool.terminate()
                pool.close()
            break
    return

def signal_handle(_signal, frame):
    print("Stopping the Jobs.")

def check_stop_signal():
    global stop_event
    """
    Checks continuously (every 0.1 s) if a "stop" flag has been set in the database.
    Needs to run in its own thread.
    """
    while True:
        if io.check_stop():
            print("Program was aborted by user.")
            print("Setting threading stop event...")
            stop_event.set()
            break
        sleep(0.1)


#-------------------------------------------------------------GUI FUNCTIONS-------------------------------------------------------------#

def steal_focus():
    global main_window

    if(sys.platform == "win32"):
        main_window.TKroot.attributes('-topmost', True)
        main_window.TKroot.attributes('-topmost', False)
        main_window.TKroot.deiconify()
    if(sys.platform == "linux"):
        main_window.TKroot.attributes('-topmost', 1)
        main_window.TKroot.attributes('-topmost', 0)
        main_window.BringToFront()


def font_length(Text, Font, Size) :
    f = tf.Font(family=Font , size = Size)
    length = f.measure(Text)
    #print(length)
    return length



#--------------------------------------------------------------MAIN FUNCTIONS------------------------------------------------------------#


def main():
    global process_transcribe, thread_transcribe, not_transcribing, canceled, stop_event

    parser = argparse.ArgumentParser()
    parser.add_argument('-S', '--src-language', help="Voice language", default="en")
    parser.add_argument('-D', '--dst-language', help="Desired language for translation", default="en")
    parser.add_argument('-v', '--version', action='version', version='0.0.4')
    parser.add_argument('-lf', '--list-formats', help="List all available subtitle formats", action='store_true')
    parser.add_argument('-ll', '--list-languages', help="List all available source/destination languages", action='store_true')

    args = parser.parse_args()

    if args.src_language not in map_language_of_code.keys():
        print("Source language not supported. Run with --list-languages to see all supported languages.")
        sys.exit(0)

    if args.dst_language not in map_language_of_code.keys():
        print("Destination language not supported. Run with --list-languages to see all supported languages.")
        sys.exit(0)

    if not args.src_language:
        src = "en"

    if args.src_language:
        src = args.src_language

    if args.dst_language:
        dest = args.dst_language

    if not args.dst_language:
        dst = "en"


    if args.list_formats:
        print("List of formats:")
        for subtitle_format in FORMATTERS.keys():
            print("{format}".format(format=subtitle_format))
        return 0

    if args.list_languages:
        print("List of all languages:")
        for code, language in sorted(map_language_of_code.items()):
            print("{code}\t{language}".format(code=code, language=language))
        sys.exit(0)


#--------------------------------------------------------------MAIN WINDOW--------------------------------------------------------------#


    xmax,ymax=sg.Window.get_screen_size()
    wsizex=int(0.6*xmax)
    wsizey=int(0.3*ymax)
    mlszx=int(0.1*wsizex)
    mlszy=int(0.05*wsizey)
    wx=int((xmax-wsizex)/2)
    wy=int((ymax-wsizey)/2)

    if not src==None:
        combo_src=map_language_of_code[src]
    else:
        combo_src='Indonesian'
    if not dest==None:
        combo_dest=map_language_of_code[dest]
    else:
        combo_dest='English'

    #sg.set_options(font=('Courier New', 10))
    #sg.set_options(font=('Monospaced', 9))
    font=('Consolas', 9)

    layout = [[sg.Text('Voice language       :'),
               sg.Combo(list(map_code_of_language), default_value=combo_src, enable_events=True, key='-SRC-')],
              [sg.Text('Translation language :'),
               sg.Combo(list(map_code_of_language), default_value=combo_dest, enable_events=True, key='-DST-')],
              [sg.Text('Subtitle format      :'),
               sg.Combo(list(arraylist_subtitle_format), default_value='srt', enable_events=True, key='-SUBTITLE-FORMAT-')],
              [sg.Text('Filepath             :',), sg.InputText(key='-FILEPATH-', expand_x=True, expand_y=True), sg.FileBrowse()],
              [sg.Button('Start', expand_x=True, expand_y=True, key='-START-')],
              [sg.Multiline(size=(mlszx, mlszy), expand_x=True, expand_y=True, key='-ML1-')],
              [sg.Button('Exit', expand_x=True, expand_y=True)]]

    main_window = sg.Window('PyAutoSRT', layout, font=font, resizable=True, keep_on_top=True, finalize=True)
    main_window['-SRC-'].block_focus()

    not_transcribing = True

    if  (sys.platform == "win32"):
        main_window.TKroot.attributes('-topmost', True)
        main_window.TKroot.attributes('-topmost', False)

    if not (sys.platform == "win32"):
        main_window.TKroot.attributes('-topmost', 1)
        main_window.TKroot.attributes('-topmost', 0)



#---------------------------------------------------------------MAIN LOOP--------------------------------------------------------------#

    while True:
        #window, event, values = sg.read_all_windows()
        event, values = main_window.read()

        if (event == 'Exit') or (event == sg.WIN_CLOSED):
            break

        elif event == '-SRC-':
            src = map_code_of_language[str(main_window['-SRC-'].get())]
            dst = map_code_of_language[str(main_window['-DST-'].get())]

        elif event == '-DST-':
            src = map_code_of_language[str(main_window['-SRC-'].get())]
            dst = map_code_of_language[str(main_window['-DST-'].get())]

        elif event == '-START-':
            src = map_code_of_language[str(main_window['-SRC-'].get())]
            dst = map_code_of_language[str(main_window['-DST-'].get())]
            filepath = values['-FILEPATH-']
            subtitle_format = values['-SUBTITLE-FORMAT-']

            if filepath and src and dst and subtitle_format:
                not_transcribing = not not_transcribing
                if not not_transcribing:
                    main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))
                    sys.tracebacklimit = 0
                    with contextlib.suppress(Exception):
                        thread_transcribe = StoppableThread(target=transcribe, args=(src, dst, filepath, subtitle_format, main_window), daemon=True)
                        thread_transcribe.start()
                        all_threads.append(thread_transcribe)

                else:
                    canceled = True
                    not_transcribing = True
                    main_window['-START-'].update(('Cancel','Start')[not_transcribing], button_color=(('white', ('red', '#283b5b')[not_transcribing])))
                    sys.tracebacklimit = 0
                    with contextlib.suppress(Exception):
                        for t in all_threads:
                            t.join()
                    main_window['-ML1-'].update("", append=False)
                    main_window['-ML1-'].update("All tasks has been canceled", append=False)

            else:
                main_window['-ML1-'].update("You should pick a file first")

    main_window.close()
    sys.exit(0)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()

