from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import pandas as pd
from docx import Document
from datetime import datetime, timedelta
import os
import json
from werkzeug.utils import secure_filename
import tempfile
import zipfile

class AutomatizacaoEscritorio:
    def __init__(self, arquivo_excel):
        """
        Inicializa a classe com o arquivo Excel base
        """
        self.arquivo_excel = arquivo_excel
        self.df = self.carregar_dados()
    
    def carregar_dados(self):
        """
        Carrega os dados do arquivo Excel
        """
        try:
            if os.path.exists(self.arquivo_excel):
                return pd.read_excel(self.arquivo_excel)
            else:
                return self.criar_estrutura_inicial()
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
            return self.criar_estrutura_inicial()
    
    def criar_estrutura_inicial(self):
        """
        Cria uma planilha inicial se não existir
        """
        # Garantir que o diretório existe
        os.makedirs(os.path.dirname(self.arquivo_excel), exist_ok=True)
        
        dados_iniciais = {
            'Numero_Processo': ['001/2025', '002/2025'],
            'Cliente': ['Cliente Exemplo 1', 'Cliente Exemplo 2'],
            'Advogado_Responsavel': ['Dr. Silva', 'Dra. Santos'],
            'Tipo_Acao': ['Cível', 'Trabalhista'],
            'Data_Cadastro': [datetime.now().strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d')],
            'Data_Intimacao': [datetime.now().strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d')],
            'Dias_Prazo': [15, 10],
            'Status': ['Ativo', 'Ativo']
        }
        
        df = pd.DataFrame(dados_iniciais)
        try:
            df.to_excel(self.arquivo_excel, index=False)
            print(f"Arquivo {self.arquivo_excel} criado com dados iniciais.")
        except Exception as e:
            print(f"Erro ao criar arquivo Excel: {e}")
        return df
    
    def adicionar_processo(self, dados):
        """
        Adiciona um novo processo à planilha
        """
        # Verificar se processo já existe
        if dados['numero'] in self.df['Numero_Processo'].values:
            return False, f"Processo {dados['numero']} já existe na base de dados."
        
        novo_processo = {
            'Numero_Processo': dados['numero'],
            'Cliente': dados['cliente'],
            'Advogado_Responsavel': dados['advogado'],
            'Tipo_Acao': dados['tipo'],
            'Data_Cadastro': datetime.now().strftime('%Y-%m-%d'),
            'Data_Intimacao': dados.get('dataIntimacao', datetime.now().strftime('%Y-%m-%d')),
            'Dias_Prazo': dados.get('diasPrazo', 15),
            'Status': 'Ativo'
        }
        
        novo_df = pd.DataFrame([novo_processo])
        self.df = pd.concat([self.df, novo_df], ignore_index=True)
        self.salvar_dados()
        return True, f"Processo {dados['numero']} adicionado com sucesso."
    
    def atualizar_processo(self, numero, dados):
        """
        Atualiza dados de um processo específico
        """
        if numero not in self.df['Numero_Processo'].values:
            return False, f"Processo {numero} não encontrado."
        
        # Mapeamento dos campos
        campos_mapeados = {
            'cliente': 'Cliente',
            'advogado': 'Advogado_Responsavel',
            'tipo': 'Tipo_Acao',
            'dataIntimacao': 'Data_Intimacao',
            'diasPrazo': 'Dias_Prazo',
            'status': 'Status'
        }
        
        for campo_front, campo_db in campos_mapeados.items():
            if campo_front in dados:
                self.df.loc[self.df['Numero_Processo'] == numero, campo_db] = dados[campo_front]
        
        self.salvar_dados()
        return True, f"Processo {numero} atualizado com sucesso."
    
    def remover_processo(self, numero):
        """
        Remove um processo da base de dados
        """
        if numero not in self.df['Numero_Processo'].values:
            return False, f"Processo {numero} não encontrado."
        
        self.df = self.df[self.df['Numero_Processo'] != numero]
        self.salvar_dados()
        return True, f"Processo {numero} removido com sucesso."
    
    def salvar_dados(self):
        """
        Salva os dados no arquivo Excel
        """
        try:
            self.df.to_excel(self.arquivo_excel, index=False)
            return True
        except Exception as e:
            print(f"Erro ao salvar dados: {e}")
            return False
    
    def obter_todos_processos(self):
        """
        Retorna todos os processos em formato JSON
        """
        if self.df.empty:
            return []
        
        processos = []
        for _, row in self.df.iterrows():
            processo = {
                'numero': row['Numero_Processo'],
                'cliente': row['Cliente'],
                'advogado': row['Advogado_Responsavel'],
                'tipo': row['Tipo_Acao'],
                'dataCadastro': row['Data_Cadastro'],
                'dataIntimacao': row['Data_Intimacao'],
                'diasPrazo': int(row['Dias_Prazo']),
                'status': row['Status']
            }
            processos.append(processo)
        
        return processos
    
    def calcular_prazos(self):
        """
        Calcula prazos processuais e retorna informações de prazo
        """
        if self.df.empty:
            return []
        
        processos_com_prazo = []
        hoje = datetime.now().date()
        
        for _, row in self.df.iterrows():
            try:
                data_intimacao = pd.to_datetime(row['Data_Intimacao']).date()
                prazo_final = data_intimacao + timedelta(days=int(row['Dias_Prazo']))
                dias_restantes = (prazo_final - hoje).days
                
                if dias_restantes < 0:
                    status_prazo = 'vencido'
                elif dias_restantes <= 2:
                    status_prazo = 'critico'
                elif dias_restantes <= 5:
                    status_prazo = 'atencao'
                else:
                    status_prazo = 'normal'
                
                processo = {
                    'numero': row['Numero_Processo'],
                    'cliente': row['Cliente'],
                    'advogado': row['Advogado_Responsavel'],
                    'dataIntimacao': row['Data_Intimacao'],
                    'prazoFinal': prazo_final.strftime('%Y-%m-%d'),
                    'diasRestantes': dias_restantes,
                    'statusPrazo': status_prazo
                }
                processos_com_prazo.append(processo)
                
            except Exception as e:
                print(f"Erro ao calcular prazo para processo {row['Numero_Processo']}: {e}")
        
        return processos_com_prazo
    
    def gerar_contrato(self, dados_cliente, template_tipo='contrato_servicos'):
        """
        Gera um contrato personalizado
        """
        try:
            # Template básico em memória (em produção, usar arquivos .docx reais)
            templates = {
                'contrato_servicos': {
                    'titulo': 'CONTRATO DE PRESTAÇÃO DE SERVIÇOS JURÍDICOS',
                    'conteudo': f"""
CONTRATO DE PRESTAÇÃO DE SERVIÇOS JURÍDICOS

CONTRATANTE: {dados_cliente.get('nome', '[NOME_CLIENTE]')}
CPF: {dados_cliente.get('cpf', '[CPF_CLIENTE]')}
Endereço: {dados_cliente.get('endereco', '[ENDERECO_CLIENTE]')}
Telefone: {dados_cliente.get('telefone', '[TELEFONE_CLIENTE]')}
E-mail: {dados_cliente.get('email', '[EMAIL_CLIENTE]')}

CONTRATADO: {dados_cliente.get('advogado', '[ADVOGADO]')}

Data: {datetime.now().strftime('%d/%m/%Y')}

Pelo presente instrumento, as partes acima qualificadas acordam
as seguintes cláusulas e condições:

CLÁUSULA 1ª - DO OBJETO
O presente contrato tem por objeto a prestação de serviços jurídicos
pelo CONTRATADO ao CONTRATANTE.

CLÁUSULA 2ª - DAS RESPONSABILIDADES
O CONTRATADO compromete-se a prestar os serviços com diligência
e em conformidade com a legislação vigente.

CLÁUSULA 3ª - DO FORO
Fica eleito o foro da comarca para dirimir quaisquer questões
decorrentes do presente contrato.

____________________                    ____________________
    CONTRATANTE                             CONTRATADO
                    """
                },
                'procuracao': {
                    'titulo': 'PROCURAÇÃO',
                    'conteudo': f"""
PROCURAÇÃO

OUTORGANTE: {dados_cliente.get('nome', '[NOME_CLIENTE]')}
CPF: {dados_cliente.get('cpf', '[CPF_CLIENTE]')}

OUTORGADO: {dados_cliente.get('advogado', '[ADVOGADO]')}

Pelo presente instrumento, o OUTORGANTE nomeia e constitui
seu bastante procurador o OUTORGADO, para representá-lo
perante órgãos públicos e tribunais.

Data: {datetime.now().strftime('%d/%m/%Y')}

____________________
    OUTORGANTE
                    """
                }
            }
            
            template = templates.get(template_tipo, templates['contrato_servicos'])
            
            # Criar arquivo temporário
            temp_dir = tempfile.mkdtemp()
            filename = f"{template['titulo']}_{dados_cliente.get('nome', 'Cliente')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = os.path.join(temp_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(template['conteudo'])
            
            return True, filepath, filename
            
        except Exception as e:
            return False, str(e), None
    
    def gerar_relatorio(self, mes=None, ano=None):
        """
        Gera um relatório com estatísticas dos processos
        """
        if mes is None:
            mes = datetime.now().month
        if ano is None:
            ano = datetime.now().year
        
        if self.df.empty:
            return {
                'periodo': f"{mes:02d}/{ano}",
                'totalProcessos': 0,
                'mensagem': 'Não há processos cadastrados'
            }
        
        # Filtrar por mês/ano
        df = self.df.copy()
        try:
            df['Data_Cadastro'] = pd.to_datetime(df['Data_Cadastro'])
            df_filtrado = df[
                (df['Data_Cadastro'].dt.month == mes) & 
                (df['Data_Cadastro'].dt.year == ano)
            ]
        except Exception as e:
            print(f"Erro ao filtrar dados por período: {e}")
            df_filtrado = df
        
        # Calcular estatísticas
        total_processos = len(df_filtrado)
        
        if total_processos == 0:
            return {
                'periodo': f"{mes:02d}/{ano}",
                'totalProcessos': 0,
                'mensagem': f'Não há processos cadastrados para {mes:02d}/{ano}'
            }
        
        processos_por_advogado = df_filtrado['Advogado_Responsavel'].value_counts().to_dict()
        processos_por_tipo = df_filtrado['Tipo_Acao'].value_counts().to_dict()
        processos_por_status = df_filtrado['Status'].value_counts().to_dict()
        
        # Calcular status dos prazos
        processos_com_prazo = self.calcular_prazos()
        status_prazos = {}
        for processo in processos_com_prazo:
            status = processo['statusPrazo']
            status_prazos[status] = status_prazos.get(status, 0) + 1
        
        return {
            'periodo': f"{mes:02d}/{ano}",
            'totalProcessos': total_processos,
            'processosPorAdvogado': processos_por_advogado,
            'processosPorTipo': processos_por_tipo,
            'processosPorStatus': processos_por_status,
            'statusPrazos': status_prazos,
            'dataGeracao': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        }
    
    def buscar_processos(self, termo):
        """
        Busca processos com base em termo
        """
        if self.df.empty or not termo:
            return self.obter_todos_processos()
        
        # Buscar em múltiplas colunas
        df_resultado = self.df[
            self.df['Numero_Processo'].str.contains(termo, case=False, na=False) |
            self.df['Cliente'].str.contains(termo, case=False, na=False) |
            self.df['Advogado_Responsavel'].str.contains(termo, case=False, na=False) |
            self.df['Tipo_Acao'].str.contains(termo, case=False, na=False)
        ]
        
        processos = []
        for _, row in df_resultado.iterrows():
            processo = {
                'numero': row['Numero_Processo'],
                'cliente': row['Cliente'],
                'advogado': row['Advogado_Responsavel'],
                'tipo': row['Tipo_Acao'],
                'dataCadastro': row['Data_Cadastro'],
                'dataIntimacao': row['Data_Intimacao'],
                'diasPrazo': int(row['Dias_Prazo']),
                'status': row['Status']
            }
            processos.append(processo)
        
        return processos


# Inicializar Flask
app = Flask(__name__)
CORS(app)  # Permitir requisições CORS

# Configurações
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('dados', exist_ok=True)
os.makedirs('documentos_gerados', exist_ok=True)

# Inicializar sistema de automação
automacao = AutomatizacaoEscritorio('dados/processos.xlsx')

# Interface HTML (será servida pela rota principal)
HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema de Automação - Escritório de Advocacia</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        /* CSS completo da interface anterior */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #008080;
            min-height: 100vh;
            color: #333;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            text-align: center;
        }

        .header h1 {
            color: #2c3e50;
            margin-bottom: 5px;
            font-size: 2.2em;
        }

        .header p {
            color: #7f8c8d;
            font-size: 1.1em;
        }

        .nav-tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 20px;
            background: rgba(255, 255, 255, 0.1);
            padding: 5px;
            border-radius: 12px;
            backdrop-filter: blur(10px);
        }

        .nav-tab {
            flex: 1;
            padding: 12px 20px;
            background: transparent;
            border: none;
            border-radius: 8px;
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .nav-tab:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateY(-2px);
        }

        .nav-tab.active {
            background: rgba(255, 255, 255, 0.95);
            color: #2c3e50;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }

        .content-panel {
            display: none;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            animation: fadeIn 0.5s ease-in;
        }

        .content-panel.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            text-decoration: none;
            margin-right: 10px;
            margin-bottom: 10px;
        }

        .btn-primary {
            background: linear-gradient(45deg, #008080, #20B2AA);
            color: white;
        }

        .btn-success {
            background: linear-gradient(45deg, #56ab2f, #a8e6cf);
            color: white;
        }

        .btn-danger {
            background: linear-gradient(45deg, #ff6b6b, #ee5a24);
            color: white;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #2c3e50;
        }

        input, select, textarea {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s ease;
            background: #fff;
        }

        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .table-container {
            overflow-x: auto;
            margin-top: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }

        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }

        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }

        tr:hover {
            background: #f8f9fa;
        }

        .status-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }

        .status-ativo { background: #d4edda; color: #155724; }
        .status-critico { background: #f8d7da; color: #721c24; }
        .status-atencao { background: #fff3cd; color: #856404; }
        .status-normal { background: #d4edda; color: #155724; }
        .status-vencido { background: #f8d7da; color: #721c24; }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            text-align: center;
            border-left: 4px solid #667eea;
        }

        .stat-number {
            font-size: 2.5em;
            font-weight: 700;
            color: #2c3e50;
            margin-bottom: 5px;
        }

        .stat-label {
            color: #7f8c8d;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9em;
        }

        .search-box {
            position: relative;
            margin-bottom: 20px;
        }

        .search-box input {
            padding-left: 45px;
        }

        .search-box i {
            position: absolute;
            left: 15px;
            top: 50%;
            transform: translateY(-50%);
            color: #7f8c8d;
        }

        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1000;
            backdrop-filter: blur(5px);
        }

        .modal-content {
            background: white;
            margin: 5% auto;
            padding: 30px;
            border-radius: 15px;
            width: 90%;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .close {
            background: none;
            border: none;
            font-size: 1.5em;
            cursor: pointer;
            color: #7f8c8d;
            padding: 5px;
            border-radius: 50%;
            width: 35px;
            height: 35px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .close:hover {
            background: #f8f9fa;
            color: #dc3545;
        }

        .alert {
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .alert-success {
            background: #d4edda;
            border-left: 4px solid #28a745;
            color: #155724;
        }

        .alert-danger {
            background: #f8d7da;
            border-left: 4px solid #dc3545;
            color: #721c24;
        }

        .alert-info {
            background: #d1ecf1;
            border-left: 4px solid #17a2b8;
            color: #0c5460;
        }

        .loading {
            text-align: center;
            padding: 20px;
        }

        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-balance-scale"></i> Sistema de Automação Jurídica</h1>
            <p>Programa de estudo de automação de gestão de processos, prazos e documentos em Python <br> Conectado ao Backend </p>
        </div>

        <div class="nav-tabs">
            <button class="nav-tab active" data-tab="processos">
                <i class="fas fa-folder-open"></i> Processos
            </button>
            <button class="nav-tab" data-tab="prazos">
                <i class="fas fa-clock"></i> Prazos
            </button>
            <button class="nav-tab" data-tab="documentos">
                <i class="fas fa-file-contract"></i> Documentos
            </button>
            <button class="nav-tab" data-tab="relatorios">
                <i class="fas fa-chart-bar"></i> Relatórios
            </button>
        </div>

        <!-- Painel de Processos -->
        <div class="content-panel active" id="processos">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2><i class="fas fa-folder-open"></i> Gestão de Processos</h2>
                <button class="btn btn-primary" onclick="openModal('modalNovoProcesso')">
                    <i class="fas fa-plus"></i> Novo Processo
                </button>
            </div>

            <div class="search-box">
                <i class="fas fa-search"></i>
                <input type="text" id="searchProcessos" placeholder="Buscar por número, cliente ou advogado...">
            </div>

            <div id="loadingProcessos" class="loading" style="display: none;">
                <div class="spinner"></div>
                <p>Carregando processos...</p>
            </div>

            <div class="table-container">
                <table id="tabelaProcessos">
                    <thead>
                        <tr>
                            <th>Número</th>
                            <th>Cliente</th>
                            <th>Advogado</th>
                            <th>Tipo</th>
                            <th>Data Cadastro</th>
                            <th>Status</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody id="bodyProcessos">
                        <!-- Dados serão inseridos via API -->
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Outros painéis similares à interface anterior -->
        <div class="content-panel" id="prazos">
            <h2><i class="fas fa-clock"></i> Controle de Prazos</h2>
            
            <div class="stats-grid">
                <div class="stat-card" style="border-left-color: #dc3545;">
                    <div class="stat-number" id="statVencidos">0</div>
                    <div class="stat-label">Vencidos</div>
                </div>
                <div class="stat-card" style="border-left-color: #ffc107;">
                    <div class="stat-number" id="statCriticos">0</div>
                    <div class="stat-label">Críticos</div>
                </div>
                <div class="stat-card" style="border-left-color: #fd7e14;">
                    <div class="stat-number" id="statAtencao">0</div>
                    <div class="stat-label">Atenção</div>
                </div>
                <div class="stat-card" style="border-left-color: #28a745;">
                    <div class="stat-number" id="statNormais">0</div>
                    <div class="stat-label">Normais</div>
                </div>
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Número</th>
                            <th>Cliente</th>
                            <th>Data Intimação</th>
                            <th>Prazo Final</th>
                            <th>Dias Restantes</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody id="bodyPrazos">
                        <!-- Dados serão inseridos via API -->
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Painel de Documentos -->
        <div class="content-panel" id="documentos">
            <h2><i class="fas fa-file-contract"></i> Geração de Documentos</h2>
            
            <div class="alert alert-info">
                <i class="fas fa-info-circle"></i>
                Funcionalidade de geração de contratos conectada ao backend Python.
            </div>

            <form id="formContrato">
                <div class="form-row">
                    <div class="form-group">
                        <label for="templateContrato">Template *</label>
                        <select id="templateContrato" required>
                            <option value="">Selecione um template</option>
                            <option value="contrato_servicos">Contrato de Serviços Jurídicos</option>
                            <option value="procuracao">Procuração</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="clienteContrato">Cliente *</label>
                        <input type="text" id="clienteContrato" placeholder="Nome do cliente" required>
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="cpfContrato">CPF *</label>
                        <input type="tex1t" id="cpfContrato" minlength="11" maxlength="11" placeholder="000.000.000-00" required>
                    </div>
                    <div class="form-group">
                        <label for="advogadoContrato">Advogado Responsável *</label>
                        <input type="text" id="advogadoContrato" placeholder="Nome do advogado" required>
                    </div>
                </div>

                <div class="form-group">
                    <label for="enderecoContrato">Endereço</label>
                    <input type="text" id="enderecoContrato" placeholder="Endereço completo">
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="telefoneContrato">Telefone</label>
                        <input type="text" id="telefoneContrato" min="19" max="19" placeholder="(00) 00000-0000">
                    </div>
                    <div class="form-group">
                        <label for="emailContrato">E-mail</label>
                        <input type="email" id="emailContrato" placeholder="cliente@email.com">
                    </div>
                </div>

                <button type="submit" class="btn btn-success">
                    <i class="fas fa-file-download"></i> Gerar Documento
                </button>
            </form>
        </div>

        <!-- Painel de Relatórios -->
        <div class="content-panel" id="relatorios">
            <h2><i class="fas fa-chart-bar"></i> Relatórios e Estatísticas</h2>
            
            <div class="form-row" style="margin-bottom: 20px;">
                <div class="form-group">
                    <label for="mesRelatorio">Mês</label>
                    <select id="mesRelatorio">
                        <option value="1">Janeiro</option>
                        <option value="2">Fevereiro</option>
                        <option value="3">Março</option>
                        <option value="4">Abril</option>
                        <option value="5">Maio</option>
                        <option value="6">Junho</option>
                        <option value="7">Julho</option>
                        <option value="8">Agosto</option>
                        <option value="9">Setembro</option>
                        <option value="10">Outubro</option>
                        <option value="11">Novembro</option>
                        <option value="12">Dezembro</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="anoRelatorio">Ano</label>
                    <select id="anoRelatorio">
                        <option value="2023">2023</option>
                        <option value="2024">2024</option>
                        <option value="2025">2025</option>
                    </select>
                </div>
            </div>

            <button class="btn btn-primary" onclick="gerarRelatorio()">
                <i class="fas fa-chart-line"></i> Gerar Relatório
            </button>

            <div id="relatorioContent" style="margin-top: 20px;"></div>
        </div>
    </div>

    <!-- Modal Novo Processo -->
    <div class="modal" id="modalNovoProcesso">
        <div class="modal-content">
            <div class="modal-header">
                <h3><i class="fas fa-plus"></i> Novo Processo</h3>
                <button class="close" onclick="closeModal('modalNovoProcesso')">&times;</button>
            </div>
            
            <form id="formNovoProcesso">
                <div class="form-row">
                    <div class="form-group">
                        <label for="numeroProcesso">Número do Processo *</label>
                        <input type="text" id="numeroProcesso" required placeholder="001/2025">
                    </div>
                    <div class="form-group">
                        <label for="clienteProcesso">Cliente *</label>
                        <input type="text" id="clienteProcesso" required placeholder="Nome do cliente">
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="advogadoProcesso">Advogado Responsável *</label>
                        <input type="text" id="advogadoProcesso" required placeholder="Nome do advogado">
                    </div>
                    <div class="form-group">
                        <label for="tipoAcao">Tipo de Ação *</label>
                        <select id="tipoAcao" required>
                            <option value="">Selecione</option>
                            <option value="Cível">Cível</option>
                            <option value="Trabalhista">Trabalhista</option>
                            <option value="Penal">Penal</option>
                            <option value="Família">Família</option>
                            <option value="Tributário">Tributário</option>
                            <option value="Administrativo">Administrativo</option>
                        </select>
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="dataIntimacao">Data da Intimação</label>
                        <input type="date" id="dataIntimacao">
                    </div>
                    <div class="form-group">
                        <label for="diasPrazo">Dias de Prazo</label>
                        <input type="number" id="diasPrazo" value="15" min="1" max="365">
                    </div>
                </div>

                <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                    <button type="button" class="btn" style="background: #6c757d; color: white;" onclick="closeModal('modalNovoProcesso')">
                        Cancelar
                    </button>
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i> Salvar Processo
                    </button>
                </div>
            </form>
        </div>
    </div>

    <script>
        // Configuração da API
        const API_BASE_URL = '';  // Como está na mesma origem, não precisa especificar

        // Funções de API
        async function apiCall(endpoint, method = 'GET', data = null) {
            try {
                const options = {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                    }
                };

                if (data) {
                    options.body = JSON.stringify(data);
                }

                const response = await fetch(`${API_BASE_URL}/api/${endpoint}`, options);
                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || 'Erro na requisição');
                }

                return result;
            } catch (error) {
                console.error('Erro na API:', error);
                throw error;
            }
        }

        // Navegação entre abas
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', function() {
                document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.content-panel').forEach(p => p.classList.remove('active'));
                
                this.classList.add('active');
                document.getElementById(this.dataset.tab).classList.add('active');
                
                // Carregar dados do painel
                if (this.dataset.tab === 'processos') {
                    carregarProcessos();
                } else if (this.dataset.tab === 'prazos') {
                    carregarPrazos();
                }
            });
        });

        // Funções de modal
        function openModal(modalId) {
            document.getElementById(modalId).style.display = 'block';
            document.body.style.overflow = 'hidden';
        }

        function closeModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
            document.body.style.overflow = 'auto';
            
            // Resetar formulário se for modal de processo
            if (modalId === 'modalNovoProcesso') {
                document.getElementById('formNovoProcesso').reset();
                document.getElementById('formNovoProcesso').removeAttribute('data-editing');
                document.querySelector('#modalNovoProcesso .modal-header h3').innerHTML = '<i class="fas fa-plus"></i> Novo Processo';
            }
        }

        // Carregar processos
        async function carregarProcessos() {
            const tbody = document.getElementById('bodyProcessos');
            const loading = document.getElementById('loadingProcessos');
            
            loading.style.display = 'block';
            tbody.innerHTML = '';
            
            try {
                const data = await apiCall('processos');
                
                data.processos.forEach(processo => {
                    const row = tbody.insertRow();
                    row.innerHTML = `
                        <td>${processo.numero}</td>
                        <td>${processo.cliente}</td>
                        <td>${processo.advogado}</td>
                        <td>${processo.tipo}</td>
                        <td>${formatarData(processo.dataCadastro)}</td>
                        <td><span class="status-badge status-${processo.status.toLowerCase()}">${processo.status}</span></td>
                        <td>
                            <button class="btn" style="background: #17a2b8; color: white; padding: 5px 10px; margin-right: 5px;" onclick="editarProcesso('${processo.numero}')">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn" style="background: #dc3545; color: white; padding: 5px 10px;" onclick="excluirProcesso('${processo.numero}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    `;
                });
            } catch (error) {
                mostrarAlerta('danger', 'Erro ao carregar processos: ' + error.message);
            } finally {
                loading.style.display = 'none';
            }
        }

        // Carregar prazos
        async function carregarPrazos() {
            try {
                const data = await apiCall('prazos');
                
                // Atualizar estatísticas
                const stats = {
                    vencidos: data.prazos.filter(p => p.statusPrazo === 'vencido').length,
                    criticos: data.prazos.filter(p => p.statusPrazo === 'critico').length,
                    atencao: data.prazos.filter(p => p.statusPrazo === 'atencao').length,
                    normais: data.prazos.filter(p => p.statusPrazo === 'normal').length
                };
                
                document.getElementById('statVencidos').textContent = stats.vencidos;
                document.getElementById('statCriticos').textContent = stats.criticos;
                document.getElementById('statAtencao').textContent = stats.atencao;
                document.getElementById('statNormais').textContent = stats.normais;
                
                // Atualizar tabela
                const tbody = document.getElementById('bodyPrazos');
                tbody.innerHTML = '';
                
                data.prazos
                    .sort((a, b) => a.diasRestantes - b.diasRestantes)
                    .forEach(processo => {
                        const row = tbody.insertRow();
                        row.innerHTML = `
                            <td>${processo.numero}</td>
                            <td>${processo.cliente}</td>
                            <td>${formatarData(processo.dataIntimacao)}</td>
                            <td>${formatarData(processo.prazoFinal)}</td>
                            <td>${processo.diasRestantes}</td>
                            <td><span class="status-badge status-${processo.statusPrazo}">${processo.statusPrazo.toUpperCase()}</span></td>
                        `;
                    });
            } catch (error) {
                mostrarAlerta('danger', 'Erro ao carregar prazos: ' + error.message);
            }
        }

        // Adicionar/Editar processo
        document.getElementById('formNovoProcesso').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const numeroEditando = this.getAttribute('data-editing');
            const dados = {
                numero: document.getElementById('numeroProcesso').value,
                cliente: document.getElementById('clienteProcesso').value,
                advogado: document.getElementById('advogadoProcesso').value,
                tipo: document.getElementById('tipoAcao').value,
                dataIntimacao: document.getElementById('dataIntimacao').value || new Date().toISOString().split('T')[0],
                diasPrazo: parseInt(document.getElementById('diasPrazo').value) || 15
            };
            
            try {
                if (numeroEditando) {
                    await apiCall(`processos/${numeroEditando}`, 'PUT', dados);
                    mostrarAlerta('success', 'Processo atualizado com sucesso!');
                } else {
                    await apiCall('processos', 'POST', dados);
                    mostrarAlerta('success', 'Processo cadastrado com sucesso!');
                }
                
                carregarProcessos();
                closeModal('modalNovoProcesso');
            } catch (error) {
                mostrarAlerta('danger', 'Erro ao salvar processo: ' + error.message);
            }
        });

        // Editar processo
        async function editarProcesso(numero) {
            try {
                const data = await apiCall('processos');
                const processo = data.processos.find(p => p.numero === numero);
                
                if (processo) {
                    document.getElementById('numeroProcesso').value = processo.numero;
                    document.getElementById('clienteProcesso').value = processo.cliente;
                    document.getElementById('advogadoProcesso').value = processo.advogado;
                    document.getElementById('tipoAcao').value = processo.tipo;
                    document.getElementById('dataIntimacao').value = processo.dataIntimacao;
                    document.getElementById('diasPrazo').value = processo.diasPrazo;
                    
                    document.querySelector('#modalNovoProcesso .modal-header h3').innerHTML = '<i class="fas fa-edit"></i> Editar Processo';
                    document.getElementById('formNovoProcesso').setAttribute('data-editing', numero);
                    
                    openModal('modalNovoProcesso');
                }
            } catch (error) {
                mostrarAlerta('danger', 'Erro ao carregar processo: ' + error.message);
            }
        }

        // Excluir processo
        async function excluirProcesso(numero) {
            if (confirm('Tem certeza que deseja excluir este processo?')) {
                try {
                    await apiCall(`processos/${numero}`, 'DELETE');
                    mostrarAlerta('success', 'Processo excluído com sucesso!');
                    carregarProcessos();
                } catch (error) {
                    mostrarAlerta('danger', 'Erro ao excluir processo: ' + error.message);
                }
            }
        }

        // Busca de processos
        document.getElementById('searchProcessos').addEventListener('input', async function(e) {
            const termo = e.target.value;
            
            if (termo.length >= 3 || termo.length === 0) {
                try {
                    const data = await apiCall(`buscar?termo=${encodeURIComponent(termo)}`);
                    
                    const tbody = document.getElementById('bodyProcessos');
                    tbody.innerHTML = '';
                    
                    data.processos.forEach(processo => {
                        const row = tbody.insertRow();
                        row.innerHTML = `
                            <td>${processo.numero}</td>
                            <td>${processo.cliente}</td>
                            <td>${processo.advogado}</td>
                            <td>${processo.tipo}</td>
                            <td>${formatarData(processo.dataCadastro)}</td>
                            <td><span class="status-badge status-${processo.status.toLowerCase()}">${processo.status}</span></td>
                            <td>
                                <button class="btn" style="background: #17a2b8; color: white; padding: 5px 10px; margin-right: 5px;" onclick="editarProcesso('${processo.numero}')">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn" style="background: #dc3545; color: white; padding: 5px 10px;" onclick="excluirProcesso('${processo.numero}')">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </td>
                        `;
                    });
                } catch (error) {
                    console.error('Erro na busca:', error);
                }
            }
        });

        // Gerar contrato
        document.getElementById('formContrato').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const dados = {
                template: document.getElementById('templateContrato').value,
                nome: document.getElementById('clienteContrato').value,
                cpf: document.getElementById('cpfContrato').value,
                advogado: document.getElementById('advogadoContrato').value,
                endereco: document.getElementById('enderecoContrato').value,
                telefone: document.getElementById('telefoneContrato').value,
                email: document.getElementById('emailContrato').value
            };
            
            try {
                const response = await fetch('/api/gerar-contrato', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(dados)
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${dados.template}_${dados.nome}.txt`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    
                    mostrarAlerta('success', 'Documento gerado e baixado com sucesso!');
                    this.reset();
                } else {
                    throw new Error('Erro ao gerar documento');
                }
            } catch (error) {
                mostrarAlerta('danger', 'Erro ao gerar documento: ' + error.message);
            }
        });

        // Gerar relatório
        async function gerarRelatorio() {
            const mes = parseInt(document.getElementById('mesRelatorio').value);
            const ano = parseInt(document.getElementById('anoRelatorio').value);
            
            try {
                const data = await apiCall(`relatorio?mes=${mes}&ano=${ano}`);
                
                let relatorioHTML = `
                    <div class="alert alert-info">
                        <i class="fas fa-calendar"></i>
                        <strong>Relatório do período:</strong> ${data.relatorio.periodo}
                    </div>
                    
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">${data.relatorio.totalProcessos}</div>
                            <div class="stat-label">Total de Processos</div>
                        </div>
                `;
                
                if (data.relatorio.totalProcessos > 0) {
                    relatorioHTML += `
                        <div class="stat-card" style="border-left-color: #28a745;">
                            <div class="stat-number">${Object.keys(data.relatorio.processosPorAdvogado).length}</div>
                            <div class="stat-label">Advogados Ativos</div>
                        </div>
                        <div class="stat-card" style="border-left-color: #17a2b8;">
                            <div class="stat-number">${Object.keys(data.relatorio.processosPorTipo).length}</div>
                            <div class="stat-label">Tipos de Ação</div>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                            <h4 style="margin-bottom: 15px; color: #2c3e50;"><i class="fas fa-user-tie"></i> Processos por Advogado</h4>
                            ${Object.entries(data.relatorio.processosPorAdvogado).map(([advogado, count]) => 
                                `<div style="display: flex; justify-content: space-between; margin-bottom: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px;">
                                    <span>${advogado}</span>
                                    <span style="font-weight: bold; color: #667eea;">${count}</span>
                                </div>`
                            ).join('')}
                        </div>
                        
                        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                            <h4 style="margin-bottom: 15px; color: #2c3e50;"><i class="fas fa-gavel"></i> Processos por Tipo</h4>
                            ${Object.entries(data.relatorio.processosPorTipo).map(([tipo, count]) => 
                                `<div style="display: flex; justify-content: space-between; margin-bottom: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px;">
                                    <span>${tipo}</span>
                                    <span style="font-weight: bold; color: #667eea;">${count}</span>
                                </div>`
                            ).join('')}
                        </div>
                    </div>
                    `;
                } else {
                    relatorioHTML += `</div><p style="text-align: center; margin-top: 20px; color: #7f8c8d; font-style: italic;">${data.relatorio.mensagem}</p>`;
                }
                
                document.getElementById('relatorioContent').innerHTML = relatorioHTML;
            } catch (error) {
                mostrarAlerta('danger', 'Erro ao gerar relatório: ' + error.message);
            }
        }

        // Funções utilitárias
        function formatarData(data) {
            if (!data) return '-';
            const date = new Date(data);
            return date.toLocaleDateString('pt-BR');
        }

        function mostrarAlerta(tipo, mensagem) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${tipo}`;
            alertDiv.innerHTML = `
                <i class="fas fa-${tipo === 'success' ? 'check-circle' : tipo === 'danger' ? 'exclamation-triangle' : 'info-circle'}"></i>
                ${mensagem}
            `;
            
            const container = document.querySelector('.container');
            container.insertBefore(alertDiv, container.children[1]);
            
            setTimeout(() => {
                alertDiv.remove();
            }, 5000);
        }

        // Fechar modal ao clicar fora
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        }

        // Inicializar aplicação
        function inicializar() {
            const hoje = new Date();
            document.getElementById('mesRelatorio').value = hoje.getMonth() + 1;
            document.getElementById('anoRelatorio').value = hoje.getFullYear();
            
            carregarProcessos();
        }

        document.addEventListener('DOMContentLoaded', inicializar);
    </script>
</body>
</html>
"""

# Rotas da API
@app.route('/')
def index():
    """Servir a interface HTML"""
    return render_template_string(HTML_INTERFACE)

@app.route('/api/processos', methods=['GET'])
def get_processos():
    """Obter todos os processos"""
    try:
        processos = automacao.obter_todos_processos()
        return jsonify({
            'success': True,
            'processos': processos
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/processos', methods=['POST'])
def add_processo():
    """Adicionar novo processo"""
    try:
        dados = request.get_json()
        sucesso, mensagem = automacao.adicionar_processo(dados)
        
        if sucesso:
            return jsonify({
                'success': True,
                'message': mensagem
            })
        else:
            return jsonify({
                'success': False,
                'error': mensagem
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/processos/<numero>', methods=['PUT'])
def update_processo(numero):
    """Atualizar processo existente"""
    try:
        dados = request.get_json()
        sucesso, mensagem = automacao.atualizar_processo(numero, dados)
        
        if sucesso:
            return jsonify({
                'success': True,
                'message': mensagem
            })
        else:
            return jsonify({
                'success': False,
                'error': mensagem
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/processos/<numero>', methods=['DELETE'])
def delete_processo(numero):
    """Excluir processo"""
    try:
        sucesso, mensagem = automacao.remover_processo(numero)
        
        if sucesso:
            return jsonify({
                'success': True,
                'message': mensagem
            })
        else:
            return jsonify({
                'success': False,
                'error': mensagem
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/prazos', methods=['GET'])
def get_prazos():
    """Obter informações de prazos"""
    try:
        prazos = automacao.calcular_prazos()
        return jsonify({
            'success': True,
            'prazos': prazos
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/gerar-contrato', methods=['POST'])
def gerar_contrato():
    """Gerar contrato personalizado"""
    try:
        dados = request.get_json()
        sucesso, caminho_ou_erro, filename = automacao.gerar_contrato(dados, dados.get('template', 'contrato_servicos'))
        
        if sucesso:
            return send_file(
                caminho_ou_erro,
                as_attachment=True,
                download_name=filename,
                mimetype='text/plain'
            )
        else:
            return jsonify({
                'success': False,
                'error': caminho_ou_erro
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/relatorio', methods=['GET'])
def get_relatorio():
    """Gerar relatório"""
    try:
        mes = request.args.get('mes', type=int)
        ano = request.args.get('ano', type=int)
        
        relatorio = automacao.gerar_relatorio(mes, ano)
        return jsonify({
            'success': True,
            'relatorio': relatorio
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/buscar', methods=['GET'])
def buscar_processos():
    """Buscar processos"""
    try:
        termo = request.args.get('termo', '')
        processos = automacao.buscar_processos(termo)
        return jsonify({
            'success': True,
            'processos': processos
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/backup', methods=['POST'])
def criar_backup():
    """Criar backup dos dados"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_processos_{timestamp}.xlsx'
        backup_path = os.path.join('backups', backup_filename)
        
        os.makedirs('backups', exist_ok=True)
        automacao.df.to_excel(backup_path, index=False)
        
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=backup_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Obter status do sistema"""
    try:
        total_processos = len(automacao.df)
        prazos = automacao.calcular_prazos()
        
        stats_prazos = {
            'vencidos': len([p for p in prazos if p['statusPrazo'] == 'vencido']),
            'criticos': len([p for p in prazos if p['statusPrazo'] == 'critico']),
            'atencao': len([p for p in prazos if p['statusPrazo'] == 'atencao']),
            'normais': len([p for p in prazos if p['statusPrazo'] == 'normal'])
        }
        
        return jsonify({
            'success': True,
            'status': {
                'totalProcessos': total_processos,
                'prazos': stats_prazos,
                'ultimaAtualizacao': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Tratamento de erros
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint não encontrado'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Erro interno do servidor'
    }), 500

if __name__ == '__main__':
    print("🚀 Iniciando Sistema de Automação Jurídica")
    print("📊 Interface disponível em: http://localhost:5000")
    print("🔗 API endpoints disponíveis:")
    print("   GET  /api/processos      - Listar todos os processos")
    print("   POST /api/processos      - Criar novo processo")
    print("   PUT  /api/processos/<id> - Atualizar processo")
    print("   DELETE /api/processos/<id> - Excluir processo")
    print("   GET  /api/prazos         - Obter informações de prazos")
    print("   POST /api/gerar-contrato - Gerar documento personalizado")
    print("   GET  /api/relatorio      - Gerar relatório estatístico")
    print("   GET  /api/buscar         - Buscar processos")
    print("   POST /api/backup         - Criar backup dos dados")
    print("   GET  /api/status         - Status do sistema")
    print("\n💡 Recursos implementados:")
    print("   ✅ CRUD completo de processos")
    print("   ✅ Cálculo automático de prazos")
    print("   ✅ Geração de documentos personalizados")
    print("   ✅ Relatórios estatísticos")
    print("   ✅ Sistema de busca")
    print("   ✅ Interface web responsiva")
    print("   ✅ Persistência em Excel")
    print("   ✅ API REST completa")
    print("\n🔧 Para usar:")
    print("   1. Instale as dependências: pip install flask flask-cors pandas openpyxl python-docx")
    print("   2. Execute: python app.py")
    print("   3. Acesse: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)