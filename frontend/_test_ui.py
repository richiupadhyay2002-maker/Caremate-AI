import http.client

conn = http.client.HTTPConnection("127.0.0.1", 3001, timeout=30)
conn.request("GET", "/")
resp = conn.getresponse()
body = resp.read().decode()
print("STATUS:", resp.status)
print("CONTENT-TYPE:", resp.getheader("content-type"))
print("BODY LENGTH:", len(body))
print("FIRST 300 CHARS:", body[:300])
conn.close()
