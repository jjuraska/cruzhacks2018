from flask import Flask, request, render_template
import client as client
app = Flask(__name__)


# import RecognizerConfig as rc

@app.route('/')
def index():
    return render_template('home_page.html')


@app.route('/forward/', methods=["POST"])
def my_link():
    
	
	filePicker=request.files["filePicker"]
	key = request.form['key']
	language = request.form["languageOptions"]
	
	recognitionMode = request.form["recognitionMode"]
	
	formatOptions = request.form["formatOptions"]
	inputSource = request.form["inputSource"]
	phrase= client.start(key,language,formatOptions,filePicker)
	app.logger.info(phrase)
	return render_template('home_page.html', phrase=phrase)


# def send_start_values(key,language,recognitionMode,formatOptions,inputSource):



if __name__ == '__main__':
    app.run(threaded=True)

