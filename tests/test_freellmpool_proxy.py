import os
from openai import OpenAI

def test_proxy():
    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:8080/v1")
    api_key = os.getenv("OPENAI_API_KEY", "local")
    
    print(f"Conectando a Freellmpool Proxy en: {base_url}")
    client = OpenAI(base_url=base_url, api_key=api_key)
    
    try:
        models = client.models.list()
        print("Modelos disponibles en Freellmpool:")
        for m in models:
            print(f" - {m.id}")
            
        response = client.chat.completions.create(
            model="auto",
            messages=[{"role": "user", "content": "Hola, responde brevemente con 'OK' si el proxy funciona."}]
        )
        print("Respuesta del Chat:", response.choices[0].message.content)
        print("Conexion con Freellmpool verificada exitosamente!")
    except Exception as e:
        print(f"Error conectando con Freellmpool proxy: {e}")

if __name__ == "__main__":
    test_proxy()
