from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import os
import uuid
import shutil
import base64
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configuração de CORS para permitir que o Lovable acesse o backend sem bloqueios
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
    return {"status": "online", "service": "StarTec Multi-Compiler v2.2 (AVR/ESP + Libs)"}

@app.post("/compile")
async def compile_code(payload: CodePayload):
    # Identificador único para a compilação atual
    project_id = f"st_{uuid.uuid4().hex[:6]}"
    project_dir = f"/tmp/{project_id}"
    os.makedirs(project_dir, exist_ok=True)
    
    ino_file = f"{project_dir}/{project_id}.ino"
    build_dir = f"{project_dir}/build"
    
    try:
        # 1. Salva o código-fonte
        with open(ino_file, "w") as f:
            f.write(payload.code)
        
        # 2. Instala as bibliotecas solicitadas (via campo de busca do Lovable)
        for lib in payload.libraries:
            lib_name = lib.strip()
            if lib_name:
                print(f"[{project_id}] Verificando biblioteca: {lib_name}")
                subprocess.run(["arduino-cli", "lib", "install", lib_name], capture_output=True)
        
        # 3. Executa a compilação no arduino-cli
        compile_cmd = [
            "arduino-cli", "compile",
            "--fqbn", payload.board,
            "--output-dir", build_dir,
            "--clean",
            project_dir
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # Retorna o erro de compilação detalhado (ex: falta de ponto e vírgula no C++)
            return {"success": False, "error": result.stderr or result.stdout}

        output_data = ""
        file_format = ""
        
        if os.path.exists(build_dir):
            files = os.listdir(build_dir)
            
            # --- Lógica de Identificação por Arquitetura ---
            
            # Se a placa for da família AVR (Uno, Mega, Nano)
            if "avr" in payload.board:
                hex_file = next((f for f in files if f.endswith(".hex") and not f.endswith(".with_bootloader.hex")), None)
                if hex_file:
                    with open(f"{build_dir}/{hex_file}", "r") as f:
                        output_data = f.read()
                        file_format = "hex"
                else:
                    # Caso não ache o .hex, tenta o .bin mas avisa o formato
                    bin_file = next((f for f in files if f.endswith(".bin")), None)
                    if bin_file:
                        with open(f"{build_dir}/{bin_file}", "rb") as f:
                            output_data = base64.b64encode(f.read()).decode('utf-8')
                            file_format = "bin"

            # Se a placa for da família ESP8266 (NodeMCU)
            elif "esp8266" in payload.board:
                bin_file = next((f for f in files if f.endswith(".bin")), None)
                if bin_file:
                    with open(f"{build_dir}/{bin_file}", "rb") as f:
                        output_data = base64.b64encode(f.read()).decode('utf-8')
                        file_format = "bin"
        
        return {
            "success": True,
            "data": output_data,
            "format": file_format,
            "board_used": payload.board
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        # Limpa o projeto temporário para não encher o disco da VPS
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
