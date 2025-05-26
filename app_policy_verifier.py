import os
import tarfile
import yaml
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
import joblib  # For loading a pre-trained model

app = Flask(__name__)

# Load your pre-trained One-Class SVM model and preprocessor
OCSVM_MODEL_PATH = "ocsvm_model.pkl"  
PREPROCESSOR_PATH = "preprocessor.pkl" 

# Load the pre-trained components
ocsvm = joblib.load(OCSVM_MODEL_PATH)
preprocessor = joblib.load(PREPROCESSOR_PATH)

@app.route('/upload-helm', methods=['POST'])
def upload_helm_chart():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']

    # Check if the uploaded file is a Helm chart (.tgz)
    if not file.filename.endswith('.tgz'):
        return jsonify({"error": "Invalid file type. Please upload a .tgz Helm chart."}), 400

    # Create a temporary directory to extract the chart
    temp_dir = "temp_chart"
    os.makedirs(temp_dir, exist_ok=True)
    chart_path = os.path.join(temp_dir, file.filename)

    try:
        # Save and extract the chart
        file.save(chart_path)
        with tarfile.open(chart_path, "r:gz") as tar:
            tar.extractall(path=temp_dir)

        # Locate the values.yaml file
        values_file = None
        for root, dirs, files in os.walk(temp_dir):
            if "values.yaml" in files:
                values_file = os.path.join(root, "values.yaml")
                break

        if not values_file:
            return jsonify({"error": "values.yaml not found in the Helm chart."}), 400

        # Parse the values.yaml
        with open(values_file, 'r') as f:
            values = yaml.safe_load(f)

        # Extract and preprocess relevant values
        test_data = preprocess_values(values)

        # Preprocess the test data
        test_data_preprocessed = preprocessor.transform(test_data)

        # Predict using the One-Class SVM
        predictions = ocsvm.predict(test_data_preprocessed)

        # Convert predictions to binary labels: 1 for "right" and 0 for "wrong"
        test_data['predicted_label'] = np.where(predictions == 1, 1, 0)

        # Return predictions as JSON
        response = {
            "helm_file": file.filename,
            "predictions": test_data.to_dict(orient="records")
        }
        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Clean up temporary files
        if os.path.exists(temp_dir):
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(temp_dir)


def preprocess_values(values):
    """
    Extract relevant values from values.yaml and prepare them as a DataFrame for model input.
    """
    try:
        # Extract values for AMF, SMF, and UPF components
        components = ["amf", "smf", "pcf"]
        data = []

        for component in components:
            if component in values:
                component_data = values[component]
                replica_count = component_data.get("replicaCount", 0)
                cpu_limit = component_data.get("resources", {}).get("limits", {}).get("cpu", 0)
                memory_limit = component_data.get("resources", {}).get("limits", {}).get("memory", 0)

                # Add a row with component name and its extracted values
                data.append({
                    "replica_count": replica_count,
                    "cpu_limit": int(cpu_limit),
                    "memory_limit": int(memory_limit),
                    "network_function": component.upper()  # AMF, SMF, PCF
                })
            else:
                # Append default values if the component is missing
                data.append({
                    "replica_count": 0,
                    "cpu_limit": 0,
                    "memory_limit": 0,
                    "network_function": component.upper()
                })

        # Convert to a DataFrame
        df = pd.DataFrame(data)
        return df

    except Exception as e:
        raise ValueError(f"Error in preprocessing values: {e}")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
