# app.py (VERSÃO FINAL E SIMPLIFICADA)
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timezone
from sqlalchemy import func
from dateutil import parser
import pytz

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
CORS(app) 
app.json.ensure_ascii = False

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///' + os.path.join(basedir, 'instance', 'corridas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Corrida(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    plataforma = db.Column(db.String(50), nullable=True) 
    origem = db.Column(db.String(200), nullable=True)
    destino = db.Column(db.String(200), nullable=True)
    data_corrida = db.Column(db.DateTime, nullable=False)
    forma_pagamento = db.Column(db.String(100), nullable=True)

@app.route('/api/corridas', methods=['POST'])
def adicionar_corrida():
    dados = request.get_json()
    if not dados or 'valor' not in dados or 'data_corrida' not in dados:
        return jsonify({'erro': 'Dados insuficientes (valor, data_corrida)'}), 400
    try:
        data_corrida_obj = parser.parse(dados['data_corrida'])
        valor_corrida = float(dados['valor'])
        plataforma = dados.get('plataforma')
    except (ValueError, TypeError):
        return jsonify({'erro': 'Valor ou formato de data inválido.'}), 400
    corrida_existente = Corrida.query.filter_by(plataforma=plataforma, valor=valor_corrida, data_corrida=data_corrida_obj).first()
    if corrida_existente:
        return jsonify({'mensagem': 'Corrida duplicada, ignorada com sucesso.'}), 200
    nova_corrida = Corrida(valor=valor_corrida, plataforma=plataforma, origem=dados.get('origem'), destino=dados.get('destino'), data_corrida=data_corrida_obj, forma_pagamento=dados.get('forma_pagamento'))
    db.session.add(nova_corrida)
    db.session.commit()
    return jsonify({'mensagem': 'Corrida adicionada com sucesso!', 'id': nova_corrida.id}), 201

@app.route('/api/corridas/<int:corrida_id>', methods=['PUT'])
def editar_corrida(corrida_id):
    corrida = Corrida.query.get_or_404(corrida_id)
    dados = request.get_json()
    try:
        if 'plataforma' in dados: corrida.plataforma = dados['plataforma']
        if 'valor' in dados: corrida.valor = float(dados['valor'])
        if 'origem' in dados: corrida.origem = dados['origem']
        if 'destino' in dados: corrida.destino = dados['destino']
        if 'forma_pagamento' in dados: corrida.forma_pagamento = dados['forma_pagamento']
        if 'data_corrida' in dados: corrida.data_corrida = parser.parse(dados['data_corrida'])
        db.session.commit()
        return jsonify({'mensagem': 'Corrida atualizada com sucesso!'})
    except (ValueError, TypeError):
        return jsonify({'erro': 'Formato de dados inválido.'}), 400

@app.route('/api/corridas/<int:corrida_id>', methods=['DELETE'])
def deletar_corrida(corrida_id):
    corrida = Corrida.query.get_or_404(corrida_id)
    db.session.delete(corrida)
    db.session.commit()
    return jsonify({'mensagem': 'Corrida deletada com sucesso!'})

@app.route('/api/corridas', methods=['GET'])
def listar_corridas():
    corridas_recentes = Corrida.query.order_by(Corrida.data_corrida.desc()).limit(50).all()
    lista_de_corridas = []
    fuso_horario_local = pytz.timezone("America/Sao_Paulo")
    for corrida in corridas_recentes:
        data_utc = corrida.data_corrida.replace(tzinfo=pytz.utc)
        data_local = data_utc.astimezone(fuso_horario_local)
        lista_de_corridas.append({'id': corrida.id, 'valor': corrida.valor, 'plataforma': corrida.plataforma, 'origem': corrida.origem, 'destino': corrida.destino, 'data_corrida': data_local.strftime('%d/%m/%Y %H:%M'), 'forma_pagamento': corrida.forma_pagamento})
    return jsonify(lista_de_corridas)

@app.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    total_gasto = db.session.query(func.sum(Corrida.valor)).scalar() or 0.0
    total_de_corridas = Corrida.query.count()
    media_por_corrida = total_gasto / total_de_corridas if total_de_corridas > 0 else 0.0
    inicio_do_mes = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total_este_mes = db.session.query(func.sum(Corrida.valor)).filter(Corrida.data_corrida >= inicio_do_mes).scalar() or 0.0
    stats = {'total_gasto': round(total_gasto, 2), 'total_de_corridas': total_de_corridas, 'media_por_corrida': round(media_por_corrida, 2), 'total_este_mes': round(total_este_mes, 2)}
    return jsonify(stats)

if __name__ == '__main__':
    app.run(debug=True)