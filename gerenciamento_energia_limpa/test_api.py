import os
import requests
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def test_api():
    api_key = os.environ.get("WEATHER_API_KEY", "")
    
    if not api_key:
        print("ERRO: Chave de API não encontrada no arquivo .env")
        return False
    
    print(f"Chave carregada: {api_key[:5]}{'*' * 10} (mostrando primeiros 5 caracteres)")
    
    # Testar a chave em uma requisição simples
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": -20.8477,
        "lon": -41.1150,
        "appid": api_key
    }
    
    try:
        print(f"Fazendo requisição para {url}")
        response = requests.get(url, params=params)
        
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            print("API funcionando corretamente!")
            data = response.json()
            print(f"Temperatura atual em Cachoeiro de Itapemirim: {data['main']['temp']-273.15:.1f}°C")
            print(f"Condições: {data['weather'][0]['description']}")
            return True
        else:
            print(f"Erro na API: {response.text}")
            return False
    except Exception as e:
        print(f"Erro ao fazer requisição: {e}")
        return False

if __name__ == "__main__":
    print("=== TESTE DA API OPENWEATHER ===")
    test_api() 