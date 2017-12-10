# Библиотеки распознавания и синтеза речи
import queue

import speech_recognition as sr
from gtts import gTTS

# misc
import logging
import os
import time

# Воспроизведение речи
from pygame import mixer

mixer.init()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# Statement from SpeechRecognition.recognize_google()
# Because sometimes sr.recognize_google() fails due to field 'confidence' don't exists in json
# So we will get all statements in json style and beautify them
class Statement:
    def __init__(self, dict):
        self.confidence = dict['confidence']
        self.text = dict['transcript'].lower()

    def __repr__(self):
        return "[{}] {}".format(self.confidence, self.text)

    def __str__(self):
        return self.text

    def __gt__(self, other):
        return self.confidence > other.confidence


class Speech_AI:
    def __init__(self, google_threshold=0.5):
        self._recognizer = sr.Recognizer()
        self._microphone = sr.Microphone()

        self.google_threshold = google_threshold  # min allowed confidence in speech recognition

        self._mp3_name = "generated_sounds/speech"
        self.be_quiet = False

        self.questions = queue.Queue()
        self.questions.put('Вы посетили медицинский центр Инвитро?')
        self.questions.put('Оправдались ли ваши ожидания?')
        self.questions.put('Оцените центр по пятибальной шкале.')
        self.questions.put('Теперь вы можете оставить комментарий в свободной форме.')

        self.answers = {}

    def work(self):

        print('Минутку тишины, пожалуйста...')
        with self._microphone as source:
            self._recognizer.adjust_for_ambient_noise(source)

        i = 0
        while True:

            if self.questions.empty():
                break

            # question
            key = self.questions.get()

            # ask
            print(key)
            self.say(self._mp3_name + str(i) + '.mp3', key)
            i += 1

            # response
            with self._microphone as source:
                audio = self._recognizer.listen(source)
            print("Понял, идет распознавание...")
            statements = self.recognize(audio)
            best_statement = self.choose_best_statement(statements)

            # response verification
            print('Вы сказали: ', best_statement)
            self.answers.update({key: best_statement})

            # logic
            if key == 'Вы посетили медицинский центр Инвитро?' and 'нет' in best_statement.__str__().lower():
                self.questions = queue.Queue()
                self.questions.put('Пожалуйста, укажите причину в свободной форме.')

            print()

        # end politely
        print(self.answers)
        self.say(self._mp3_name + '.mp3', 'Спасибо.')

        # save results
        with open("results/result.txt", "a") as myfile:
            myfile.write(' '.join(str(k) + '_' + str(v) for k, v in self.answers.items()))

    # recognize google can return json if show_all is True
    # returns:
    # * on success: list of Statement objects
    # * on error: if error arises, return empty list
    def recognize(self, audio):
        statements = []
        try:
            json = self._recognizer.recognize_google(audio, language="ru_RU", show_all=True)
            statements = self.json_to_statements(json)
        except sr.UnknownValueError:
            print("[GoogleSR] Неизвестное выражение")
        except sr.RequestError as e:
            print("[GoogleSR] Не могу получить данные; {0}".format(e))
        return statements

    # json to statements (check class in beginning of this script)
    def json_to_statements(self, json):
        statements = []
        if len(json) is not 0:
            for dict in json['alternative']:
                if 'confidence' not in dict:
                    dict['confidence'] = self.google_threshold + 0.1  # must not be filtered
                statements.append(Statement(dict))
        return statements

    # get best google recognized statement
    def choose_best_statement(self, statements):
        if statements:
            return max(statements, key=lambda s: s.confidence)
        else:
            return None

    # get synthesized mp3 and play it with pygame
    def say(self, filename, phrase):
        # Synthesize answer
        # todo check exceptons there
        print("[GoogleTTS] Начало запроса")
        print(filename)
        try:
            tts = gTTS(text=phrase, lang="ru")
            tts.save(filename)
        except Exception as e:
            print("[GoogleTTS] Не удалось синтезировать речь: {}".format(e.strerror))
            return
        # Play answer
        mixer.music.load(filename)
        mixer.music.play()

        while mixer.music.get_busy():
            time.sleep(0.1)

    # keyboard exception handler
    def shutdown(self, export=False):
        if export:
            self.bot.trainer.export_for_training('corpus/last_session_corpus.json')
            print("База данных экспортирована в корпус last_session_corpus.json")

        # self._clean_up()
        print("Завершение работы")

    # free memory
    def clean_up(self):
        os.remove(self._mp3_name)


def main():
    ai = Speech_AI()
    try:
        ai.work()
    except KeyboardInterrupt:
        ai.shutdown()


main()
