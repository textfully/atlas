import boto3
import json
import os


def main():
    secret_id = "atlas-secrets"
    region_name = "us-east-1"
    env_path = ".env"

    try:
        client = boto3.client("secretsmanager", region_name=region_name)
        response = client.get_secret_value(SecretId=secret_id)
        secrets = (
            json.loads(response["SecretString"]) if "SecretString" in response else {}
        )
    except Exception as e:
        print(f"Error retrieving secret: {e}")
        return

    existing_env = {}
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    existing_env[key] = value

    if "DEPLOY_KEY" in existing_env:
        secrets["DEPLOY_KEY"] = existing_env["DEPLOY_KEY"]

    with open(env_path, "w") as f:
        for key, value in secrets.items():
            f.write(f"{key}={value}\n")

    print(f"Secrets written to {env_path}.")


if __name__ == "__main__":
    main()
