import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
from apscheduler.schedulers.background import BackgroundScheduler

from controllers.predict import predict_bp, schedule_predict
from controllers.weather import weather_bp, schedule_job

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)
Swagger(app)

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
