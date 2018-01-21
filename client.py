import sys
import json
import uuid
import datetime
import platform
import requests
import websockets
import asyncio
from urllib.parse import urlencode


class SpeechClient:
    # ---- CONSTRUCTOR ----

    def __init__(self, api_key):
        self.uuid = self.__generate_id()
        self.connection_id = self.__generate_id()
        self.request_id = self.__generate_id()
        self.auth_token = self.__obtain_auth_token(api_key)

        self.endpoint_interactive = r'wss://speech.platform.bing.com/speech/recognition/interactive/cognitiveservices/v1'
        self.endpoint_conversation = r'wss://speech.platform.bing.com/speech/recognition/conversation/cognitiveservices/v1'
        self.endpoint_dictation = r'wss://speech.platform.bing.com/speech/recognition/dictation/cognitiveservices/v1'

        self.chunk_size = 4096
        self.is_ongoing_turn = False
        self.cur_hypothesis = ''
        self.phrase = ''


    # ---- PUBLIC METHODS ----

    async def send_stt_request(self, audio_file_path):

        url = self.endpoint_interactive + '?language=en-US&format=simple'
        headers = {'Authorization': 'Bearer ' + self.auth_token,
                   'X-ConnectionId': self.connection_id}

        async with websockets.client.connect(url, extra_headers=headers) as ws:
            try:
                ws.handshake(url, origin='https://speech.platform.bing.com')

                # DEBUG PRINT
                # print('Handshake successful!')
                # print(ws.host)
            except websockets.exceptions.InvalidHandshake as e:
                print('Handshake error: {0}'.format(e))

            context = {
                'system': {
                    'version': '5.4'
                },
                'os': {
                    'platform': platform.system(),
                    'name': platform.system() + ' ' + platform.version(),
                    'version': platform.version()
                },
                'device': {
                    'manufacturer': 'SpeechSample',
                    'model': 'SpeechSample',
                    'version': '1.0.00000'
                }
            }
            payload = {'context': context}

            msg = 'Path: speech.config\r\n'
            msg += 'Content-Type: application/json; charset=utf-8\r\n'
            msg += 'X-Timestamp: ' + str(datetime.datetime.now())[:-3] + 'Z\r\n'
            msg += '\r\n' + json.dumps(payload)

            # DEBUG PRINT
            # print(msg)

            ws.send(msg)

            # r = await ws.recv()
            # print(r)

            with open(audio_file_path, 'rb') as f_audio:
                num_chunks = 0
                while True:
                    audio_chunk = f_audio.read(self.chunk_size)
                    if not audio_chunk:
                        break
                    num_chunks += 1

                    msg = b'Path: audio\r\n'
                    msg += b'Content-Type: audio/x-wav\r\n'
                    msg += b'X-RequestId: ' + bytearray(self.request_id, 'ascii') + b'\r\n'
                    msg += b'X-Timestamp: ' + bytearray(str(datetime.datetime.now())[:-3], 'ascii') + b'Z\r\n'
                    # prepend the length of the header in 2-byte big-endian format
                    msg = len(msg).to_bytes(2, byteorder='big') + msg

                    msg += b'\r\n' + audio_chunk

                    # DEBUG PRINT
                    print(msg)

                    # await ws.send(audio_chunk)
                    await ws.send(msg)

                    try:
                        self.process_response(ws, await ws.recv())
                    except websockets.exceptions.ConnectionClosed as e:
                        print('Connection closed: {0}'.format(e))

            # ws.close()


    async def process_response(self, ws, r):
        response_path = self.__parse_header_value(r, 'Path')

        if response_path is None:
            ws.close()
            return

        if response_path == 'turn.start':
            self.is_ongoing_turn = True
        elif response_path == 'speech.startDetected':
            pass
        elif response_path == 'speech.hypothesis':
            self.cur_hypothesis = self.__parse_body_json(r)['Text']
            print('Current hypothesis: ' + self.cur_hypothesis)
            pass
        elif response_path == 'speech.phrase':
            self.phrase = self.__parse_body_json(r)['Text']
            print('Predicted phrase: ' + self.cur_hypothesis)
        elif response_path == 'speech.endDetected':
            pass
        elif response_path == 'turn.end':
            self.is_ongoing_turn = False

        # expect more incoming messages
        if self.is_ongoing_turn:
            try:
                self.process_response(ws, await ws.recv())
            except websockets.exceptions.ConnectionClosed as e:
                print('Connection closed: {0}'.format(e))


    # ---- PRIVATE METHODS ----

    def __obtain_auth_token(self, api_key):
        url = 'https://api.cognitive.microsoft.com/sts/v1.0/issueToken'
        headers = {
            'Content-type': 'application/x-www-form-urlencoded',
            'Content-Length': '0',
            'Ocp-Apim-Subscription-Key': api_key
        }

        r = requests.post(url, headers=headers)

        # DEBUG PRINT
        # print(r.headers['content-type'])
        # print(r.encoding)
        # print(r.text)

        if r.status_code == 200:
            data = r.text
        else:
            r.raise_for_status()

        return data


    def __generate_id(self):
        return str(uuid.uuid4()).replace('-', '')


    def __parse_header_value(self, r, header_to_find):
        for line in r.split('\n'):
            if len(line) == 0:
                break
            header_prompt = header_to_find + ': '
            if line.startswith(header_prompt):
                return line.lstrip(header_prompt)

        print('Error: invalid response header.')

        return None


    def __parse_body_json(self, r):
        body_str = ''
        body_dict = None

        r_as_lines = r.split('\n')
        for i, line in enumerate(r_as_lines):
            if len(line) == 0:
                if i < len(r_as_lines) - 1:
                    # load the lines from the header-body separator until the end (corresponding to a JSON) into a dictionary
                    try:
                        body_dict = json.loads('\n'.join(r_as_lines[(i + 1):]))
                    except json.JSONDecodeError as e:
                        print('Error: the response body is not a valid JSON document.')
                else:
                    print('Error: no body found in the response.')
                break

        return body_dict


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Please, provide your key to access the Bing Speech API.')
        exit()

    client = SpeechClient(sys.argv[1])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.send_stt_request('data/whatstheweatherlike.wav'))
    loop.close()
