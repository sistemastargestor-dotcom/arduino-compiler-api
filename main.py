from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import os
import uuid
import shutil
import base64
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configuração de CORS para permitir que o navegador (Lovable) acesse a API sem bloqueios
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodePayload(BaseModel):
    code: str
    board: str = "arduino:avr:uno"
    libraries: list[str] = []

@app.get("/")
async def health():
    return {"status": "online", "service": "StarTec Multi-Compiler v2.1 (AVR/ESP + Libs)"}

@app.post("/compile")
async def compile_code(payload: CodePayload):
    # Criamos um ID único para cada compilação para evitar conflitos entre usuários
    project_id = f"st_{uuid.uuid4().hex[:6]}"
    project_dir = f"/tmp/{project_id}"
    os.makedirs(project_dir, exist_ok=True)
    
    ino_file = f"{project_dir}/{project_id}.ino"
    build_dir = f"{project_dir}/build"
    
    try:
        # Salva o código enviado pelo usuário
        with open(ino_file, "w") as f:
            f.write(payload.code)
        
        # Instalação automática das bibliotecas enviadas pelo campo de pesquisa
        for lib in payload.libraries:
            lib_name = lib.strip()
            if lib_name:
                print(f"[{project_id}] Verificando biblioteca: {lib_name}")
                # O arduino-cli gerencia o cache (só baixa se não existir)
                subprocess.run(["arduino-cli", "lib", "install", lib_name], capture_output=True)
        
        # Executa a compilação no arduino-cli
        compile_cmd = [
            "arduino-cli", "compile",
            "--fqbn", payload.board,
            "--output-dir", build_dir,
            "--clean",
            project_dir
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # Retorna o erro detalhado da IDE (ex: erro de sintaxe)
            return {"success": False, "error": result.stderr or result.stdout}

        output_data = ""
        file_format = ""
        
        if os.path.exists(build_dir):
            files = os.listdir(build_dir)
            
            # Ordem de detecção: 
            # 1. Se gerou .bin -> É uma placa tipo ESP8266
            bin_file = next((f for f in files if f.endswith(".bin")), None)
            # 2. Se gerou .hex -> É uma placa tipo Arduino (AVR)
            hex_file = next((f for f in files if f.endswith(".hex") and not f.endswith(".with_bootloader.hex")), None)

            if bin_file:
                with open(f"{build_dir}/{bin_file}", "rb") as f:
                    # ESP8266 exige Base64 para envio binário seguro via JSON
                    output_data = base64.b64encode(f.read()).decode('utf-8')
                    file_format = "bin"
            elif hex_file:
                with open(f"{build_dir}/{hex_file}", "r") as f:
                    # Arduino Uno/Mega envia o HEX como texto puro
                    output_data = f.read()
                    file_format = "hex"
        
        return {
            "success": True,
            "data": output_data,
            "format": file_format, # CAMPO VITAL: Indica ao Lovable qual protocolo usar
            "board_used": payload.board
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        # Limpa o projeto temporário mas mantém as bibliotecas instaladas no sistema
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
