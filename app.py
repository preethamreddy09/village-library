import os
from flask import Flask
from config import Config
from models import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Connect SQLAlchemy to this app
    db.init_app(app)

    # Make sure the folders we need actually exist
    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Register routes (blueprints) — we'll fill these files in over the next steps
    from routes.catalog import catalog_bp
    from routes.circulation import circulation_bp
    from routes.patterns import patterns_bp
    from routes.auth import auth_bp
    from routes.history import history_bp
    from routes.about import about_bp
    app.register_blueprint(catalog_bp)
    app.register_blueprint(circulation_bp)
    app.register_blueprint(patterns_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(about_bp)

    # Create tables on first run if they don't exist yet
    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=False)