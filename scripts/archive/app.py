import os
import chromadb
from google import generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 1. Configure the Google Gemini SDK
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("⚠️ GOOGLE_API_KEY was not found in the environment variables.")

genai.configure(api_key=api_key)

def consultar_gemini(prompt: str):
    """Send a request to the Gemini 1.5 Flash model."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error querying Gemini: {e}"

def probar_chromadb():
    """Connect to ChromaDB and run a basic vector storage test."""
    try:
        host = os.getenv("CHROMA_HOST", "localhost")
        port = int(os.getenv("CHROMA_PORT", "8000"))
        
        client = chromadb.HttpClient(host=host, port=port)
        
        # Create or retrieve a test collection
        collection = client.get_or_create_collection(name="agencia_memoria")
        
        # Add a test document
        collection.upsert(
            documents=["The development environment is optimized and running."],
            metadatas=[{"source": "setup_test"}],
            ids=["doc1"]
        )
        
        # Query
        results = collection.query(
            query_texts=["How is the environment?"],
            n_results=1
        )
        return f"✅ ChromaDB connected successfully. Result: {results['documents']}"
    except Exception as e:
        return f"❌ Error connecting to ChromaDB: {e}"

if __name__ == "__main__":
    print("🚀 Starting AI Agency - Optimized Environment...\n")
    
    # ChromaDB test
    print(probar_chromadb())
    
    # Gemini test
    prompt_prueba = "Briefly introduce yourself as your AI assistant optimized for Python and Docker."
    print(f"\n🤖 Prompt sent to Gemini: '{prompt_prueba}'")
    respuesta = consultar_gemini(prompt_prueba)
    print(f"\n💬 Gemini response:\n{respuesta}")
