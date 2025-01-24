from docling.document_converter import DocumentConverter
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from chatbot import PDFChatBot
from typing import List, Optional
import json
from pathlib import Path
from datetime import datetime

# Inicializar FastAPI
app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos de datos
class UserAccess(BaseModel):
    name: str
    email: EmailStr

class ChatRequest(BaseModel):
    text: str
    selected_pdfs: List[str]  # Lista de números de ley
    user: Optional[dict] = None  # Hacemos el usuario opcional por ahora

# Registro de uso
USAGE_LOG_FILE = Path("storage/usage_log.json")
USAGE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def log_user_access(user: UserAccess):
    """Registra el acceso de un usuario al sistema"""
    logs = []
    if USAGE_LOG_FILE.exists():
        with open(USAGE_LOG_FILE, 'r') as f:
            logs = json.load(f)
    
    # Registrar nuevo acceso
    access_log = {
        "name": user.name,
        "email": user.email,
        "timestamp": datetime.now().isoformat(),
    }
    logs.append(access_log)
    
    with open(USAGE_LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

# Inicializar chatbot
chatbot = PDFChatBot()

@app.post("/api/register")
async def register_access(user: UserAccess):
    """Registra el acceso del usuario y permite uso del bot"""
    try:
        log_user_access(user)
        return {
            "message": "Acceso concedido",
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/laws")
async def get_laws():
    """Retorna lista de proyectos de ley disponibles"""
    try:
        laws = chatbot.pdf_processor.get_available_pdfs()
        if not laws:
            return {
                "laws": [],
                "message": "No hay proyectos de ley disponibles en este momento."
            }
            
        formatted_laws = []
        for law in laws:
            formatted_law = {
                "number": f"{law['ley_nro']}/2024-2025",
                "title": law['titulo'],
                "description": law['descripcion'],
                "pdfUrl": f"https://diputados.gob.bo/wp-content/uploads/2025/01/PL-No-{law['ley_nro']}2024-2025.pdf"
            }
            formatted_laws.append(formatted_law)
            
        print(f"📚 Enviando {len(formatted_laws)} leyes al frontend")
        return {
            "laws": formatted_laws
        }
    except Exception as e:
        print(f"❌ Error obteniendo leyes: {str(e)}")
        return {
            "laws": [],
            "error": str(e)
        }

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Procesa preguntas sobre PDFs seleccionados"""
    try:
        print(f"📝 Pregunta recibida: {request.text}")
        print(f"📚 PDFs seleccionados: {request.selected_pdfs}")
        
        # Obtener respuesta del chatbot
        response = chatbot.ask_specific(request.text, request.selected_pdfs)
        
        # Registrar la consulta en el log
        if USAGE_LOG_FILE.exists():
            try:
                with open(USAGE_LOG_FILE, 'r+') as f:
                    logs = json.load(f)
                    logs.append({
                        "timestamp": datetime.now().isoformat(),
                        "question": request.text,
                        "pdfs": request.selected_pdfs
                    })
                    f.seek(0)
                    json.dump(logs, f, indent=2)
            except Exception as e:
                print(f"⚠️ Error al registrar log: {str(e)}")
        
        return {
            "response": response,
            "status": "success"
        }
        
    except Exception as e:
        print(f"❌ Error en chat_endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la pregunta: {str(e)}"
        )

if __name__ == "__main__":
    # Iniciar el servidor FastAPI
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
