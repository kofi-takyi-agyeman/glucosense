from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from models.models import Report
from extensions import db
import os, uuid

reports_bp = Blueprint("reports", __name__)

ALLOWED = {"pdf", "png", "jpg", "jpeg", "doc", "docx", "txt"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


@reports_bp.route("/", methods=["GET"])
@jwt_required()
def list_reports():
    user_id = int(get_jwt_identity())
    reports = Report.query.filter_by(user_id=user_id).order_by(Report.created_at.desc()).all()
    return jsonify([r.to_dict() for r in reports]), 200


@reports_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_report():
    user_id = int(get_jwt_identity())
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
    file.save(save_path)

    report = Report(
        user_id=user_id,
        filename=unique_name,
        original_name=secure_filename(file.filename),
        file_size=os.path.getsize(save_path),
        file_type=ext,
    )
    db.session.add(report)
    db.session.commit()
    return jsonify(report.to_dict()), 201


@reports_bp.route("/download/<int:report_id>", methods=["GET"])
@jwt_required()
def download_report(report_id):
    user_id = int(get_jwt_identity())
    report = Report.query.filter_by(id=report_id, user_id=user_id).first()
    if not report:
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        report.filename,
        as_attachment=True,
        download_name=report.original_name,
    )


@reports_bp.route("/<int:report_id>", methods=["DELETE"])
@jwt_required()
def delete_report(report_id):
    user_id = int(get_jwt_identity())
    report = Report.query.filter_by(id=report_id, user_id=user_id).first()
    if not report:
        return jsonify({"error": "Not found"}), 404

    try:
        os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], report.filename))
    except FileNotFoundError:
        pass
    db.session.delete(report)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200