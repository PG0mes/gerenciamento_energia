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
        
        return None
    
    @staticmethod
    def calcular_metricas_gerais(fonte_id):
        """Calcula métricas gerais para o dashboard"""
        if not PANDAS_AVAILABLE:
            return {
                'total_energia': 0,
                'potencia_maxima': 0,
                'media_diaria': 0,
                'dias_monitorados': 0,
                'ultima_atualizacao': datetime.now().strftime('%d/%m/%Y %H:%M')
            }
            
        df = DashboardController.get_dados_fonte(fonte_id)
        
        if df is None or df.empty:
            return {
                'total_energia': 0,
                'potencia_maxima': 0,
                'media_diaria': 0,
                'dias_monitorados': 0,
                'ultima_atualizacao': None
            }
        
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
    def get_dados_producao_diaria(fonte_id):
        """Obtém dados de produção diária para gráficos"""
        if not PANDAS_AVAILABLE:
            return []
            
        df = DashboardController.get_dados_fonte(fonte_id)
        
        if df is None or df.empty:
            return []
        
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
    def get_dados_producao_horaria(fonte_id, dia=None):
        """Obtém dados de produção por hora para um dia específico"""
        if not PANDAS_AVAILABLE:
            return []
            
        df = DashboardController.get_dados_fonte(fonte_id)
        
        if df is None or df.empty:
            return []
        
        # Se não for especificado o dia, usa o último dia com dados
        if dia is None:
            dia = df['data_hora'].dt.date.max()
        else:
            dia = datetime.strptime(dia, '%Y-%m-%d').date()
        
        # Filtrar para o dia específico
        df_dia = df[df['data_hora'].dt.date == dia]
        
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