from flask import Flask, request, render_template,redirect,session
import client as client
import asyncio

app = Flask(__name__)
app.secret_key = "super secret key"

# import RecognizerConfig as rc

@app.route('/')
def index():
    return render_template('home_page.html')



@app.route('/forward/', methods=["POST"])
def my_link():
    
    
    #filePicker=request.files["filePicker"]
    audio_file_path = 'data/whatstheweatherlike.wav'
    key = request.form['key']
    language = request.form["languageOptions"]
    
    recognitionMode = request.form["recognitionMode"]
    
    formatOptions = request.form["formatOptions"]
    inputSource = request.form["inputSource"]
    app.logger.info(key)
    #result=hello()
    phrase= yield client.start(key,language,formatOptions,recognitionMode,audio_file_path)
    #store=session.get('store')
    if phrase=='':
        app.logger.info("blank")
    else:
        app.logger.info(next(phrase))
    return render_template('home_page.html')

def hello():
    #session['store'] = "hi"
    app.logger.info("nehal")
    return "hello"
# def send_start_values(key,language,recognitionMode,formatOptions,inputSource):



if __name__ == '__main__':
    app.run(debug=True)

