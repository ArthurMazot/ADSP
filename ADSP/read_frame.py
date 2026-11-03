# 1. Import the library
from inference_sdk import InferenceHTTPClient, InferenceConfiguration

# 2. Connect to your workflow
client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="Fgugzd9PwTSrd4HTF8Nm"
)

# 3. Run your workflow on an image
result = client.run_workflow(
    workspace_name="arthurs-workspace-pjgli",
    workflow_id="seven-segment-multi-display-reader-1793736667455",
    images={
        "image": "Teste24.jpg" # Path to your image file
    },
    use_cache=True # Speeds up repeated requests
)

# 4. Get your results
print(result)
