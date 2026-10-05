import http.client
import json

API = "127.0.0.1"
PORT = 8080
ORIGIN = "http://localhost:3001"

def api_request(method, path, body=None, token=None):
    conn = http.client.HTTPConnection(API, PORT, timeout=15)
    headers = {"Content-Type": "application/json", "Origin": ORIGIN}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body) if body else None
    conn.request(method, path, body=data, headers=headers)
    resp = conn.getresponse()
    body_str = resp.read().decode()
    try:
        result = json.loads(body_str)
    except:
        result = body_str[:200]
    conn.close()
    return resp.status, result

# Test 1: Admin login
print("=== ADMIN LOGIN ===")
status, data = api_request("POST", "/auth/token", {"email": "admin@caremate.ai", "password": "adminpass"})
print(f"Status: {status}")
if status == 200:
    admin_token = data["access_token"]
    print(f"Token: {admin_token[:30]}...")

    # Get admin info
    s, admin_user = api_request("GET", "/auth/me", token=admin_token)
    print(f"Admin user: {json.dumps(admin_user, indent=2)}")

    # List all patients (admin only)
    s, patients = api_request("GET", "/doctors/me/patients", token=admin_token)
    print(f"Patients: {json.dumps(patients, indent=2)[:300]}")

# Test 2: Doctor login
print("=== DOCTOR LOGIN ===")
status, data = api_request("POST", "/auth/token", {"email": "doctor@caremate.ai", "password": "doctor123"})
print(f"Status: {status}")
if status == 200:
    doc_token = data["access_token"]
    print(f"Token: {doc_token[:30]}...")

    # Get doctor info
    s, doc_user = api_request("GET", "/auth/me", token=doc_token)
    print(f"Doctor user: {json.dumps(doc_user, indent=2)}")

    # List doctor patients
    s, docs = api_request("GET", "/doctors/me/patients", token=doc_token)
    print(f"Doctor patients: {json.dumps(docs, indent=2)[:300]}")

# Test 3: Patient login
print("=== PATIENT LOGIN ===")
status, data = api_request("POST", "/auth/token", {"email": "patient@caremate.ai", "password": "patient123"})
print(f"Status: {status}")
if status == 200:
    pat_token = data["access_token"]
    print(f"Token: {pat_token[:30]}...")

    # Get patient info
    s, pat_user = api_request("GET", "/auth/me", token=pat_token)
    print(f"Patient user: {json.dumps(pat_user, indent=2)}")

    # Get patient context
    s, ctx = api_request("GET", "/patients/P0001/context", token=pat_token)
    print(f"Patient context: {json.dumps(ctx, indent=2)[:400]}")

# Test 4: Test ask endpoint
print("=== PATIENT ASK ===")
if status == 200:
    s, resp = api_request("POST", "/patients/P0001/ask", {"query": "What medications am I taking?"}, token=pat_token)
    print(f"Ask status: {s}")
    print(f"Answer: {json.dumps(resp, indent=2)[:500]}")

# Test 5: Test CORS headers
print("=== CORS CHECK ===")
s, _ = api_request("GET", "/health")
print(f"Health check: status={s}")

print("=== ALL TESTS COMPLETE ===")
