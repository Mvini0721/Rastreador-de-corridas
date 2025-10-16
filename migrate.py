from flask_migrate import upgrade
from app import app, db

# Garante que o script rode no contexto da aplicação
with app.app_context():
    print("INFO: Aplicando migrações do banco de dados...")
    # O comando 'upgrade' aplica as mudanças ao banco de dados
    upgrade()
    print("INFO: Migrações aplicadas com sucesso.")