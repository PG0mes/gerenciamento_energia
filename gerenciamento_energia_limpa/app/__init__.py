from flask import Flask
from config.config import config

def create_app(config_name='default'):
    """Cria e configura a aplicação Flask"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Registro dos blueprints
    from app.views.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app