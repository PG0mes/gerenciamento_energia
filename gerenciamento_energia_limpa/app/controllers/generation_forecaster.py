import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from app.services.weather_service import WeatherService
from app.controllers.dashboard_controller import DashboardController
from app.models.fonte_energia import FonteEnergiaRepository

class GenerationForecaster:
    """Classe para previsão de geração de energia solar com base em dados meteorológicos"""
    
    # Diretório para armazenar previsões
    FORECAST_DIR = os.path.join('data', 'forecasts')
    
    # Pesos para diferentes condições meteorológicas
    WEATHER_WEIGHTS = {
        'uvi': 0.45,            # Índice UV tem grande impacto na geração
        'clouds': 0.25,         # Cobertura de nuvens reduz significativamente a geração
        'rain': 0.15,           # Chuva reduz a geração
        'pop': 0.05,            # Probabilidade de precipitação
        'daylight_hours': 0.10, # Horas de luz solar disponíveis
    }
    
    # Condições ideais para máxima referência
    IDEAL_CONDITIONS = {
        'uvi': 10.0,            # Índice UV máximo
        'clouds': 0.0,          # Sem nuvens
        'rain': 0.0,            # Sem chuva
        'pop': 0.0,             # Sem probabilidade de chuva
        'daylight_hours': 12.0  # 12 horas de luz
    }
    
    @classmethod
    def predict_generation(cls, fonte_id, days=5):
        """
        Calcula a previsão de geração para os próximos dias
        
        Args:
            fonte_id (int): ID da fonte de energia
            days (int): Número de dias para previsão
            
        Returns:
            list: Lista com previsões de geração ou None em caso de erro
        """
        # Verificar se diretório existe
        if not os.path.exists(cls.FORECAST_DIR):
            os.makedirs(cls.FORECAST_DIR)
        
        # Carregar dados históricos da fonte
        fonte = FonteEnergiaRepository.buscar_por_id(fonte_id)
        if not fonte:
            print(f"Fonte com ID {fonte_id} não encontrada")
            return None
            
        # Obter coordenadas geográficas da localização
        coords = WeatherService.get_location_coords(fonte.localizacao)
        if not coords:
            print(f"Não foi possível obter coordenadas para: {fonte.localizacao}")
            # Usar previsão simulada como fallback
            return cls._generate_simulated_forecast(fonte, days)
            
        lat, lon = coords
        
        # Obter previsão do tempo
        forecast = WeatherService.get_forecast(lat, lon, days)
        if not forecast:
            print("Não foi possível obter previsão do tempo - usando dados simulados")
            return cls._generate_simulated_forecast(fonte, days)
            
        # Obter histórico de produção
        df_producao = cls._obter_historico_producao(fonte_id)
        if df_producao is None or df_producao.empty:
            print("Histórico de produção não disponível")
            return cls._estimar_sem_historico(fonte, forecast)
        
        # Calcular previsão com base no histórico e dados meteorológicos
        previsoes = cls._calcular_previsao(fonte, df_producao, forecast)
        
        # Salvar previsões
        cls._salvar_previsao(fonte_id, previsoes)
        
        return previsoes
    
    @classmethod
    def _obter_historico_producao(cls, fonte_id):
        """Obtém o histórico de produção da fonte"""
        try:
            # Usar o controller de dashboard para obter os dados
            df = DashboardController.get_dados_fonte(fonte_id)
            
            if df is None or df.empty:
                return None
                
            # Agrupar por data para obter produção diária
            df['data'] = pd.to_datetime(df['data_hora']).dt.date
            producao_diaria = df.groupby('data')['energia_kwh'].sum().reset_index()
            
            # Ordenar por data
            producao_diaria = producao_diaria.sort_values('data')
            
            return producao_diaria
        except Exception as e:
            print(f"Erro ao obter histórico de produção: {str(e)}")
            return None
    
    @classmethod
    def _estimar_sem_historico(cls, fonte, forecast):
        """
        Estima a geração quando não há histórico disponível
        Usa a capacidade nominal da fonte e eficiência estimada
        """
        previsoes = []
        
        # Capacidade nominal em kWp
        try:
            capacidade = float(fonte.capacidade)
        except (ValueError, TypeError):
            capacidade = 5.0  # Valor padrão se não for possível converter
        
        # Eficiência média diária (horas de sol equivalentes a plena carga)
        eficiencia_base = 4.2  # Média de horas de sol pleno no Brasil
        
        for day_forecast in forecast:
            # Calcular fator climático
            fator_climatico = cls._calcular_fator_climatico(day_forecast)
            
            # Estimar produção com base na capacidade e condições climáticas
            energia_estimada = round(capacidade * eficiencia_base * fator_climatico, 2)
            
            # Criar registro de previsão
            previsao = {
                **day_forecast,
                'energia_estimada': energia_estimada,
                'fator_climatico': round(fator_climatico * 100, 1),
                'mensagem': cls._gerar_mensagem(energia_estimada, fator_climatico, capacidade)
            }
            
            previsoes.append(previsao)
            
        return previsoes
    
    @classmethod
    def _calcular_previsao(cls, fonte, df_historico, forecast):
        """Calcula a previsão com base no histórico e dados meteorológicos"""
        previsoes = []
        
        # Calcular média histórica de produção
        media_historica = df_historico['energia_kwh'].mean()
        
        # Capacidade nominal em kWp
        try:
            capacidade = float(fonte.capacidade)
        except (ValueError, TypeError):
            capacidade = 5.0  # Valor padrão se não for possível converter
        
        for day_forecast in forecast:
            # Calcular fator climático
            fator_climatico = cls._calcular_fator_climatico(day_forecast)
            
            # Estimar produção com base no histórico e condições climáticas
            energia_estimada = round(media_historica * fator_climatico, 2)
            
            # Comparar com produção teórica baseada na capacidade
            producao_teorica = capacidade * 4.2 * fator_climatico  # 4.2h de sol pleno
            
            # Usar o menor valor entre histórico ajustado e teórico para ser conservador
            energia_estimada = min(energia_estimada, producao_teorica)
            
            # Criar registro de previsão
            previsao = {
                **day_forecast,
                'energia_estimada': energia_estimada,
                'fator_climatico': round(fator_climatico * 100, 1),
                'mensagem': cls._gerar_mensagem(energia_estimada, fator_climatico, media_historica)
            }
            
            previsoes.append(previsao)
            
        return previsoes
    
    @classmethod
    def _calcular_fator_climatico(cls, weather_data):
        """
        Calcula o fator de ajuste baseado nas condições climáticas
        Retorna um valor entre 0 (sem geração) e 1 (condições ideais)
        """
        # Normalizar valores
        uvi_norm = min(weather_data['uvi'] / cls.IDEAL_CONDITIONS['uvi'], 1.0)
        clouds_norm = 1.0 - (weather_data['clouds'] / 100)  # Inverter: menos nuvens = melhor
        rain_norm = 1.0 if weather_data['rain'] == 0 else max(0.0, 1.0 - (weather_data['rain'] / 25.0))
        pop_norm = 1.0 - (weather_data['pop'] / 100)
        daylight_norm = min(weather_data['daylight_hours'] / cls.IDEAL_CONDITIONS['daylight_hours'], 1.0)
        
        # Aplicar pesos
        fator = (
            cls.WEATHER_WEIGHTS['uvi'] * uvi_norm +
            cls.WEATHER_WEIGHTS['clouds'] * clouds_norm +
            cls.WEATHER_WEIGHTS['rain'] * rain_norm +
            cls.WEATHER_WEIGHTS['pop'] * pop_norm +
            cls.WEATHER_WEIGHTS['daylight_hours'] * daylight_norm
        )
        
        # Garantir que o fator esteja entre 0 e 1
        return max(0.0, min(1.0, fator))
    
    @classmethod
    def _gerar_mensagem(cls, energia_estimada, fator_climatico, referencia):
        """Gera uma mensagem com base na previsão de geração"""
        if fator_climatico >= 0.8:
            return f"Ótimas condições para geração solar! Aproveite para usar aparelhos de alto consumo."
        elif fator_climatico >= 0.6:
            return f"Boas condições para geração solar. Produção dentro do esperado."
        elif fator_climatico >= 0.4:
            return f"Condições moderadas para geração solar. Considere reduzir o uso de aparelhos de alto consumo."
        else:
            return f"Condições desfavoráveis para geração solar. Recomenda-se economizar energia."
    
    @classmethod
    def _salvar_previsao(cls, fonte_id, previsoes):
        """Salva a previsão em um arquivo JSON"""
        try:
            # Preparar dados para salvar
            dados = {
                'fonte_id': fonte_id,
                'data_previsao': datetime.now().isoformat(),
                'previsoes': previsoes
            }
            
            # Salvar arquivo
            arquivo = os.path.join(cls.FORECAST_DIR, f'previsao_fonte_{fonte_id}.json')
            with open(arquivo, 'w') as f:
                json.dump(dados, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Erro ao salvar previsão: {str(e)}")
            return False
    
    @classmethod
    def get_saved_forecast(cls, fonte_id):
        """
        Obtém a previsão salva para uma fonte
        
        Args:
            fonte_id (int): ID da fonte de energia
            
        Returns:
            dict: Dados de previsão ou None se não houver previsão salva
        """
        arquivo = os.path.join(cls.FORECAST_DIR, f'previsao_fonte_{fonte_id}.json')
        
        if not os.path.exists(arquivo):
            return None
            
        try:
            with open(arquivo, 'r') as f:
                dados = json.load(f)
                
            # Verificar se a previsão não está desatualizada (máx. 12h)
            data_previsao = datetime.fromisoformat(dados['data_previsao'])
            agora = datetime.now()
            
            if (agora - data_previsao).total_seconds() > 12 * 3600:
                # Previsão desatualizada, gerar nova
                return None
                
            return dados
        except Exception as e:
            print(f"Erro ao ler previsão salva: {str(e)}")
            return None
            
    @classmethod
    def clear_forecast(cls, fonte_id):
        """
        Remove uma previsão salva para forçar a geração de uma nova
        
        Args:
            fonte_id (int): ID da fonte de energia
            
        Returns:
            bool: True se a previsão foi removida ou não existia, False se houve erro
        """
        try:
            arquivo = os.path.join(cls.FORECAST_DIR, f'previsao_fonte_{fonte_id}.json')
            
            if os.path.exists(arquivo):
                os.remove(arquivo)
                print(f"Previsão para fonte {fonte_id} removida.")
            
            return True
        except Exception as e:
            print(f"Erro ao remover previsão: {str(e)}")
            return False
    
    @classmethod
    def _generate_simulated_forecast(cls, fonte, days=5):
        """
        Gera previsões simuladas quando a API de previsão do tempo falha
        
        Args:
            fonte: Objeto FonteEnergia
            days: Número de dias para previsão
            
        Returns:
            list: Lista com previsões simuladas
        """
        print("Gerando previsões simuladas...")
        previsoes = []
        today = datetime.now()
        
        # Condições meteorológicas típicas
        weather_conditions = [
            {"id": 800, "main": "Clear", "description": "céu limpo", "icon": "01d"},
            {"id": 801, "main": "Clouds", "description": "algumas nuvens", "icon": "02d"},
            {"id": 802, "main": "Clouds", "description": "nuvens dispersas", "icon": "03d"},
            {"id": 803, "main": "Clouds", "description": "nuvens quebradas", "icon": "04d"},
            {"id": 500, "main": "Rain", "description": "chuva leve", "icon": "10d"}
        ]
        
        # Capacidade nominal em kWp
        try:
            capacidade = float(fonte.capacidade)
        except (ValueError, TypeError):
            capacidade = 5.0  # Valor padrão se não for possível converter
        
        # Gerar previsão para cada dia
        for i in range(days):
            date = today + timedelta(days=i)
            # Escolher condição meteorológica aleatória com tendência para dias ensolarados
            weather_idx = min(int(np.random.exponential(1)), len(weather_conditions) - 1)
            weather = weather_conditions[weather_idx]
            
            # Temperatura entre 22 e 32 graus
            temp_max = round(26 + np.random.uniform(-4, 6), 1)
            temp_min = round(temp_max - np.random.uniform(3, 8), 1)
            
            # Geração baseada na condição do tempo
            fator_nuvens = 1.0 if weather["main"] == "Clear" else (0.7 if weather["main"] == "Clouds" else 0.4)
            clouds = 0 if weather["main"] == "Clear" else (np.random.randint(25, 60) if weather["main"] == "Clouds" else np.random.randint(60, 90))
            
            # Probabilidade de chuva
            pop = 0 if weather["main"] == "Clear" else (20 if weather["main"] == "Clouds" else 70)
            
            # Horas de luz solar (12h em média)
            daylight_hours = round(12 + np.random.uniform(-1, 1), 1)
            
            # Índice UV (mais alto em dias claros)
            uvi = 9 if weather["main"] == "Clear" else (6 if weather["main"] == "Clouds" else 3)
            
            # Calcular energia estimada
            energia_diaria = capacidade * 4.2 * fator_nuvens  # 4.2h é a média de horas de sol pleno
            energia_estimada = round(energia_diaria * (1 + np.random.uniform(-0.1, 0.1)), 2)  # Variação de +-10%
            
            # Criar previsão para o dia
            forecast_day = {
                "date": date.strftime("%Y-%m-%d"),
                "date_formatted": date.strftime("%d/%m/%Y"),
                "weekday": date.strftime("%A"),
                "weekday_short": date.strftime("%a"),
                "temp_max": temp_max,
                "temp_min": temp_min,
                "clouds": clouds,
                "weather_id": weather["id"],
                "weather_main": weather["main"],
                "weather_description": weather["description"],
                "weather_icon": weather["icon"],
                "rain": 0 if weather["main"] != "Rain" else np.random.uniform(0.5, 5.0),
                "uvi": uvi,
                "pop": pop,
                "daylight_hours": daylight_hours,
                "humidity": np.random.randint(40, 80),
                "icon_url": f"https://openweathermap.org/img/wn/{weather['icon']}@2x.png",
                "energia_estimada": energia_estimada,
                "fator_climatico": round(fator_nuvens * 100, 1),
                "mensagem": cls._gerar_mensagem(energia_estimada, fator_nuvens, capacidade),
                "source": "simulado"  # Identificador para dados simulados
            }
            
            previsoes.append(forecast_day)
            
        return previsoes 