import sys
import json
import platform
import asyncio
import websockets

import utils


class SpeechClient:
    # ---- CONSTRUCTOR ----

    def __init__(self, api_key):
        self.uuid = utils.generate_id()
        self.connection_id = utils.generate_id()
        self.request_id = utils.generate_id()
        self.auth_token = utils.obtain_auth_token(api_key)

        self.endpoint_interactive = r'wss://speech.platform.bing.com/speech/recognition/interactive/cognitiveservices/v1'
        self.endpoint_conversation = r'wss://speech.platform.bing.com/speech/recognition/conversation/cognitiveservices/v1'
        self.endpoint_dictation = r'wss://speech.platform.bing.com/speech/recognition/dictation/cognitiveservices/v1'

        self.language = 'en-US'
        self.response_format = 'simple'
        self.recognition_mode = 'interactive'

        self.chunk_size = 8192

        self.num_turns = 0
        self.is_ongoing_turn = False
        self.cur_hypothesis = ''
        self.phrase = ''
        self.received_messages = []
        self.metrics = []


    # ---- PUBLIC METHODS ----

    async def speech_to_text(self, language, response_format, recognition_mode, audio_file_path):
        self.language = language
        self.response_format = response_format
        self.recognition_mode = recognition_mode

        # determine the endpoint based on the selected recognition mode
        endpoint = self.__get_cur_endpoint()
        if endpoint is None:
            print('Error: invalid recognition mode.')
            return

        # assemble the URL and the headers for the connection request
        url = endpoint + '?language={0}&format={1}'.format(self.language, self.response_format)
        headers = {
            'Authorization': 'Bearer ' + self.auth_token,
            'X-ConnectionId': self.connection_id
        }

        # record the Connection metric telemetry data
        self.metrics.append({
            'Name': 'Connection',
            'Id': self.connection_id,
            'Start': utils.generate_timestamp()
        })

        # request a WebSocket connection to the Bing Speech API
        async with websockets.client.connect(url, extra_headers=headers) as ws:
            # TODO: catch connection errors, and add Connection failure telemetry for error cases

            # record the Connection metric telemetry data
            self.metrics[-1]['End'] = utils.generate_timestamp()

            # try:
            #     ws.handshake(url, origin='https://speech.platform.bing.com')
            # except websockets.exceptions.InvalidHandshake as e:
            #     print('Handshake error: {0}'.format(e))

            # send the speech.config message
            await self.send_speech_config_msg(ws)

            # perform the sending and receiving via the WebSocket concurrently
            sending_task = asyncio.ensure_future(self.send_audio_msg(ws, audio_file_path))
            receiving_task = asyncio.ensure_future(self.process_response(ws))
            # wait for both the tasks to complete
            await asyncio.wait(
                [sending_task, receiving_task],
                return_when=asyncio.ALL_COMPLETED,
            )


    async def send_speech_config_msg(self, ws):
        # assemble the payload for the speech.config message
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

        # assemble the header for the speech.config message
        msg = 'Path: speech.config\r\n'
        msg += 'Content-Type: application/json; charset=utf-8\r\n'
        msg += 'X-Timestamp: ' + utils.generate_timestamp() + '\r\n'
        # append the body of the message
        msg += '\r\n' + json.dumps(payload, indent=2)

        # DEBUG PRINT
        # print('>>', msg)

        await ws.send(msg)


    async def send_audio_msg(self, ws, audio_file_path):
        # open the binary audio file
        with open(audio_file_path, 'rb') as f_audio:
            num_chunks = 0
            while True:
                # read the audio file in small consecutive chunks
                audio_chunk = f_audio.read(self.chunk_size)
                if not audio_chunk:
                    break
                num_chunks += 1

                # assemble the header for the binary audio message
                msg = b'Path: audio\r\n'
                msg += b'Content-Type: audio/x-wav\r\n'
                msg += b'X-RequestId: ' + bytearray(self.request_id, 'ascii') + b'\r\n'
                msg += b'X-Timestamp: ' + bytearray(utils.generate_timestamp(), 'ascii') + b'\r\n'
                # prepend the length of the header in 2-byte big-endian format
                msg = len(msg).to_bytes(2, byteorder='big') + msg
                # append the body of the message
                msg += b'\r\n' + audio_chunk

                # DEBUG PRINT
                print('>>', msg)
                sys.stdout.flush()

                try:
                    await ws.send(msg)
                    # DEBUG CONCURRENCY
                    # await asyncio.sleep(0.1)
                except websockets.exceptions.ConnectionClosed as e:
                    print('Connection closed: {0}'.format(e))
                    return


    async def send_telemetry_data(self, ws, is_first_turn=False):
        # assemble the payload for the telemetry message
        payload = {
            'ReceivedMessages': self.received_messages
        }
        if is_first_turn:
            payload['Metrics'] = self.metrics

        # assemble the header for the speech.config message
        msg = 'Path: telemetry\r\n'
        msg += 'Content-Type: application/json; charset=utf-8\r\n'
        msg += 'X-RequestId: ' + self.request_id + '\r\n'
        msg += 'X-Timestamp: ' + utils.generate_timestamp() + '\r\n'
        # append the body of the message
        msg += '\r\n' + json.dumps(payload, indent=2)

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
                # DEBUG PRINT
                print('<<', utils.generate_timestamp() + '\r\n' + response)
                sys.stdout.flush()
            except websockets.exceptions.ConnectionClosed as e:
                print('Connection closed: {0}'.format(e))
                return

            # identify the type of response
            response_path = utils.parse_header_value(response, 'Path')
            if response_path is None:
                print('Error: invalid response header.')
                ws.close()
                return

            # record the telemetry data for received messages
            self.__record_telemetry(response_path)

            if response_path == 'turn.start':
                self.is_ongoing_turn = True
                self.num_turns += 1
            elif response_path == 'speech.startDetected':
                pass
            elif response_path == 'speech.hypothesis':
                response_dict = utils.parse_body_json(response)
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
                response_dict = utils.parse_body_json(response)
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

        await self.send_telemetry_data(ws, is_first_turn=(self.num_turns == 1))


    # ---- PRIVATE METHODS ----

    def __get_cur_endpoint(self):
        if self.recognition_mode == 'interactive':
            return self.endpoint_interactive
        elif self.recognition_mode == 'conversation':
            return self.endpoint_conversation
        elif self.recognition_mode == 'dictation':
            return self.endpoint_dictation
        else:
            return None


    def __record_telemetry(self, response_path):
        # if a single message of a certain type, store the value directly
        if response_path not in [next(iter(msg.keys())) for msg in self.received_messages]:
            self.received_messages.append({
                response_path: utils.generate_timestamp()
            })
        # if multiple messages of a certain type, store the values in a list
        else:
            for i, msg in enumerate(self.received_messages):
                if next(iter(msg.keys())) == response_path:
                    if not isinstance(msg[response_path], list):
                        self.received_messages[i][response_path] = [msg[response_path]]
                    self.received_messages[i][response_path].append(utils.generate_timestamp())
                    break


# ---- MAIN ----

def main():
    if len(sys.argv) != 2:
        print('Please, provide your key to access the Bing Speech API.')
        exit()

    language = 'en-US'
    # response_format = 'simple'
    response_format = 'detailed'
    recognition_mode = 'interactive'
    # recognition_mode = 'conversation'
    # recognition_mode = 'dictation'
    audio_file_path = 'data/whatstheweatherlike.wav'
    # audio_file_path = 'data/test.wav'


    client = SpeechClient(sys.argv[1])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.speech_to_text(language, response_format, recognition_mode, audio_file_path))
    loop.close()

    # print the result
    if client.phrase != '':
        print('\nRecognized phrase: ' + client.phrase)
    else:
        print('\nSorry, we were unable to recognize the utterance.')


if __name__ == '__main__':
    main()
