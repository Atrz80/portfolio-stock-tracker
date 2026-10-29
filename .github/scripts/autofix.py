import os
import sys
import subprocess
import requests
import google.generativeai as genai

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
RUN_ID = os.getenv("RUN_ID")

if not GOOGLE_API_KEY or not GITHUB_TOKEN or not RUN_ID:
    print("❌ Faltan variables de entorno necesarias (GITHUB_TOKEN, GOOGLE_API_KEY, RUN_ID).")
    sys.exit(1)

genai.configure(api_key=GOOGLE_API_KEY)

def get_build_logs():
    """Descarga los logs del workflow fallido desde la API de GitHub."""
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/actions/runs/{RUN_ID}/logs"
    
    print(f"📥 Descargando logs para Run ID {RUN_ID}...")
    response = requests.get(url, headers=headers, allow_redirects=True)
    if response.status_code != 200:
        print(f"❌ Error al obtener logs: {response.status_code} - {response.text}")
        return ""
    return response.text

def analyze_and_fix(error_logs):
    """Consulta a Gemini (gemini-1.5-flash / gemini-3.5-flash-lite) para proponer correcciones o aplicar heurísticas."""
    print("🤖 Consultando a Gemini para diagnóstico y corrección automática...")
    
    prompt = f"""
    Eres un Ingeniero DevSecOps y experto en Android. El pipeline de CI/CD de GitHub Actions ha fallado al compilar una app con Gradle.
    Aquí tienes las líneas de error extraídas del log:
    
    {error_logs[-4000:]}
    
    Analiza el error. Si el error es sobre versiones de Gradle incompatibles, HasConvention, plugins obsoletos, o dependencias faltantes, provee una solución clara o ajusta los archivos si es necesario. Asegúrate de que gradle.properties tenga android.useAndroidX=true.
    """
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        print(f"💡 Diagnóstico de Gemini:\n{response.text}")
    except Exception as e:
        print(f"⚠️ Error al consultar Gemini API: {e}")

def apply_safeguards():
    """Aplica salvaguardas robustas de Gradle y AndroidX automáticamente."""
    print("🛡️ Aplicando salvaguardas estándar de Gradle y AndroidX...")
    
    # Asegurar gradle.properties con AndroidX
    props_path = "android_app/gradle.properties"
    os.makedirs(os.path.dirname(props_path), exist_ok=True)
    with open(props_path, "w", encoding="utf-8") as f:
        f.write("org.gradle.jvmargs=-Xmx2048M -Dfile.encoding=UTF-8\n")
        f.write("android.useAndroidX=true\n")
        f.write("android.enableJetifier=true\n")

def commit_and_push():
    """Realiza commit y push automático a la rama main."""
    print("🚀 Realizando commit y push automático de la corrección...")
    subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions Bot"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
    
    subprocess.run(["git", "add", "."], check=True)
    
    # Verificar si hay cambios
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
    if not status.stdout.strip():
        print("ℹ️ No hay cambios nuevos que commitear.")
        return

    subprocess.run(["git", "commit", "-m", "fix(autofix): auto-correction applied by Gemini AI & DevSecOps bot"], check=True)
    
    remote_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPOSITORY}.git"
    subprocess.run(["git", "push", remote_url, "HEAD:main", "--force"], check=True)
    print("✅ Push completado con éxito.")

if __name__ == "__main__":
    logs = get_build_logs()
    analyze_and_fix(logs)
    apply_safeguards()
    commit_and_push()
