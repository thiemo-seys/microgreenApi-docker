import base64
import numpy as np
import io
import os
import datetime
import requests as rq

from azureManager import AzureManager

from flask import Flask
from flask import request, redirect,abort
from flask import jsonify
from flask import send_from_directory

from keras.models import load_model
from keras_preprocessing.image import img_to_array
from PIL import Image

from flask_swagger_ui import get_swaggerui_blueprint

az = AzureManager()
app = Flask(__name__)

### swagger specific ###
SWAGGER_URL = '/documentation'
API_URL = '/static/swagger.yaml'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Microgreen API"
    }
)
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)
### end swagger specific ###



MODEL_DIRECTORY = "static/models"
IMAGE_DIRECTORY = "static/images/"
global image_count
image_count = 0
global retraining_threshold
retraining_threshold = 100
global training_server_ip
training_server_ip = 'http://127.0.0.1:1234'
list_classes = az.species

def generate_static_folders():
    if not os.path.exists(MODEL_DIRECTORY):
        print("making model folder")
        os.makedirs(MODEL_DIRECTORY)
        #TODO: maybe request latest model?

    if not os.path.exists(IMAGE_DIRECTORY):
        os.makedirs(IMAGE_DIRECTORY)

    for microgreen in list_classes:
        if not os.path.exists(IMAGE_DIRECTORY + microgreen):
            print('making '+ microgreen)
            os.makedirs(IMAGE_DIRECTORY + microgreen)

#TODO: finish this function to fully work, gets latest model and maybe class list fron azure and use it.
#TODO: call this function a bit after retraining to always use the latest model.
def get_model():
    print('downloading latest model')
    az.get_latest_model()
    global model_transferlearning
    print('loading model')
    model_path = 'static/models/'
    model_name = ''
    for file in os.listdir(model_path):
        model_name = file

    model_transferlearning = load_model(model_path+model_name)
    print('DONE: model loaded')

def preprocess_image(image, target_size):
    if image.mode != 'RGB':
        image.convert("RGB")
    image = image.resize(target_size)
    image = img_to_array(image)
    image = np.expand_dims(image, axis=0)
    return image

generate_static_folders()
get_model()

@app.route('/')
def hello_world():
    return 'This is a microgreens classifying API, if you see this message then the server is currently active!'

@app.route('/retrainingTreshold', methods=["GET"])
def get_retrainingTreshold():
        return jsonify(retraining_threshold)

@app.route('/setretrainingTreshold', methods=["POST"])
def set_retrainingTreshold():
    message = request.get_json(force=True)
    threshold = message['threshold']
    global  retraining_threshold
    retraining_threshold = threshold
    return jsonify("changed retraining threshold")


#receives a picture and return the prediction matrix
@app.route('/predict', methods=['POST'])
def predict():
    message = request.get_json(force=True)
    encoded = message['image']
    try:
        decoded = base64.b64decode(encoded)
        image = Image.open(io.BytesIO(decoded))
        processed_image = preprocess_image(image, target_size=(256,256))

        prediction = model_transferlearning.predict(processed_image).tolist()

        return jsonify(prediction[0])
    except OSError as e:
        print(e)
        return jsonify(e)

#lists all the saved models
@app.route("/model")
def list_files():
    """Endpoint to list files on the server."""
    files = []
    for filename in os.listdir(MODEL_DIRECTORY):
        path = os.path.join(MODEL_DIRECTORY, filename)
        if os.path.isfile(path):
            files.append(filename)
    return jsonify(files)

@app.route("/download")
def get_model():
    """Download a file."""
    file = request.args.get('filename')
    return send_from_directory(MODEL_DIRECTORY, file, as_attachment=True)

#lists all the saved models
@app.route("/species")
def list_species():
    """Endpoint to list files on the server."""
    return jsonify(az.list_all_plant_containers())

#TODO: upload pictures and store to cloud.
#receives a picture and return the prediction matrix
@app.route('/save', methods=['POST'])
def save():
    message = request.get_json(force=True)
    encoded = message['image']
    species = message['species']
    try:
        decoded = base64.b64decode(encoded)
        image = Image.open(io.BytesIO(decoded))
        image_folder = IMAGE_DIRECTORY + species + "/"
        if not os.path.exists(image_folder):
            os.makedirs(image_folder)
        if species not in list_classes:
            az.create_container(species)

        filename = str(datetime.datetime.now())
        image_path = image_folder + filename
        image.save(image_path, 'JPEG')
        az.upload_single_picture(filename=filename, species=species)
        global image_count
        image_count = image_count + 1
        if image_count == retraining_threshold:
            rq.get(training_server_ip + '/train')
            get_model()
            az.species = az.list_all_plant_containers()
        return jsonify("saved img")

    except OSError as e:
        print(e)
        return jsonify(e)


@app.route('/trainserverIP', methods=["GET"])
def get_trainingserverIP():
        return jsonify(training_server_ip)

@app.route('/settrainserverIP', methods=["POST"])
def set_trainingserverIP():
    message = request.get_json(force=True)
    ip = message['ip']
    global  training_server_ip
    training_server_ip = ip
    return jsonify("changed retraining threshold")


if __name__ == '__main__':
    app.run()
