import os
import sys
import subprocess
import re

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
RUN_ID = os.getenv("RUN_ID")

if not GITHUB_TOKEN or not RUN_ID:
    print("❌ Faltan variables de entorno necesarias (GITHUB_TOKEN, RUN_ID).")
    sys.exit(1)

def get_build_logs():
    """Descarga los logs del workflow fallido desde la API de GitHub."""
    import requests
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/actions/runs/{RUN_ID}/logs"
    
    print(f"📥 Descargando logs para Run ID {RUN_ID}...")
    try:
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
        if response.status_code != 200:
            print(f"⚠️ No se pudieron obtener logs vía API ({response.status_code}), usando análisis heurístico estándar.")
            return ""
        return response.text
    except Exception as e:
        print(f"⚠️ Excepción al descargar logs: {e}")
        return ""

def apply_deterministic_fixes(error_logs):
    """Aplica correcciones deterministas basadas en heurísticas (Sin depender de cuotas de IA)."""
    print("🛡️ Aplicando motor heurístico determinista para errores comunes de Gradle y Android...")
    fixed = False

    # 1. Asegurar gradle.properties con AndroidX y Jetifier
    props_path = "android_app/gradle.properties"
    os.makedirs(os.path.dirname(props_path), exist_ok=True)
    prop_content = ""
    if os.path.exists(props_path):
        with open(props_path, "r", encoding="utf-8") as f:
            prop_content = f.read()
    
    updates = []
    if "android.useAndroidX=true" not in prop_content:
        updates.append("android.useAndroidX=true")
    if "android.enableJetifier=true" not in prop_content:
        updates.append("android.enableJetifier=true")
    if "org.gradle.jvmargs" not in prop_content:
        updates.append("org.gradle.jvmargs=-Xmx2048M -Dfile.encoding=UTF-8")

    if updates:
        with open(props_path, "a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(updates) + "\n")
        print(f"✅ Añadidas propiedades de Gradle: {updates}")
        fixed = True

    # 2. Verificar repositorios en build.gradle.kts o settings.gradle.kts si hay errores de resolución de dependencias
    if "Could not resolve" in error_logs or "SDK" in error_logs or not error_logs:
        print("ℹ️ Verificando configuración de repositorios y SDKs...")
        # Asegurarnos de que gradlew tenga permisos de ejecución
        gradlew_path = "android_app/gradlew"
        if os.path.exists(gradlew_path):
            os.chmod(gradlew_path, 0o755)
            fixed = True

    return fixed

def try_optional_ai_analysis(error_logs):
    """Usa IA de forma opcional y tolerante a fallos (con fallback si hay cuota agotada)."""
    if not GOOGLE_API_KEY or not error_logs:
        return
    try:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"Analiza este error de Gradle y da una solución breve:\n{error_logs[-2000:]}"
        response = model.generate_content(prompt)
        print(f"💡 Sugerencia de IA (Opcional):\n{response.text}")
    except Exception as e:
        print(f"ℹ️ IA omitida o cuota agotada (comportamiento esperado sin bloquear el pipeline): {e}")

def commit_and_push():
    """Realiza commit y push automático a la rama main."""
    print("🚀 Realizando commit y push automático de la corrección heurística...")
    subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions Auto-Fix"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
    
    subprocess.run(["git", "add", "."], check=True)
    
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
    if not status.stdout.strip():
        print("ℹ️ No hay cambios nuevos que commitear.")
        return

    subprocess.run(["git", "commit", "-m", "fix(autofix): deterministic heuristic correction applied"], check=True)
    
    remote_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPOSITORY}.git"
    subprocess.run(["git", "push", remote_url, "HEAD:main", "--force"], check=True)
    print("✅ Push completado con éxito.")

if __name__ == "__main__":
    logs = get_build_logs()
    apply_deterministic_fixes(logs)
    try_optional_ai_analysis(logs)
    commit_and_push()
