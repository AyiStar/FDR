from aip import AipSpeech
from pydub import AudioSegment
from pydub.playback import play
from io import BytesIO

class SpeechRobot():

    def __init__(self):
        self._APP_ID = '11341420'
        self._API_KEY = 'GMHod5vVooBOAAgmQ3wClXKr'
        self._SECRET_KEY = '07DS72Ar5OEMXkYRMxhwyrB8U23C8sMG'
        self.client = AipSpeech(self._APP_ID, self._API_KEY, self._SECRET_KEY)

    def say(self, content):
        result  = self.client.synthesis(content, 'zh', 1, {'vol': 5, 'per':1, 'spd':5, 'pitch':5})
        sound = AudioSegment.from_mp3(BytesIO(result))
        play(sound)