from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import os
import uuid
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Permite que o Lovable acesse sua API sem erro de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodePayload(BaseModel):
    code: str
    libraries: list[str] = []

@app.post("/compile")
async def compile_code(payload: CodePayload):
    project_id = str(uuid.uuid4())
    path = f"/tmp/{project_id}"
    os.makedirs(path, exist_ok=True)
    
    # Salva o arquivo .ino
    with open(f"{path}/{project_id}.ino", "w") as f:
        f.write(payload.code)
    
    # Instala bibliotecas que a IA identificou
    for lib in payload.libraries:
        subprocess.run(f"arduino-cli lib install \"{lib}\"", shell=True)
    
    # Compila para Arduino Uno
    cmd = f"arduino-cli compile --fqbn arduino:avr:uno {path} --output-dir {path}/build"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        return {"success": False, "error": result.stderr}
    
    # Lê o arquivo HEX gerado
    hex_path = f"{path}/build/{project_id}.ino.hex"
    with open(hex_path, "r") as f:
        hex_content = f.read()
        
    return {"success": True, "hex": hex_content}
