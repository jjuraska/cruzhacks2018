# Python Speech-to-Text Client

Python client library for the cloud-based Speech API to transcribe a spoken utterance to text. The asynchronous communication with the service uses the WebSocket protocol enabling real-time speech recognition.

## How to Use It

```
python3 client.py [your_api_key] [lang_code] [response_type] [recognition_mode] [path_to_audio_file]
```

- [your_api_key] must be obtained from [Microsoft Azure](https://azure.microsoft.com/)
- [lang_code] is the code of one of the [supported languages](https://docs.microsoft.com/en-us/azure/cognitive-services/speech/api-reference-rest/supportedlanguages) 
- [response_type] simple/detailed
- [recognition_mode] interactive/conversation/dictation
- [path_to_audio_file] path to a WAV (mono, 16-bit, 16 kHz) audio file _(this is an optional argument, omitting of which indicates that the input should be provided from the microphone instead of a file)_

## The Story Behind the Project

The winning project in the "Microsoft Invoke Cortana's Best Speech Client Implementation" category of the CruzHacks hackathon that took place from Jan 19 to Jan 21 2018 at the University of California, Santa Cruz.

#### Inspiration

Our project was inspired by the impressive selection of Microsoft's tools for natural language processing (NLP), but a rather limited support of their APIs for development in Python - arguably the most popular language in academia these days, as well as in deep learning and NLP projects in the industry.

#### What it does

We built a Python client library for the cloud-based Microsoft Speech API to transcribe a spoken utterance to text. The asynchronous communication with the service uses the WebSocket protocol enabling real-time speech recognition.

#### How we built it

[Microsoft Cognitive Services](https://azure.microsoft.com/en-us/services/cognitive-services/directory/speech/) offers a wide selection of tools for NLP running on the Azure cloud platform. The client we implemented communicates with their [Bing Speech API](https://azure.microsoft.com/en-us/services/cognitive-services/speech/) capable of both automatic speech recognition and speech synthesis from text. To gain access to the power of the Speech API, we subscribed to the service to get a 30-day free trial (limited to 5000 transactions @ 20 per minute), and were issued API keys for authentication in the communication of our client with the server.

As for the implementation of the client itself, we chose to work with the [websockets](https://websockets.readthedocs.io/) library containing tools to build a client or a server using the WebSocket protocol in Python. Aside from that, we made use of the following libraries and packages: asyncio, websockets, pyaudio, wave and flask. Our client library supports input directly from a microphone, as well as from a pre-recorded audio file. It allows the speech recognition to be performed in various languages and in 3 different recognition modes offered by the Speech API: interactive, conversation and dictation. All these parameters can be specified before running the client.

#### Challenges we ran into

Having never worked on client-server communication, we had to learn how the modern WebSocket protocol works, and study Microsoft's [documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/speech/home) of how their Speech API uses this protocol (their documentation is well-written and comprehensive, so don't be afraid of jumping on the Microsoft waggon). We were looking for a WebSocket package in Python that would support the passing of a header in the messages sent to the server after the handshake, only to realize several hours later - on the verge of switching to using HTTP instead of WebSocket - that WebSocket handles the header passing differently. Another challenge was to get the asynchronicity right, and make the messages between the client and the server to be exchanged concurrently. Finally, we made a simple web UI for the client, however, having very limited experience with web development, we didn't manage to integrate it with the client as we had intended, and thus the client remained usable via the command line only.

#### Accomplishments that we're proud of

Successfully completing our first hackathon project within the given timeframe, and in a team of only two people. Being the first to implement a client for the Speech API in Python, which will hopefully serve the users of this API when they are developing a Python project utilizing Microsoft Cognitive Services.

#### What we learned

We learned how to implement asynchronous client-server communication in Python, and how to take advantage of the WebSocket protocol for real-time communication when sequential data (such as audio) needs to be processed by a service. We also got our hands on some of Microsoft's newest NLP tools, which opened our eyes to even more cool products and APIs out there that we could make use of in our future NLP projects. Not to mention that the hackathon is a great training for time management and work under time pressure.

#### What's next for Python Speech-to-Text Client

In order to make the client library complete, we intend to integrate the microphone input in such a way that the client would be sending it as a stream to the Speech API for transcription and receiving partial text hypotheses about the speech in real time. Moreover, we would like to finish and improve the UI component as well so that it eventually supports the real-time transcription of the microphone input too.
