import urllib.request
import json
import os

# 1. Login
login_url = 'http://localhost:8000/api/v1/auth/login'
login_data = json.dumps({'email': 'admin@cyberhub.dev', 'password': 'Admin1234!'}).encode('utf-8')
req = urllib.request.Request(login_url, data=login_data, headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as response:
    auth_resp = json.loads(response.read().decode('utf-8'))
token = auth_resp['access_token']
print('[TEST] Logged in successfully. Token acquired.')

# 2. Create Investigation
case_url = 'http://localhost:8000/api/v1/investigations'
case_data = json.dumps({'title': 'Test CLI Search Investigation', 'description': 'Testing web-search API'}).encode('utf-8')
req_case = urllib.request.Request(case_url, data=case_data, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
with urllib.request.urlopen(req_case) as response:
    case_resp = json.loads(response.read().decode('utf-8'))
case_id = case_resp['id']
print(f'[TEST] Created case ID: {case_id}')

# 3. Read real image file
img_path = '/mnt/c/Users/vaish/Music/cyber security/image copy.png'
with open(img_path, 'rb') as f:
    image_bytes = f.read()

# 4. Upload Reference Image (Multipart)
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = []
body.append(f'--{boundary}'.encode('utf-8'))
body.append(b'Content-Disposition: form-data; name="file"; filename="image.png"')
body.append(b'Content-Type: image/png')
body.append(b'')
body.append(image_bytes)
body.append(f'--{boundary}--'.encode('utf-8'))
body.append(b'')

payload = b'\r\n'.join(body)

upload_url = f'http://localhost:8000/api/v1/investigations/{case_id}/reference-image'
req_upload = urllib.request.Request(upload_url, data=payload, headers={'Content-Type': f'multipart/form-data; boundary={boundary}', 'Authorization': f'Bearer {token}'})
with urllib.request.urlopen(req_upload) as response:
    upload_resp = json.loads(response.read().decode('utf-8'))
print(f'[TEST] Uploaded reference image: {json.dumps(upload_resp, indent=2)}')

# 5. Trigger Web Search
search_url = f'http://localhost:8000/api/v1/investigations/{case_id}/web-search'
search_data = json.dumps({'max_results': 25, 'include_similar': True}).encode('utf-8')
req_search = urllib.request.Request(search_url, data=search_data, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
with urllib.request.urlopen(req_search) as response:
    search_resp = json.loads(response.read().decode('utf-8'))
print(f'[TEST] Web search result: {json.dumps(search_resp, indent=2)}')

# 6. Fetch Findings
findings_url = f'http://localhost:8000/api/v1/investigations/{case_id}/findings'
req_findings = urllib.request.Request(findings_url, headers={'Authorization': f'Bearer {token}'})
with urllib.request.urlopen(req_findings) as response:
    findings_resp = json.loads(response.read().decode('utf-8'))
print(f'[TEST] Findings result: {json.dumps(findings_resp, indent=2)}')
