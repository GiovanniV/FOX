import subprocess

subprocess.run(["python", "-m", "pip", "freeze"], text=True, stdout=open("requirements.txt", "w"))
