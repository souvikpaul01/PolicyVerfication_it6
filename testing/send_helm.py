import requests
import json

url = "http://127.0.0.1:5000/upload-helm"
file_path = "example-helm-chart-1.0.0.tgz"

with open(file_path, 'rb') as file:
    response = requests.post(url, files={'file': file})

# Print the server's response
# print("Status Code:", response.status_code)
# print("Response:", response.json())

if response.status_code == 200:
  data = response.json()  # Assuming the response is in JSON format
  pretty_response = json.dumps(data, indent=4)
  print(pretty_response)  # This will print the retrieved row or an empty dictionary if not found
else:
  print("Request failed with status code:", response.status_code)
