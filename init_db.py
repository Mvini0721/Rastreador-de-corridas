from app import app, db

# Cria o contexto da aplicação para que o db saiba a qual app pertence
with app.app_context():
    print("INFO: Criando todas as tabelas do banco de dados...")
    # O comando mais fundamental: cria as tabelas se elas não existirem
    db.create_all()
    print("INFO: Tabelas criadas com sucesso (ou já existiam).")