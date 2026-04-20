from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.models import Assessment
from extensions import db

records_bp = Blueprint("records", __name__)


@records_bp.route("/", methods=["GET"])
@jwt_required()
def get_records():
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    paginated = (Assessment.query
                 .filter_by(user_id=user_id)
                 .order_by(Assessment.created_at.desc())
                 .paginate(page=page, per_page=per_page, error_out=False))

    return jsonify({
        "records": [r.to_dict() for r in paginated.items],
        "total": paginated.total,
        "pages": paginated.pages,
        "current_page": page,
    }), 200


@records_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_stats():
    user_id = int(get_jwt_identity())
    all_assessments = Assessment.query.filter_by(user_id=user_id).all()
    total = len(all_assessments)
    if total == 0:
        return jsonify({"total": 0, "avg_probability": 0, "latest_risk": None, "high_risk_count": 0}), 200

    avg_prob = sum(a.probability for a in all_assessments) / total
    latest = max(all_assessments, key=lambda x: x.created_at)
    high_risk = sum(1 for a in all_assessments if a.risk_level == "High")

    return jsonify({
        "total": total,
        "avg_probability": round(avg_prob * 100, 1),
        "latest_risk": latest.risk_level,
        "latest_probability": round(latest.probability * 100, 1),
        "high_risk_count": high_risk,
    }), 200


@records_bp.route("/<int:record_id>", methods=["DELETE"])
@jwt_required()
def delete_record(record_id):
    user_id = int(get_jwt_identity())
    record = Assessment.query.filter_by(id=record_id, user_id=user_id).first()
    if not record:
        return jsonify({"error": "Record not found"}), 404
    db.session.delete(record)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200