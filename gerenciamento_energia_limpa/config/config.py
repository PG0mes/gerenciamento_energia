import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configurações base do aplicativo"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'chave-secreta-padrao')
    DATA_FOLDER = 'data'
    
    # Configurações para eventual integração com API Growatt
    GROWATT_API_URL = os.environ.get('GROWATT_API_URL', '')
    GROWATT_USERNAME = os.environ.get('GROWATT_USERNAME', '')
    GROWATT_PASSWORD = os.environ.get('GROWATT_PASSWORD', '')

class DevelopmentConfig(Config):
    """Configurações de desenvolvimento"""
    DEBUG = True
    
class ProductionConfig(Config):
    """Configurações de produção"""
    DEBUG = False

# Configuração a ser usada
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}