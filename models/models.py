from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

#  ---------MODELSS---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(10), nullable=False)

    full_name = db.Column(db.String(100), nullable=True)
    pincode = db.Column(db.String(10), nullable=True)
    address = db.Column(db.String(200), nullable=True)

    @property
    def has_parked(self):
        return Spots.query.filter_by(user_id=self.id, status="O").first() is not None


class Lots(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    address = db.Column(db.String(200))
    pincode = db.Column(db.String(10))
    price = db.Column(db.Float)
    max_spots = db.Column(db.Integer)


class Spots(db.Model):
    __tablename__ = "spots"
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey("lots.id"), nullable=False)
    lot = db.relationship("Lots", backref="spot_list", lazy=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    status = db.Column(db.String(1), default="E") 
    in_time = db.Column(db.DateTime, nullable=True)
    out_time = db.Column(db.DateTime, nullable=True)
    vehicle_no = db.Column(db.String(20), nullable=True)


class Bookings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer, db.ForeignKey('user.id'))
    spot_id=db.Column(db.Integer, db.ForeignKey('spots.id'))
    park_in = db.Column(db.DateTime)
    park_out = db.Column(db.DateTime)
    cost = db.Column(db.Float)

    

