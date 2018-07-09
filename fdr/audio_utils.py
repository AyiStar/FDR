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

    def say(self, content, speed=5, volume=5, person=0, pitch=5):
        result  = self.client.synthesis(content, 'zh', 1, {'vol': volume, 'per': person, 'spd': speed, 'pit': pitch})
        sound = AudioSegment.from_mp3(BytesIO(result))
        play(sound)