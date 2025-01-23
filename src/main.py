from docling.document_converter import DocumentConverter
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chatbot import PDFChatBot

# Inicializar FastAPI
app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Inicializar el chatbot (esto ya incluye la descarga y procesamiento de PDFs)
chatbot = PDFChatBot()

class ChatRequest(BaseModel):
    text: str

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        response = chatbot.ask(request.text)
        return {"response": response, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "error"}

if __name__ == "__main__":
    # Iniciar el servidor FastAPI
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
