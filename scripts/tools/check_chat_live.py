import json
import urllib.request

payload = json.dumps({"message": "Reply with only the word OK"}).encode("utf-8")
request = urllib.request.Request(
    "http://127.0.0.1:8000/chat",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=120) as response:
    result = json.load(response)
reply = result.get("response", "")
print(f"CHAT_RESPONSE_LENGTH={len(reply)}")
print(f"CHAT_RESPONSE={reply}")