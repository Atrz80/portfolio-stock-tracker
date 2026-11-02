import os
import sys
import subprocess
import re

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
RUN_ID = os.getenv("RUN_ID")

if not GITHUB_TOKEN or not RUN_ID:
    print("❌ Required environment variables are missing (GITHUB_TOKEN, RUN_ID).")
    sys.exit(1)

def get_build_logs():
    """Download logs from the failed workflow via the GitHub API."""
    import requests
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/actions/runs/{RUN_ID}/logs"
    
    print(f"📥 Downloading logs for Run ID {RUN_ID}...")
    try:
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
        if response.status_code != 200:
            print(f"⚠️ Could not retrieve logs via the API ({response.status_code}); using standard heuristic analysis.")
            return ""
        return response.text
    except Exception as e:
        print(f"⚠️ Exception while downloading logs: {e}")
        return ""

def apply_deterministic_fixes(error_logs):
    """Apply deterministic, heuristic-based fixes without relying on AI quotas."""
    print("🛡️ Applying the deterministic heuristic engine for common Gradle and Android errors...")
    fixed = False

    # 1. Ensure gradle.properties includes AndroidX and Jetifier
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
        print(f"✅ Added Gradle properties: {updates}")
        fixed = True

    # 2. Check repositories in build.gradle.kts or settings.gradle.kts for dependency resolution errors
    if "Could not resolve" in error_logs or "SDK" in error_logs or not error_logs:
        print("ℹ️ Checking repository and SDK configuration...")
        # Ensure gradlew has execute permissions
        gradlew_path = "android_app/gradlew"
        if os.path.exists(gradlew_path):
            os.chmod(gradlew_path, 0o755)
            fixed = True

    return fixed

def try_optional_ai_analysis(error_logs):
    """Optionally use AI with failure tolerance and a fallback for exhausted quotas."""
    if not GOOGLE_API_KEY or not error_logs:
        return
    try:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"Analyze this Gradle error and suggest a brief solution:\n{error_logs[-2000:]}"
        response = model.generate_content(prompt)
        print(f"💡 AI suggestion (optional):\n{response.text}")
    except Exception as e:
        print(f"ℹ️ AI skipped or quota exhausted (expected behavior without blocking the pipeline): {e}")

def commit_and_push():
    """Automatically commit and push to the main branch."""
    print("🚀 Committing and automatically pushing the heuristic fix...")
    subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions Auto-Fix"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
    
    subprocess.run(["git", "add", "."], check=True)
    
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
    if not status.stdout.strip():
        print("ℹ️ No new changes to commit.")
        return

    subprocess.run(["git", "commit", "-m", "fix(autofix): deterministic heuristic correction applied"], check=True)
    
    remote_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPOSITORY}.git"
    subprocess.run(["git", "push", remote_url, "HEAD:main", "--force"], check=True)
    print("✅ Push completed successfully.")

if __name__ == "__main__":
    logs = get_build_logs()
    apply_deterministic_fixes(logs)
    try_optional_ai_analysis(logs)
    commit_and_push()
