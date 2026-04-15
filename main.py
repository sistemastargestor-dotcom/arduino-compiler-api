from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import os
import uuid
import shutil
import base64
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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
    return {"status": "online", "service": "StarTec Multi-Board Compiler"}

@app.post("/compile")
async def compile_code(payload: CodePayload):
    project_id = f"st_{uuid.uuid4().hex[:6]}"
    project_dir = f"/tmp/{project_id}"
    os.makedirs(project_dir, exist_ok=True)
    
    ino_file = f"{project_dir}/{project_id}.ino"
    build_dir = f"{project_dir}/build"
    
    try:
        with open(ino_file, "w") as f:
            f.write(payload.code)
        
        for lib in payload.libraries:
            subprocess.run(["arduino-cli", "lib", "install", lib], capture_output=True)
        
        # Compilação limpa
        compile_cmd = [
            "arduino-cli", "compile",
            "--fqbn", payload.board,
            "--output-dir", build_dir,
            "--clean",
            project_dir
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return {"success": False, "error": result.stderr}

        output_data = ""
        file_format = ""
        
        if os.path.exists(build_dir):
            files = os.listdir(build_dir)
            
            # Prioridade 1: Arquivo .bin (Para ESP8266/NodeMCU)
            bin_file = next((f for f in files if f.endswith(".bin")), None)
            # Prioridade 2: Arquivo .hex (Para Uno/Mega)
            hex_file = next((f for f in files if f.endswith(".hex") and not f.endswith(".with_bootloader.hex")), None)

            if bin_file:
                with open(f"{build_dir}/{bin_file}", "rb") as f:
                    # Converte binário para Base64 para envio seguro via JSON
                    output_data = base64.b64encode(f.read()).decode('utf-8')
                    file_format = "bin"
            elif hex_file:
                with open(f"{build_dir}/{hex_file}", "r") as f:
                    output_data = f.read()
                    file_format = "hex"
            else:
                return {"success": False, "error": "Nenhum arquivo binário (.bin) ou hex (.hex) gerado."}
        
        return {
            "success": True,
            "data": output_data, # Pode ser HEX string ou Base64 binário
            "format": file_format,
            "board_used": payload.board,
            "project_id": project_id
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
