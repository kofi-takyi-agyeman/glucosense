from datetime import datetime
from extensions import db


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assessments        = db.relationship("Assessment",       backref="user", lazy=True, cascade="all, delete-orphan")
    kidney_assessments = db.relationship("KidneyAssessment", backref="user", lazy=True, cascade="all, delete-orphan")
    reports            = db.relationship("Report",           backref="user", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "age": self.age,
            "gender": self.gender,
            "phone": self.phone,
            "created_at": self.created_at.isoformat(),
        }


class Assessment(db.Model):
    __tablename__ = "assessments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    pregnancies = db.Column(db.Float)
    glucose = db.Column(db.Float)
    blood_pressure = db.Column(db.Float)
    skin_thickness = db.Column(db.Float)
    insulin = db.Column(db.Float)
    bmi = db.Column(db.Float)
    diabetes_pedigree = db.Column(db.Float)
    age_input = db.Column(db.Float)
    probability = db.Column(db.Float)
    risk_level = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "pregnancies": self.pregnancies,
            "glucose": self.glucose,
            "blood_pressure": self.blood_pressure,
            "skin_thickness": self.skin_thickness,
            "insulin": self.insulin,
            "bmi": self.bmi,
            "diabetes_pedigree": self.diabetes_pedigree,
            "age_input": self.age_input,
            "probability": self.probability,
            "risk_level": self.risk_level,
            "created_at": self.created_at.isoformat(),
        }


class KidneyAssessment(db.Model):
    __tablename__ = "kidney_assessments"
    id                     = db.Column(db.Integer, primary_key=True)
    user_id                = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    age_input              = db.Column(db.Float)
    blood_pressure         = db.Column(db.Float)
    blood_glucose_random   = db.Column(db.Float)
    blood_urea             = db.Column(db.Float)
    serum_creatinine       = db.Column(db.Float)
    sodium                 = db.Column(db.Float)
    potassium              = db.Column(db.Float)
    haemoglobin            = db.Column(db.Float)
    packed_cell_volume     = db.Column(db.Float)
    white_blood_cell_count = db.Column(db.Float)
    red_blood_cell_count   = db.Column(db.Float)
    hypertension           = db.Column(db.Integer)   # 0 / 1
    diabetes_mellitus      = db.Column(db.Integer)   # 0 / 1
    pedal_edema            = db.Column(db.Integer)   # 0 / 1
    anemia                 = db.Column(db.Integer)   # 0 / 1
    probability            = db.Column(db.Float)
    risk_level             = db.Column(db.String(20))
    created_at             = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":                     self.id,
            "age_input":              self.age_input,
            "blood_pressure":         self.blood_pressure,
            "blood_glucose_random":   self.blood_glucose_random,
            "blood_urea":             self.blood_urea,
            "serum_creatinine":       self.serum_creatinine,
            "sodium":                 self.sodium,
            "potassium":              self.potassium,
            "haemoglobin":            self.haemoglobin,
            "packed_cell_volume":     self.packed_cell_volume,
            "white_blood_cell_count": self.white_blood_cell_count,
            "red_blood_cell_count":   self.red_blood_cell_count,
            "hypertension":           self.hypertension,
            "diabetes_mellitus":      self.diabetes_mellitus,
            "pedal_edema":            self.pedal_edema,
            "anemia":                 self.anemia,
            "probability":            self.probability,
            "risk_level":             self.risk_level,
            "created_at":             self.created_at.isoformat(),
        }


class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    filename = db.Column(db.String(256), nullable=False)
    original_name = db.Column(db.String(256), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "original_name": self.original_name,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "created_at": self.created_at.isoformat(),
        }