import http.client
import json

# Leer el archivo JSON
with open('test_order.json', 'r', encoding='utf-8') as f:
    order_data = json.load(f)

# Convertir a JSON string
json_data = json.dumps(order_data)

# Crear conexión
conn = http.client.HTTPConnection("localhost", 8000)

# Enviar request
headers = {'Content-Type': 'application/json'}
conn.request("POST", "/api/v1/orders", json_data, headers)

# Obtener respuesta
response = conn.getresponse()

# Leer y parsear respuesta
response_data = response.read().decode('utf-8')
response_json = json.loads(response_data)

# Mostrar resultado
print(f"Status Code: {response.status}")
print(f"\nResponse:")
print(json.dumps(response_json, indent=2, ensure_ascii=False))

conn.close()
