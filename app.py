from flask import Flask, render_template, request
import yt_dlp as youtube_dl
import os
import subprocess
import speech_recognition as sr
from pydub import AudioSegment
from pydub.utils import make_chunks
from yake import KeywordExtractor

app = Flask(__name__)

language_options = {
    "English (US)": "en",
    "English (UK)": "en",
    "Tamil (India)": "ta",
    "Telugu (India)": "te",
    "Hindi (India)": "hi",
    "French (France)": "fr",
    "Kannada (India)": "kn"
}

def transcribe_audio(filename, language='en-US'):
    transcriptions = []
    myaudio = AudioSegment.from_wav(filename)
    chunks_length = 8000
    chunks = make_chunks(myaudio, chunks_length)
    for i, chunk in enumerate(chunks):
        chunkName = f"./chunked/{os.path.basename(filename)}_{i}.wav"
        print(f"I am exporting {chunkName}")
        chunk.export(chunkName, format="wav")
        file = chunkName
        r = sr.Recognizer()
        with sr.AudioFile(file) as source:
            audio_listened = r.listen(source)
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
