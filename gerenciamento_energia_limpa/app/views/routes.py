from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models.fonte_energia import FonteEnergia, FonteEnergiaRepository
from app.data_processors.data_importer import GrowattDataImporter
from app.controllers.dashboard_controller import DashboardController
import os
from werkzeug.utils import secure_filename

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Página inicial - Lista todas as fontes"""
    fontes = FonteEnergiaRepository.listar_todas()
    return render_template('index.html', fontes=fontes)

@main.route('/fonte/nova', methods=['GET', 'POST'])
def nova_fonte():
    """Cadastro de uma nova fonte de energia"""
    if request.method == 'POST':
        try:
            fonte = FonteEnergia(
                nome=request.form['nome'],
                localizacao=request.form['localizacao'],
                capacidade=request.form['capacidade'],
                marca=request.form['marca'],
                modelo=request.form['modelo'],
                data_instalacao=request.form['data_instalacao']
            )
            
            FonteEnergiaRepository.salvar(fonte)
            flash('Fonte de energia cadastrada com sucesso!', 'success')
            
            # Gerar dados simulados para desenvolvimento
            if request.form.get('gerar_dados_simulados') == 'on':
                GrowattDataImporter.gerar_dados_simulados(fonte.id)
                flash('Dados simulados gerados com sucesso!', 'success')
                
            return redirect(url_for('main.dashboard', fonte_id=fonte.id))
        except Exception as e:
            flash(f'Erro ao cadastrar fonte: {str(e)}', 'danger')
    
    return render_template('cadastro_fonte.html')

@main.route('/fonte/<int:fonte_id>')
def detalhe_fonte(fonte_id):
    """Exibe detalhes de uma fonte específica"""
    fonte = FonteEnergiaRepository.buscar_por_id(fonte_id)
    if not fonte:
        flash('Fonte não encontrada!', 'danger')
        return redirect(url_for('main.index'))
    
    return render_template('detalhe_fonte.html', fonte=fonte)

@main.route('/fonte/<int:fonte_id>/editar', methods=['GET', 'POST'])
def editar_fonte(fonte_id):
    """Edição de uma fonte existente"""
    fonte = FonteEnergiaRepository.buscar_por_id(fonte_id)
    if not fonte:
        flash('Fonte não encontrada!', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            fonte.nome = request.form['nome']
            fonte.localizacao = request.form['localizacao']
            fonte.capacidade = request.form['capacidade']
            fonte.marca = request.form['marca']
            fonte.modelo = request.form['modelo']
            fonte.data_instalacao = request.form['data_instalacao']
            
            FonteEnergiaRepository.salvar(fonte)
            flash('Fonte atualizada com sucesso!', 'success')
            return redirect(url_for('main.detalhe_fonte', fonte_id=fonte.id))
        except Exception as e:
            flash(f'Erro ao atualizar fonte: {str(e)}', 'danger')
    
    return render_template('editar_fonte.html', fonte=fonte)

@main.route('/fonte/<int:fonte_id>/importar', methods=['GET', 'POST'])
def importar_dados(fonte_id):
    """Importação de dados para uma fonte"""
    fonte = FonteEnergiaRepository.buscar_por_id(fonte_id)
    if not fonte:
        flash('Fonte não encontrada!', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        if 'arquivo_csv' in request.files:
            arquivo = request.files['arquivo_csv']
            if arquivo.filename:
                # Salvar arquivo temporariamente
                filename = secure_filename(arquivo.filename)
                filepath = os.path.join('data', 'temp', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                arquivo.save(filepath)
                
                # Importar dados
                resultado = GrowattDataImporter.importar_csv(filepath, fonte_id)
                
                # Remover arquivo temporário
                os.unlink(filepath)
                
                if resultado['sucesso']:
                    flash(f"Dados importados com sucesso! {resultado['registros']} registros processados.", 'success')
                else:
                    flash(f"Erro na importação: {resultado['mensagem']}", 'danger')
                
                return redirect(url_for('main.dashboard', fonte_id=fonte_id))
            else:
                flash('Nenhum arquivo selecionado!', 'warning')
        elif request.form.get('gerar_simulados') == 'on':
            # Gerar dados simulados
            dias = int(request.form.get('dias_simulados', 30))
            resultado = GrowattDataImporter.gerar_dados_simulados(fonte_id, dias)
            
            if resultado['sucesso']:
                flash(f"Dados simulados gerados com sucesso! {resultado['registros']} registros criados.", 'success')
            else:
                flash(f"Erro na geração de dados: {resultado['mensagem']}", 'danger')
            
            return redirect(url_for('main.dashboard', fonte_id=fonte_id))
    
    return render_template('importar_dados.html', fonte=fonte)

@main.route('/dashboard/<int:fonte_id>')
def dashboard(fonte_id):
    """Dashboard para visualização dos dados de geração"""
    fonte = FonteEnergiaRepository.buscar_por_id(fonte_id)
    if not fonte:
        flash('Fonte não encontrada!', 'danger')
        return redirect(url_for('main.index'))
    
    # Métricas gerais
    metricas = DashboardController.calcular_metricas_gerais(fonte_id)
    
    return render_template('dashboard.html', fonte=fonte, metricas=metricas)

@main.route('/api/fonte/<int:fonte_id>/producao-diaria')
def api_producao_diaria(fonte_id):
    """API para obter dados de produção diária"""
    dados = DashboardController.get_dados_producao_diaria(fonte_id)
    return jsonify(dados)

@main.route('/api/fonte/<int:fonte_id>/producao-horaria')
def api_producao_horaria(fonte_id):
    """API para obter dados de produção horária"""
    dia = request.args.get('dia')
    dados = DashboardController.get_dados_producao_horaria(fonte_id, dia)
    return jsonify(dados)

@main.route('/home')
def home():
    """Página inicial do sistema"""
    fontes = FonteEnergiaRepository.listar_todas()
    return render_template('home.html', fontes=fontes)