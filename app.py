import os
import chromadb
from google import generativeai as genai
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# 1. Configurar SDK de Google Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("⚠️ No se encontró GOOGLE_API_KEY en las variables de entorno.")

genai.configure(api_key=api_key)

def consultar_gemini(prompt: str):
    """Realiza una consulta al modelo Gemini 1.5 Flash."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error al consultar Gemini: {e}"

def probar_chromadb():
    """Conecta con ChromaDB y realiza una prueba básica de almacenamiento vectorial."""
    try:
        host = os.getenv("CHROMA_HOST", "localhost")
        port = int(os.getenv("CHROMA_PORT", "8000"))
        
        client = chromadb.HttpClient(host=host, port=port)
        
        # Crear o obtener una colección de prueba
        collection = client.get_or_create_collection(name="agencia_memoria")
        
        # Agregar un documento de prueba
        collection.upsert(
            documents=["El entorno de desarrollo está optimizado y funcionando."],
            metadatas=[{"source": "setup_test"}],
            ids=["doc1"]
        )
        
        # Consultar
        results = collection.query(
            query_texts=["¿Cómo está el entorno?"],
            n_results=1
        )
        return f"✅ ChromaDB conectado con éxito. Resultado: {results['documents']}"
    except Exception as e:
        return f"❌ Error al conectar con ChromaDB: {e}"

if __name__ == "__main__":
    print("🚀 Iniciando Agencia IA - Entorno Optimizado...\n")
    
    # Prueba de ChromaDB
    print(probar_chromadb())
    
    # Prueba de Gemini
    prompt_prueba = "Preséntate brevemente como tu asistente de IA optimizado para Python y Docker."
    print(f"\n🤖 Prompt enviado a Gemini: '{prompt_prueba}'")
    respuesta = consultar_gemini(prompt_prueba)
    print(f"\n💬 Respuesta de Gemini:\n{respuesta}")
