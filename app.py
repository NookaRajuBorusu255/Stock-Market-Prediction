import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager

from config import Config
from database import db
from database.models import User

# Import Blueprints
from controllers.auth_controller import auth_bp
from controllers.dashboard_controller import dashboard_bp
from controllers.ml_controller import ml_bp
from controllers.chatbot_controller import chatbot_bp
from controllers.report_controller import report_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure necessary folders exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['MODELS_FOLDER'], exist_ok=True)
    
    # Ensure database folder exists
    db_path = app.config['SQLALCHEMY_DATABASE_URI']
    if db_path.startswith('sqlite:///'):
        db_filepath = db_path.replace('sqlite:///', '')
        db_dir = os.path.dirname(db_filepath)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        # Using SQLAlchemy's session.get for primary keys is standard and efficient
        return db.session.get(User, int(user_id))

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(ml_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(report_bp)

    # Global Redirect if user directly navigates to index on launch
    @app.route('/index')
    def redirect_index():
        return redirect(url_for('dashboard.index'))

    # Create tables inside application context
    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    import socket
    import os
    
    # Get the local network IP address
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # We don't actually send data; this is just to get the local network interface IP
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    # Only print links once, ignoring the Werkzeug auto-reloader startup message
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print("\n" + "=" * 60)
        print("                  STOCKS APP RUNNING")
        print("=" * 60)
        print(f" * Local Link:             http://127.0.0.1:5000")
        print(f" * Host Link (Network):    http://{local_ip}:5000")
        print("=" * 60 + "\n")

    # Run Flask server on 0.0.0.0 to listen on all interfaces
    app.run(host='0.0.0.0', port=5000, debug=True)
