# Python Speech-to-Text Client (CruzHacks 2018)

### What it does:

We built a speech to text client library using the Websockets protocol in python. 

### How we built it:

Microsoft Cognitive Services provides the Bing Speech API. From the free trial subscription keys from the Cognitive Services subscription page, we obtained the API keythe API Key. We used Websockets - a client library in Python which works on the WebSocket protocol.
We used the following Python libraries sys, json, platform, asyncio, websockets and utils.
Our client library takes into input- in the form of audio file and microphone input, uses the 3 recognition modes: Interactive, Dictation and Conversation, and uses Microsoft Bing Speech API to convert the spoken speech to text.

### Challenges we faced:

Having never worked on Client-server library programming, it was time-consuming to read on the existing libaries already existing and implement the same in python.
There was almost no library in python for websockets client which actually sends headers in the send method after the handshake and we had to do some workaround it.

### Accomplishments that we're proud of:

Completing the project in our first hackathon. 

### What we learned:

Learning about asynchronous communication.

### What's next for Python Speech-to-Text Client:

The project was overall very exciting, and as an extension to our project, we would like to make the UI component that we started working on but turned out to be very time-consuming for real-time interaction.
