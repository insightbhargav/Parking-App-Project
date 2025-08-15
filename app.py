from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from models.models import db, User
from controllers.routes import bp
import os

app = Flask(__name__)

db_folder = os.path.join(os.path.dirname(__file__), "database")
os.makedirs(db_folder, exist_ok=True)
db_path = os.path.join(db_folder, "parking.db")


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.jinja_env.add_extension('jinja2.ext.do')

app.secret_key = "123"

db.init_app(app)
app.register_blueprint(bp)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "main.combined_login"
 


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", password="admin123", role="admin")
            db.session.add(admin)
        db.session.commit()
    app.run(debug=True)

