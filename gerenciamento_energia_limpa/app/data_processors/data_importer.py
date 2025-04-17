import os
from datetime import datetime, timedelta

# Importações condicionais para permitir execução mesmo sem todas as dependências
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    # Criando classes vazias para evitar erros de importação
    class MockPandas:
        def __getattr__(self, name):
            return None
    pd = MockPandas()
    
    class MockNumpy:
        def __getattr__(self, name):
            return None
        
        @staticmethod
        def random_uniform(*args, **kwargs):
            return 0.5
    np = MockNumpy()

class GrowattDataImporter:
    """Classe para importação de dados de inversores Growatt"""
    
    @staticmethod
    def importar_csv(arquivo, fonte_id):
        """Importa dados de um arquivo CSV exportado do Growatt"""
        if not PANDAS_AVAILABLE:
            return {
                'sucesso': False,
                'mensagem': 'Biblioteca pandas não está instalada. Instale-a com pip install pandas.',
                'caminho_arquivo': None,
                'registros': 0
            }
            
        try:
            # Leitura do arquivo CSV
            df = pd.read_csv(arquivo)
            
            # Processamento e limpeza dos dados
            # Ajuste conforme o formato real dos seus arquivos Growatt
            df = GrowattDataImporter._processar_dados_csv(df)
            
            # Associar ao ID da fonte
            df['fonte_id'] = fonte_id
            
            # Salvar dados processados
            os.makedirs('data/processed', exist_ok=True)
            output_path = f'data/processed/fonte_{fonte_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.csv'
            df.to_csv(output_path, index=False)
            
            return {
                'sucesso': True,
                'mensagem': 'Dados importados com sucesso',
                'caminho_arquivo': output_path,
                'registros': len(df)
            }
            
        except Exception as e:
            return {
                'sucesso': False,
                'mensagem': f'Erro ao importar dados: {str(e)}',
                'caminho_arquivo': None,
                'registros': 0
            }
    
    @staticmethod
    def _processar_dados_csv(df):
        """Processa os dados do CSV para padronização"""
        # Verificar se as colunas necessárias existem
        colunas_esperadas = ['data_hora', 'potencia_kw', 'energia_kwh', 'temperatura_inversor']
        colunas_presentes = set(df.columns)
        
        # Se as colunas não estiverem no formato esperado, tenta converter
        if not all(col in colunas_presentes for col in colunas_esperadas):
            # Mapeia nomes de colunas comuns em arquivos Growatt para o formato padrão
            mapeamento_colunas = {
                'timestamp': 'data_hora',
                'power': 'potencia_kw',
                'energy': 'energia_kwh',
                'temperature': 'temperatura_inversor',
                'date': 'data_hora',
                'time': 'data_hora',
                'pac': 'potencia_kw',
                'e-day': 'energia_kwh',
                'temp': 'temperatura_inversor'
            }
            
            # Renomear colunas conforme o mapeamento
            df = df.rename(columns={col: mapeamento_colunas[col] for col in df.columns 
                                   if col in mapeamento_colunas})
        
        # Verificar se a coluna data_hora existe e está no formato correto
        if 'data_hora' in df.columns:
            # Converter para datetime se ainda não estiver nesse formato
            if not pd.api.types.is_datetime64_any_dtype(df['data_hora']):
                df['data_hora'] = pd.to_datetime(df['data_hora'], errors='coerce')
                
                # Remover linhas com datas inválidas
                df = df.dropna(subset=['data_hora'])
        
        # Assegurar que as colunas numéricas são do tipo correto
        if 'potencia_kw' in df.columns:
            df['potencia_kw'] = pd.to_numeric(df['potencia_kw'], errors='coerce')
            
        if 'energia_kwh' in df.columns:
            df['energia_kwh'] = pd.to_numeric(df['energia_kwh'], errors='coerce')
            
        if 'temperatura_inversor' in df.columns:
            df['temperatura_inversor'] = pd.to_numeric(df['temperatura_inversor'], errors='coerce')
        
        # Remover linhas com valores nulos nas colunas importantes
        df = df.dropna(subset=['potencia_kw', 'energia_kwh'])
        
        # Ordenar o DataFrame por data_hora
        if 'data_hora' in df.columns:
            df = df.sort_values('data_hora')
        
        return df
    
    @staticmethod
    def gerar_dados_simulados(fonte_id, dias=30):
        """Gera dados simulados para desenvolvimento e testes"""
        if not PANDAS_AVAILABLE:
            return {
                'sucesso': False,
                'mensagem': 'Bibliotecas pandas e numpy não estão instaladas. Instale-as com pip install pandas numpy.',
                'caminho_arquivo': None,
                'registros': 0
            }
            
        # Data atual
        end_date = datetime.now()
        start_date = end_date - timedelta(days=dias)
        
        # Gerar timestamps em intervalos de 15 minutos
        timestamps = pd.date_range(start=start_date, end=end_date, freq='15T')
        
        # Dados base - padrão diário de geração solar (0h-23h)
        # 0 durante a noite, pico durante o meio-dia
        padrao_diario = [0, 0, 0, 0, 0, 0, 0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 
                         1.0, 0.9, 0.8, 0.7, 0.5, 0.3, 0.1, 0, 0, 0, 0, 0]
        
        # Criar DataFrame
        data = []
        
        for ts in timestamps:
            hora = ts.hour
            # Potência base conforme hora do dia (máximo 5kW para uma instalação de exemplo)
            potencia_base = padrao_diario[hora] * 5.0
            
            # Adicionar variação aleatória (+/- 20%)
            variacao = np.random.uniform(-0.2, 0.2)
            potencia = max(0, potencia_base * (1 + variacao))
            
            # Fatores climáticos (simplificado)
            # Redução nos finais de semana para simular diferenças
            if ts.weekday() >= 5:  # Sábado e domingo
                potencia *= 0.8
            
            # Variação sazonal (exemplo simplificado)
            # Mais produção no verão
            mes = ts.month
            if 3 <= mes <= 5:  # Outono
                fator_sazonal = 0.8
            elif 6 <= mes <= 8:  # Inverno
                fator_sazonal = 0.7
            elif 9 <= mes <= 11:  # Primavera
                fator_sazonal = 0.9
            else:  # Verão
                fator_sazonal = 1.0
                
            potencia *= fator_sazonal
            
            # Energia acumulada (kWh) - integração da potência no tempo (15min = 0.25h)
            energia = potencia * 0.25
            
            data.append({
                'data_hora': ts,
                'potencia_kw': round(potencia, 3),
                'energia_kwh': round(energia, 3),
                'temperatura_inversor': round(np.random.uniform(25, 45), 1),
                'fonte_id': fonte_id
            })
        
        # Criar DataFrame
        df = pd.DataFrame(data)
        
        # Salvar dados simulados
        os.makedirs('data/simulated', exist_ok=True)
        output_path = f'data/simulated/fonte_{fonte_id}_simulado.csv'
        df.to_csv(output_path, index=False)
        
        return {
            'sucesso': True,
            'mensagem': 'Dados simulados gerados com sucesso',
            'caminho_arquivo': output_path,
            'registros': len(df)
        }