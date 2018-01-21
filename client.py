import sys
import json
import uuid
import datetime
import platform
import requests
import websockets
import asyncio
from threading import Thread


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

        self.language = 'en-US'
        self.response_format = 'simple'

        self.chunk_size = 8192
        self.is_ongoing_turn = False
        self.cur_hypothesis = ''
        self.phrase = ''


    # ---- PUBLIC METHODS ----

    async def send_stt_request(self, language, response_format, audio_file_path):
        self.language = language
        self.response_format = response_format

        url = self.endpoint_interactive + '?language={0}&format={1}'.format(self.language, self.response_format)
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

            # assemble the header for the speech-config message
            msg = 'Path: speech.config\r\n'
            msg += 'Content-Type: application/json; charset=utf-8\r\n'
            msg += 'X-Timestamp: ' + str(datetime.datetime.now())[:-3] + 'Z\r\n'
            # append the body of the message
            msg += '\r\n' + json.dumps(payload)

            # DEBUG PRINT
            # print('>>', msg)

            await ws.send(msg)

            producer_task = asyncio.ensure_future(self.send_audio_msg(ws, audio_file_path))
            consumer_task = asyncio.ensure_future(self.process_response(ws))
            await asyncio.wait(
                [producer_task, consumer_task],
                return_when=asyncio.ALL_COMPLETED,
            )


    async def send_audio_msg(self, ws, audio_file_path):
        with open(audio_file_path, 'rb') as f_audio:
            num_chunks = 0
            while True:
                audio_chunk = f_audio.read(self.chunk_size)
                if not audio_chunk:
                    break
                num_chunks += 1

                # assemble the header for the binary audio message
                msg = b'Path: audio\r\n'
                msg += b'Content-Type: audio/x-wav\r\n'
                msg += b'X-RequestId: ' + bytearray(self.request_id, 'ascii') + b'\r\n'
                msg += b'X-Timestamp: ' + bytearray(str(datetime.datetime.now())[:-3], 'ascii') + b'Z\r\n'
                # prepend the length of the header in 2-byte big-endian format
                msg = len(msg).to_bytes(2, byteorder='big') + msg
                # append the body of the message
                msg += b'\r\n' + audio_chunk

                # DEBUG PRINT
                print('>>', msg)
                sys.stdout.flush()

                try:
                    await ws.send(msg)
                except websockets.exceptions.ConnectionClosed as e:
                    print('Connection closed: {0}'.format(e))
                    return


    async def process_response(self, ws):
        while True:
            try:
                response = await ws.recv()
                print('<<', str(datetime.datetime.now())[:-3] + 'Z\r\n' + response)
                sys.stdout.flush()
            except websockets.exceptions.ConnectionClosed as e:
                print('Connection closed: {0}'.format(e))
                return

            # identify the type of response
            response_path = self.__parse_header_value(response, 'Path')
            if response_path is None:
                print('Error: invalid response header.')
                ws.close()
                return

            if response_path == 'turn.start':
                self.is_ongoing_turn = True
            elif response_path == 'speech.startDetected':
                pass
            elif response_path == 'speech.hypothesis':
                response_dict = self.__parse_body_json(response)
                if response_dict is None:
                    print('Error: no body found in the response. Closing connection.')
                    ws.close()
                    return
                if 'Text' not in response_dict:
                    print('Error: unexpected response header. Closing connection.')
                    ws.close()
                    return
                self.cur_hypothesis = response_dict['Text']
                print('Current hypothesis: ' + self.cur_hypothesis)
            elif response_path == 'speech.phrase':
                response_dict = self.__parse_body_json(response)
                if response_dict is None:
                    print('Error: no body found in the response. Closing connection.')
                    ws.close()
                    return
                if 'RecognitionStatus' not in response_dict:
                    print('Error: unexpected response header. Closing connection.')
                    ws.close()
                    return
                if response_dict['RecognitionStatus'] == 'Success':
                    if self.response_format == 'simple':
                        if 'DisplayText' not in response_dict:
                            print('Error: unexpected response header. Closing connection.')
                            ws.close()
                            return
                        self.phrase = response_dict['DisplayText']
                    elif self.response_format == 'detailed':
                        if 'NBest' not in response_dict or 'Display' not in response_dict['NBest'][0]:
                            print('Error: unexpected response header. Closing connection.')
                            ws.close()
                            return
                        self.phrase = response_dict['NBest'][0]['Display']
                    else:
                        print('Error: unexpected response format. Closing connection.')
                        ws.close()
                        return
            elif response_path == 'speech.endDetected':
                pass
            elif response_path == 'turn.end':
                self.is_ongoing_turn = False
                break
            else:
                print('Error: unexpected response type (Path header). Closing connection.')
                ws.close()
                return


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
        for line in r.split('\r\n'):
            if len(line) == 0:
                break
            header_name = header_to_find + ':'
            if line.startswith(header_name):
                return line[len(header_name):].strip()

        return None


    def __parse_body_json(self, r):
        body_str = ''
        body_dict = None

        r_as_lines = r.split('\r\n')
        for i, line in enumerate(r_as_lines):
            if len(line) == 0:
                if i < len(r_as_lines) - 1:
                    # load the lines from the header-body separator until the end (corresponding to a JSON) into a dictionary
                    try:
                        body_dict = json.loads('\n'.join(r_as_lines[(i + 1):]))
                    except json.JSONDecodeError as e:
                        print('JSON Decode Error: {0}.'.format(e))
                break

        return body_dict


# ---- MAIN ----

def main():
    if len(sys.argv) != 2:
        print('Please, provide your key to access the Bing Speech API.')
        exit()

    language = 'en-US'
    # response_format = 'simple'
    response_format = 'detailed'
    audio_file_path = 'data/whatstheweatherlike.wav'
    # audio_file_path = 'data/test.wav'

    client = SpeechClient(sys.argv[1])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.send_stt_request(language, response_format, audio_file_path))
    loop.close()

    if client.phrase != '':
        print('\nRecognized phrase: ' + client.phrase)
    else:
        print('\nSorry, we were unable to recognize the utterance.')


if __name__ == '__main__':
    main()
