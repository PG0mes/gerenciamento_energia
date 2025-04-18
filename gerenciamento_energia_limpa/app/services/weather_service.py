import os
import requests
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Verificar se a chave está sendo carregada
api_key = os.environ.get("WEATHER_API_KEY", "")
print(f"Chave de API carregada: {api_key[:5]}{'*' * 10} (primeiros 5 caracteres)")

class WeatherService:
    """Serviço para obtenção de dados meteorológicos usando a API OpenWeather"""
    
    BASE_URL = "https://api.openweathermap.org/data/2.5"
    API_KEY = os.environ.get("WEATHER_API_KEY", "")  # Obter chave da API das variáveis de ambiente
    
    # Coordenadas padrão para cidades conhecidas no sistema
    DEFAULT_COORDINATES = {
        "São Paulo": (-23.5505, -46.6333),
        "Cachoeiro de Itapemirim": (-20.8477, -41.1150),
        "Cachoeiro de Itapemirim - ES": (-20.8477, -41.1150),
        "Aeroporto, Cachoeiro de Itapemirim - ES": (-20.8477, -41.1150)
    }
    
    @classmethod
    def get_forecast(cls, lat, lon, days=5):
        """
        Obtém previsão meteorológica para uma localização específica
        
        Args:
            lat (float): Latitude da localização
            lon (float): Longitude da localização
            days (int): Número de dias para previsão (máx. 7 para API gratuita)
            
        Returns:
            dict: Dados de previsão formatados ou None em caso de erro
        """
        if not cls.API_KEY:
            print("Chave de API do OpenWeather não configurada")
            return None
            
        # Limitar o número de dias a 7 (limitação da API gratuita)
        days = min(days, 7)
        
        try:
            # Mostrar a URL que será usada (sem a chave)
            url = f"{cls.BASE_URL}/onecall"
            print(f"Fazendo requisição para: {url}")
            print(f"Parâmetros: lat={lat}, lon={lon}, units=metric, exclui minutely,hourly,alerts,current")
            
            # Fazer a chamada à API
            response = requests.get(
                url,
                params={
                    "lat": lat,
                    "lon": lon,
                    "exclude": "minutely,hourly,alerts,current",
                    "units": "metric",
                    "appid": cls.API_KEY
                },
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"Erro ao obter previsão: {response.status_code} - {response.text}")
                print(f"URL completa (sem chave): {response.url.split('&appid=')[0]}")
                return None
                
            # Extrair e formatar dados de previsão
            data = response.json()
            forecast = cls._format_forecast_data(data, days)
            
            return forecast
            
        except Exception as e:
            print(f"Erro ao acessar API de previsão do tempo: {str(e)}")
            return None
    
    @classmethod
    def _format_forecast_data(cls, data, days):
        """Formata os dados de previsão da API"""
        if not data or "daily" not in data:
            return None
            
        daily_data = data["daily"][:days]
        forecast = []
        
        for day_data in daily_data:
            date = datetime.fromtimestamp(day_data["dt"])
            
            # Calcular horas de sol
            sunrise = datetime.fromtimestamp(day_data["sunrise"])
            sunset = datetime.fromtimestamp(day_data["sunset"])
            daylight_hours = (sunset - sunrise).total_seconds() / 3600
            
            # Obter informações relevantes para previsão de geração
            weather_data = {
                "date": date.strftime("%Y-%m-%d"),
                "date_formatted": date.strftime("%d/%m/%Y"),
                "weekday": date.strftime("%A"),
                "weekday_short": date.strftime("%a"),
                "temp_max": round(day_data["temp"]["max"], 1),
                "temp_min": round(day_data["temp"]["min"], 1),
                "clouds": day_data["clouds"],  # Cobertura de nuvens (%)
                "weather_id": day_data["weather"][0]["id"],
                "weather_main": day_data["weather"][0]["main"],
                "weather_description": day_data["weather"][0]["description"],
                "weather_icon": day_data["weather"][0]["icon"],
                "rain": day_data.get("rain", 0),  # Precipitação (mm)
                "uvi": day_data["uvi"],  # Índice UV
                "pop": day_data.get("pop", 0) * 100,  # Probabilidade de precipitação (%)
                "daylight_hours": round(daylight_hours, 1),  # Horas de luz
                "humidity": day_data["humidity"],  # Umidade (%)
                "icon_url": f"https://openweathermap.org/img/wn/{day_data['weather'][0]['icon']}@2x.png"
            }
            
            forecast.append(weather_data)
            
        return forecast
    
    @classmethod
    def get_location_coords(cls, location_string):
        """
        Converte um endereço em coordenadas geográficas (geocoding)
        
        Args:
            location_string (str): Endereço a ser convertido
            
        Returns:
            tuple: (latitude, longitude) ou None em caso de erro
        """
        # Verificar se temos coordenadas padrão para esta localização
        for key, coords in cls.DEFAULT_COORDINATES.items():
            if key in location_string:
                print(f"Usando coordenadas padrão para {key}: {coords}")
                return coords
                
        if not cls.API_KEY:
            print("Chave de API do OpenWeather não configurada")
            return None
            
        try:
            # Fazer a chamada à API de geocoding
            response = requests.get(
                "http://api.openweathermap.org/geo/1.0/direct",
                params={
                    "q": location_string,
                    "limit": 1,
                    "appid": cls.API_KEY
                },
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"Erro ao fazer geocoding: {response.status_code} - {response.text}")
                # Verificar novamente por localização aproximada
                for key, coords in cls.DEFAULT_COORDINATES.items():
                    if key.lower() in location_string.lower():
                        print(f"Usando coordenadas padrão para {key} (verificação secundária): {coords}")
                        return coords
                return None
                
            data = response.json()
            
            if not data or len(data) == 0:
                print(f"Nenhum resultado encontrado para o endereço: {location_string}")
                # Verificar novamente por localização aproximada
                for key, coords in cls.DEFAULT_COORDINATES.items():
                    if key.lower() in location_string.lower():
                        print(f"Usando coordenadas padrão para {key} (verificação secundária): {coords}")
                        return coords
                return None
                
            location = data[0]
            return (location["lat"], location["lon"])
            
        except Exception as e:
            print(f"Erro ao realizar geocoding: {str(e)}")
            # Verificar novamente por localização aproximada
            for key, coords in cls.DEFAULT_COORDINATES.items():
                if key.lower() in location_string.lower():
                    print(f"Usando coordenadas padrão para {key} (após exceção): {coords}")
                    return coords
            return None
    
    @classmethod
    def test_api_key(cls):
        """Testa a chave de API para verificar se está válida"""
        if not cls.API_KEY:
            return {
                "success": False,
                "message": "Chave de API não configurada. Configure a variável de ambiente WEATHER_API_KEY."
            }
            
        try:
            # Testar com coordenadas conhecidas (São Paulo, Brasil)
            response = requests.get(
                f"{cls.BASE_URL}/weather",
                params={
                    "lat": -23.5505,
                    "lon": -46.6333,
                    "appid": cls.API_KEY
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Chave de API válida"
                }
            else:
                return {
                    "success": False,
                    "message": f"Erro na validação da chave: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False, 
                "message": f"Erro ao testar a chave de API: {str(e)}"
            }
            
    @classmethod
    def get_weather_icon_class(cls, weather_id):
        """
        Retorna a classe de ícone Font Awesome correspondente ao código de clima
        
        Args:
            weather_id (int): Código de clima do OpenWeather
            
        Returns:
            str: Classe CSS do ícone Font Awesome
        """
        # Mapeamento dos códigos de clima do OpenWeather para ícones do Font Awesome
        icon_map = {
            # Tempestade
            200: "fa-bolt",  # trovoadas com chuva leve
            201: "fa-bolt",  # trovoadas com chuva
            202: "fa-bolt",  # trovoadas com chuva forte
            210: "fa-bolt",  # trovoadas leves
            211: "fa-bolt",  # trovoadas
            212: "fa-bolt",  # trovoadas fortes
            221: "fa-bolt",  # trovoadas irregulares
            230: "fa-bolt",  # trovoada com garoa leve
            231: "fa-bolt",  # trovoada com garoa
            232: "fa-bolt",  # trovoada com garoa forte
            
            # Garoa
            300: "fa-cloud-rain",  # garoa leve
            301: "fa-cloud-rain",  # garoa
            302: "fa-cloud-rain",  # garoa forte
            310: "fa-cloud-rain",  # chuva leve
            311: "fa-cloud-rain",  # chuva
            312: "fa-cloud-rain",  # chuva forte
            313: "fa-cloud-rain",  # chuva e garoa
            314: "fa-cloud-rain",  # chuva e garoa forte
            321: "fa-cloud-rain",  # garoa forte
            
            # Chuva
            500: "fa-cloud-showers-heavy",  # chuva leve
            501: "fa-cloud-showers-heavy",  # chuva moderada
            502: "fa-cloud-showers-heavy",  # chuva forte
            503: "fa-cloud-showers-heavy",  # chuva muito forte
            504: "fa-cloud-showers-heavy",  # chuva extrema
            511: "fa-snowflake",  # chuva gelada
            520: "fa-cloud-showers-heavy",  # chuva com intensidade leve
            521: "fa-cloud-showers-heavy",  # chuva
            522: "fa-cloud-showers-heavy",  # chuva com intensidade forte
            531: "fa-cloud-showers-heavy",  # chuva irregular
            
            # Neve
            600: "fa-snowflake",  # neve leve
            601: "fa-snowflake",  # neve
            602: "fa-snowflake",  # neve forte
            611: "fa-snowflake",  # aguaneve
            612: "fa-snowflake",  # aguaneve leve
            613: "fa-snowflake",  # aguaneve forte
            615: "fa-snowflake",  # chuva leve e neve
            616: "fa-snowflake",  # chuva e neve
            620: "fa-snowflake",  # neve leve
            621: "fa-snowflake",  # neve
            622: "fa-snowflake",  # neve forte
            
            # Atmosfera
            701: "fa-smog",  # névoa
            711: "fa-smog",  # fumaça
            721: "fa-smog",  # neblina
            731: "fa-smog",  # redemoinhos de areia/poeira
            741: "fa-smog",  # névoa
            751: "fa-smog",  # areia
            761: "fa-smog",  # poeira
            762: "fa-smog",  # cinza vulcânica
            771: "fa-wind",  # rajadas
            781: "fa-tornado",  # tornado
            
            # Céu limpo e nuvens
            800: "fa-sun",  # céu limpo
            801: "fa-cloud-sun",  # algumas nuvens (11-25%)
            802: "fa-cloud-sun",  # nuvens dispersas (25-50%)
            803: "fa-cloud",  # nuvens quebradas (51-84%)
            804: "fa-cloud",  # céu nublado (85-100%)
        }
        
        return icon_map.get(weather_id, "fa-cloud")  # Padrão se o código não for encontrado 