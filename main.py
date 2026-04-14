from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import os
import uuid
import shutil
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Habilita CORS para o Lovable
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodePayload(BaseModel):
    code: str
    board: str = "arduino:avr:uno"
    libraries: list[str] = []

@app.get("/")
async def health():
    return {"status": "online", "service": "StarTec Compiler API"}

@app.post("/compile")
async def compile_code(payload: CodePayload):
    # UUID curto para identificar o projeto nos logs
    project_id = f"st_{uuid.uuid4().hex[:6]}"
    project_dir = f"/tmp/{project_id}"
    os.makedirs(project_dir, exist_ok=True)
    
    ino_file = f"{project_dir}/{project_id}.ino"
    build_dir = f"{project_dir}/build"
    
    try:
        # Escreve o código enviado
        with open(ino_file, "w") as f:
            f.write(payload.code)
        
        # Garante que as bibliotecas solicitadas existam
        for lib in payload.libraries:
            subprocess.run(["arduino-cli", "lib", "install", lib], capture_output=True)
        
        # COMANDO DE COMPILAÇÃO:
        # --clean: Força recompilação total (essencial para mudar de Uno para Mega)
        # --output-dir: Local fixo para facilitar a busca do binário
        compile_cmd = [
            "arduino-cli", "compile",
            "--fqbn", payload.board,
            "--output-dir", build_dir,
            "--clean",
            project_dir
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        # Log de depuração no Easypanel
        print(f"[{project_id}] Placa: {payload.board}")
        
        if result.returncode != 0:
            print(f"[{project_id}] Erro: {result.stderr}")
            return {"success": False, "error": result.stderr}

        # Busca pelo arquivo HEX (Intel HEX)
        # O Mega 2560 produz um HEX que o bootloader STK500v2 entende melhor
        hex_content = ""
        if os.path.exists(build_dir):
            files = os.listdir(build_dir)
            # Filtra para pegar o .hex principal (ignora o .with_bootloader.hex)
            target = next((f for f in files if f.endswith(".hex") and not f.endswith(".with_bootloader.hex")), None)
            
            if not target: # Fallback para qualquer .hex se o anterior falhar
                target = next((f for f in files if f.endswith(".hex")), None)

            if target:
                with open(f"{build_dir}/{target}", "r") as f:
                    hex_content = f.read()
                    print(f"[{project_id}] HEX gerado com sucesso ({len(hex_content)} bytes)")
            else:
                return {"success": False, "error": "Arquivo HEX não encontrado no diretório de build."}
        
        return {
            "success": True,
            "hex": hex_content,
            "board_used": payload.board,
            "project_id": project_id
        }

    except Exception as e:
        print(f"[{project_id}] Erro Crítico: {str(e)}")
        return {"success": False, "error": str(e)}
    
    finally:
        # Limpeza para manter o servidor saudável
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
