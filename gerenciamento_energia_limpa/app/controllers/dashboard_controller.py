import os
import json
from datetime import datetime, timedelta

# Importações condicionais para permitir execução mesmo sem todas as dependências
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    # Criando classes vazias para evitar erros de importação
    class MockPandas:
        def __getattr__(self, name):
            return None
    pd = MockPandas()

class DashboardController:
    """Controlador para processamento de dados do dashboard"""
    
    @staticmethod
    def get_dados_fonte(fonte_id):
        """Obtém todos os dados disponíveis para uma fonte específica"""
        if not PANDAS_AVAILABLE:
            return None
            
        # Verificar arquivos de dados simulados
        path_simulado = f'data/simulated/fonte_{fonte_id}_simulado.csv'
        
        # Verificar arquivos de dados processados
        processed_files = []
        processed_dir = 'data/processed'
        if os.path.exists(processed_dir):
            processed_files = [f for f in os.listdir(processed_dir) 
                              if f.startswith(f'fonte_{fonte_id}_') and f.endswith('.csv')]
        
        # Lista para armazenar todos os dataframes
        dfs = []
        
        # Carregar dados simulados se existirem
        if os.path.exists(path_simulado):
            df_simulado = pd.read_csv(path_simulado)
            df_simulado['data_hora'] = pd.to_datetime(df_simulado['data_hora'])
            dfs.append(df_simulado)
        
        # Carregar dados processados se existirem
        for file in processed_files:
            file_path = os.path.join(processed_dir, file)
            df = pd.read_csv(file_path)
            df['data_hora'] = pd.to_datetime(df['data_hora'])
            dfs.append(df)
        
        # Combinar todos os dados
        if dfs:
            df_combined = pd.concat(dfs, ignore_index=True)
            # Remover duplicações por data_hora (caso haja sobreposição)
            df_combined = df_combined.drop_duplicates(subset=['data_hora'])
            # Ordenar por data_hora
            df_combined = df_combined.sort_values('data_hora')
            return df_combined
        else:
            # Se não existirem dados, gerar dados simulados automaticamente
            try:
                from app.data_processors.data_importer import GrowattDataImporter
                resultado = GrowattDataImporter.gerar_dados_simulados(fonte_id, dias=30)
                if resultado['sucesso'] and os.path.exists(resultado['caminho_arquivo']):
                    df_simulado = pd.read_csv(resultado['caminho_arquivo'])
                    df_simulado['data_hora'] = pd.to_datetime(df_simulado['data_hora'])
                    return df_simulado
            except Exception as e:
                print(f"Erro ao gerar dados simulados automaticamente: {str(e)}")
                
        return None
    
    @staticmethod
    def calcular_metricas_gerais(fonte_id):
        """Calcula métricas gerais para o dashboard"""
        if not PANDAS_AVAILABLE:
            return DashboardController._gerar_metricas_ficticias()
            
        df = DashboardController.get_dados_fonte(fonte_id)
        
        if df is None or df.empty:
            return DashboardController._gerar_metricas_ficticias()
        
        # Cálculo das métricas
        total_energia = df['energia_kwh'].sum()
        potencia_maxima = df['potencia_kw'].max()
        
        # Calcular a produção média diária
        df['data'] = df['data_hora'].dt.date
        energia_por_dia = df.groupby('data')['energia_kwh'].sum()
        media_diaria = energia_por_dia.mean()
        dias_monitorados = len(energia_por_dia)
        
        # Última atualização
        ultima_atualizacao = df['data_hora'].max()
        
        return {
            'total_energia': round(total_energia, 2),
            'potencia_maxima': round(potencia_maxima, 2),
            'media_diaria': round(media_diaria, 2),
            'dias_monitorados': dias_monitorados,
            'ultima_atualizacao': ultima_atualizacao.strftime('%d/%m/%Y %H:%M')
        }
    
    @staticmethod
    def _gerar_metricas_ficticias():
        """Gera métricas fictícias para demonstração quando não há dados reais"""
        import random
        
        # Dados fictícios realistas
        dias_monitorados = random.randint(25, 35)
        media_diaria = random.uniform(12.5, 18.2)
        total_energia = media_diaria * dias_monitorados
        potencia_maxima = random.uniform(4.2, 5.8)
        
        return {
            'total_energia': round(total_energia, 2),
            'potencia_maxima': round(potencia_maxima, 2),
            'media_diaria': round(media_diaria, 2),
            'dias_monitorados': dias_monitorados,
            'ultima_atualizacao': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
    
    @staticmethod
    def get_dados_producao_diaria(fonte_id):
        """Obtém dados de produção diária para gráficos"""
        if not PANDAS_AVAILABLE:
            return DashboardController._gerar_dados_diarios_ficticios()
            
        df = DashboardController.get_dados_fonte(fonte_id)
        
        if df is None or df.empty:
            return DashboardController._gerar_dados_diarios_ficticios()
        
        # Agrupar por data e somar energia
        df['data'] = df['data_hora'].dt.date
        producao_diaria = df.groupby('data')['energia_kwh'].sum().reset_index()
        
        # Converter para o formato adequado para o gráfico
        resultado = []
        for _, row in producao_diaria.iterrows():
            resultado.append({
                'data': row['data'].strftime('%d/%m/%Y'),
                'energia': round(row['energia_kwh'], 2)
            })
        
        return resultado
    
    @staticmethod
    def _gerar_dados_diarios_ficticios():
        """Gera dados fictícios de produção diária para demonstração"""
        resultado = []
        hoje = datetime.now()
        
        # Gerar dados para os últimos 14 dias
        for i in range(14, 0, -1):
            data = hoje - timedelta(days=i)
            # Gerar valor fictício com variação
            # Padrão mais alto nos dias de sol, menor nos fins de semana
            base = 15.0  # kWh base por dia
            
            # Variação por dia da semana (menor nos fins de semana)
            if data.weekday() >= 5:  # Sábado e domingo
                fator_dia = 0.8
            else:
                fator_dia = 1.0
                
            # Variação aleatória
            import random
            variacao = random.uniform(0.7, 1.3)
            
            energia = round(base * fator_dia * variacao, 2)
            
            resultado.append({
                'data': data.strftime('%d/%m/%Y'),
                'energia': energia
            })
            
        return resultado
    
    @staticmethod
    def get_dados_producao_horaria(fonte_id, dia=None):
        """Obtém dados de produção por hora para um dia específico"""
        if not PANDAS_AVAILABLE:
            return DashboardController._gerar_dados_horarios_ficticios()
            
        df = DashboardController.get_dados_fonte(fonte_id)
        
        if df is None or df.empty:
            return DashboardController._gerar_dados_horarios_ficticios()
        
        # Se não for especificado o dia, usa o último dia com dados
        if dia is None:
            dia = df['data_hora'].dt.date.max()
        else:
            dia = datetime.strptime(dia, '%Y-%m-%d').date()
        
        # Filtrar para o dia específico
        df_dia = df[df['data_hora'].dt.date == dia]
        
        if df_dia.empty:
            return DashboardController._gerar_dados_horarios_ficticios()
            
        # Agrupar por hora
        df_dia['hora'] = df_dia['data_hora'].dt.hour
        producao_horaria = df_dia.groupby('hora')['potencia_kw'].mean().reset_index()
        
        # Converter para o formato adequado para o gráfico
        resultado = []
        for hora in range(24):
            energia = 0
            hora_df = producao_horaria[producao_horaria['hora'] == hora]
            if not hora_df.empty:
                energia = round(hora_df['potencia_kw'].iloc[0], 2)
            
            resultado.append({
                'hora': f"{hora:02d}:00",
                'potencia': energia
            })
        
        return resultado
        
    @staticmethod
    def _gerar_dados_horarios_ficticios():
        """Gera dados fictícios de produção horária para demonstração"""
        resultado = []
        
        # Padrão de geração solar diária (maior durante o dia, zero à noite)
        padrao_solar = [
            0, 0, 0, 0, 0, 0.1,    # 0-5h: noite/amanhecer
            0.2, 0.5, 1.2, 2.1, 2.8, 3.4,   # 6-11h: manhã
            3.7, 3.5, 3.2, 2.8, 2.0, 1.3,   # 12-17h: tarde
            0.6, 0.1, 0, 0, 0, 0    # 18-23h: anoitecer/noite
        ]
        
        # Adicionar variação aleatória
        import random
        for hora in range(24):
            base = padrao_solar[hora]
            # Adicionar variação de +/- 20%
            variacao = random.uniform(0.8, 1.2)
            potencia = round(base * variacao, 2)
            
            resultado.append({
                'hora': f"{hora:02d}:00",
                'potencia': potencia
            })
            
        return resultado