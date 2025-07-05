import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
from apscheduler.schedulers.background import BackgroundScheduler

from controllers.predict import predict_bp, schedule_predict
from controllers.weather import weather_bp, schedule_job

# Load environment variables
load_dotenv(override=True)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec_1",
            "route": "/apispec_1.json",
            "rule_filter": lambda rule: True,      # all endpoints
            "model_filter": lambda tag: True,      # all models
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/"
}
swagger_template = {
    "info": {
        "title": "Floody API",
        "description": "API untuk prediksi banjir dan upload data cuaca ke Firebase",
        "version": "1.0.0",
        "contact": {
            "name": "Tim Floody",
            "email": "support@floody.app"
        }
    }
}

Swagger(app, config=swagger_config, template=swagger_template)

# Register API blueprints
app.register_blueprint(predict_bp, url_prefix='/api')
app.register_blueprint(weather_bp, url_prefix='/api')

if __name__ == '__main__':
    # Setup and start scheduler
    scheduler = BackgroundScheduler()
    schedule_predict(scheduler)
    schedule_job(scheduler)
    scheduler.start()

    # Run Flask server
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
