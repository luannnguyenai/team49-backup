import subprocess
import sys
import os

max_attempts = 10
for i in range(max_attempts):
    print(f"----- Attempt {i+1} -----")
    result = subprocess.run(
        ["uv", "run", "python", "-c", "import src.api.app; print('SUCCESS')"],
        capture_output=True, text=True
    )
    if "SUCCESS" in result.stdout:
        print("All imports successful!")
        break
    else:
        err = result.stderr
        print(err)
        # Find ModuleNotFoundError
        for line in err.split('\n'):
            if "ModuleNotFoundError:" in line:
                module = line.split("'")[1]
                print(f"Missing module detected: {module}")
                mapping = {
                    'jose': 'python-jose[cryptography]',
                    'passlib': 'passlib[bcrypt]',
                    'psycopg2': 'psycopg2-binary',
                    'langchain_openai': 'langchain-openai',
                    'langchain_core': 'langchain-core',
                    'multipart': 'python-multipart',
                    'dotenv': 'python-dotenv'
                }
                pkg_to_install = mapping.get(module, module)
                print(f"Installing {pkg_to_install}...")
                subprocess.run(["uv", "add", pkg_to_install])
                break
        else:
            print("Unknown error. Stopping.")
            break
