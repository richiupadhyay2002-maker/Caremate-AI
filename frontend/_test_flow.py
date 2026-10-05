import http.client
import json

# Step 1: Test login
conn = http.client.HTTPConnection("127.0.0.1", 8080, timeout=15)
login_body = json.dumps({"email": "patient@caremate.ai", "password": "patientpass"})
headers = {"Content-Type": "application/json", "Origin": "http://localhost:3001"}
conn.request("POST", "/auth/token", body=login_body, headers=headers)
resp = conn.getresponse()
token_data = json.loads(resp.read().decode())
token = token_data.get("access_token", "")
print("LOGIN STATUS:", resp.status)
print("TOKEN (first 20 chars):", token[:20], "...")

# Step 2: Use token to get user info
if token:
    headers2 = {"Authorization": f"Bearer {token}", "Origin": "http://localhost:3001"}
    conn.request("GET", "/auth/me", headers=headers2)
    resp2 = conn.getresponse()
    user_data = json.loads(resp2.read().decode())
    print("ME STATUS:", resp2.status)
    print("USER:", json.dumps(user_data, indent=2))

# Step 3: Get patient context
if token:
    conn.request("GET", "/patients/P0001/context", headers=headers2)
    resp3 = conn.getresponse()
    patient_data = json.loads(resp3.read().decode())
    print("CONTEXT STATUS:", resp3.status)
    print("PATIENT NAME:", patient_data.get("full_name"))

conn.close()
