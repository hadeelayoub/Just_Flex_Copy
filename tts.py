import json
from os.path import join, dirname
import wave
from io import BytesIO

# packages to install
from watson_developer_cloud import TextToSpeechV1
import pyaudio

# access API
text_to_speech = TextToSpeechV1(
    username='d5e293a1-73af-4e75-851f-c458af415c2b',
    password='l6djqI2uYn7A')  # Optional flag

# get sample
speech = text_to_speech.synthesize('Hello world!', accept='audio/wav', voice="en-US_AllisonVoice")

# create stream from sample
wavstream = BytesIO(speech)

# frame size
CHUNK = 1024
BYTE_DEPTH = 2

p = pyaudio.PyAudio()

# open PA stream
stream = p.open(format=p.get_format_from_width(BYTE_DEPTH),
                channels=1,
                rate=22050,
                output=True)

# write the sample stream to it
data = wavstream.read(CHUNK)
while len(data) >= BYTE_DEPTH:
    stream.write(data)
    data = wavstream.read(CHUNK)

stream.stop_stream()
stream.close()
wavstream.close()
p.terminate()