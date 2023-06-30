from flask import Flask, render_template, request
import yt_dlp as youtube_dl
import os
import subprocess
import speech_recognition as sr
from pydub import AudioSegment
from pydub.utils import make_chunks
from pydub.silence import split_on_silence
from yake import KeywordExtractor
from pydub.effects import normalize
import noisereduce as nr
from pydub.silence import split_on_silence
import librosa
import numpy as np
import webrtcvad
import soundfile as sf

app = Flask(__name__)

language_options = {
    "English (US)": "en-US",
    "English (UK)": "en-GB",
    "English (IN)": "en-IN",
    "Tamil (India)": "ta-IN",
    "Telugu (India)": "te-IN",
    "Hindi (India)": "hi-IN",
    "French (France)": "fr-FR",
    "Kannada (India)": "kn-IN"
}

def transcribe_audio(filename, language='en-US'):
    transcriptions = []
    audio = AudioSegment.from_wav(filename)
    chunks = split_on_silence(audio, min_silence_len=500, silence_thresh=-40, keep_silence=900)
    for i, chunk in enumerate(chunks):
        chunk.export(f"./chunked/{i}.wav", format="wav")
        file = f"./chunked/{i}.wav"
        r = sr.Recognizer()

        with sr.AudioFile(file) as source:
            audio_listened = r.record(source)
            try:
                rec = r.recognize_google(audio_listened, language=language)
                transcriptions.append(rec)
            except sr.UnknownValueError:
                print("I don't recognize your audio")
            except sr.RequestError as e:
                print("Could not get the result.")

    transcript = ' '.join(transcriptions)
    return transcript

def extract_keywords(transcript, language='en'):
    extractor = KeywordExtractor(lan=language, top=10)
    keywords = extractor.extract_keywords(transcript)
    return [keyword for keyword, score in keywords]

try:
    os.makedirs("chunked")
except:
    pass

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        youtube_url = request.form.get('youtube_url')
        uploaded_file = request.files.get('audio_file')
        selected_language = request.form.get('language')

        if youtube_url:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '192',
                }],
                'outtmpl': 'audio/%(id)s.%(ext)s',
                'extractor_args': {
                    'youtube': {
                        'no_warnings': True,
                    },
                },
            }
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                video_id = info.get('id', None)
                if video_id:
                    ydl.download([youtube_url])
                    audio_path = f"audio/{video_id}.wav"
                    transcription = transcribe_audio(audio_path, language=selected_language)
                    keywords = extract_keywords(transcription, language=selected_language.split('-')[0])
                    return render_template('index.html', transcription=transcription, keywords=keywords, language_options=language_options, selected_language=selected_language)
                else:
                    return render_template('index.html', error="Failed to extract video ID.", language_options=language_options)

        elif uploaded_file:
            audio_path = f"audio/{uploaded_file.filename}"
            uploaded_file.save(audio_path)
            transcription = transcribe_audio(audio_path, language=selected_language)
            keywords = extract_keywords(transcription, language=selected_language.split('-')[0])
            return render_template('index.html', transcription=transcription, keywords=keywords, language_options=language_options, selected_language=selected_language)

    return render_template('index.html', language_options=language_options)


if __name__ == "__main__":
    app.run(debug=True)
