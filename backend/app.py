from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from extensions import db, jwt
import os

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "glucosense-secret-2024")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "glucosense-jwt-secret-2024")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///glucosense.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)
    jwt.init_app(app)

    with app.app_context():
        from models.models import User, Assessment, KidneyAssessment, Report  # noqa
        from routes.auth import auth_bp
        from routes.predict import predict_bp
        from routes.records import records_bp
        from routes.reports import reports_bp
        from routes.kidney import kidney_bp

        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(predict_bp, url_prefix="/api/predict")
        app.register_blueprint(records_bp, url_prefix="/api/records")
        app.register_blueprint(reports_bp, url_prefix="/api/reports")
        app.register_blueprint(kidney_bp, url_prefix="/api/kidney")

        db.create_all()
        print("[GlucoSense] ✓ Database ready")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)