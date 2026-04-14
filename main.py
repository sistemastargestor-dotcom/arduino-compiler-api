from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import os
import uuid
import shutil
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configuração de CORS para permitir que o Lovable acesse a API sem bloqueios
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodePayload(BaseModel):
    code: str
    board: str = "arduino:avr:uno"  # Pode receber 'arduino:avr:uno' ou 'arduino:avr:mega'
    libraries: list[str] = []

@app.get("/")
async def health_check():
    return {"status": "online", "message": "Compilador Arduino StarTec pronto!"}

@app.post("/compile")
async def compile_code(payload: CodePayload):
    # Cria um ID único para este projeto para evitar conflitos entre múltiplos usuários
    project_id = f"proj_{uuid.uuid4().hex[:8]}"
    project_dir = f"/tmp/{project_id}"
    os.makedirs(project_dir, exist_ok=True)
    
    ino_file = f"{project_dir}/{project_id}.ino"
    
    try:
        # 1. Escreve o código no arquivo .ino
        with open(ino_file, "w") as f:
            f.write(payload.code)
        
        # 2. Instala as bibliotecas necessárias (se houver)
        for lib in payload.libraries:
            # Tenta instalar a biblioteca via arduino-cli
            subprocess.run(
                ["arduino-cli", "lib", "install", lib],
                capture_output=True,
                text=True
            )
        
        # 3. Executa a compilação
        # O output-dir define onde os arquivos .hex/.bin serão gerados
        build_dir = f"{project_dir}/build"
        compile_cmd = [
            "arduino-cli", "compile",
            "--fqbn", payload.board,
            "--output-dir", build_dir,
            project_dir
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return {
                "success": False, 
                "error": result.stderr or result.stdout
            }
        
        # 4. Busca o arquivo compilado (.hex para AVR ou .bin para outros)
        # O nome do arquivo varia conforme a placa, então buscamos por extensão
        hex_content = ""
        files = os.listdir(build_dir)
        target_file = next((f for f in files if f.endswith(".hex") or f.endswith(".bin")), None)
        
        if target_file:
            with open(f"{build_dir}/{target_file}", "r") as f:
                hex_content = f.read()
        
        return {
            "success": True,
            "hex": hex_content,
            "board_used": payload.board
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    
    finally:
        # Limpa os arquivos temporários para não encher o disco da VPS
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
