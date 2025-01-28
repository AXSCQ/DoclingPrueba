from openai import OpenAI
import os
from dotenv import load_dotenv
from pdf_processor import PDFProcessor
import requests
from config import get_db
from models import LawDocument
import re
from typing import List

# Cargar variables de entorno
load_dotenv()

class PDFChatBot:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.pdf_processor = PDFProcessor()
        self.update_laws_context()
        
    def update_laws_context(self):
        """Actualiza el contexto de leyes desde la API a la base de datos"""
        print("🔄 Actualizando contexto de leyes...")
        api_url = "https://diputados.gob.bo/wp-json/wp/v2/ley?estado_de_ley=7&page=1&per_page=100&acf_format=standard"
        
        try:
            # Obtener datos de la API
            response = requests.get(api_url)
            data = response.json()[:5]  # Limitamos a 5 PDFs
            
            # Obtener sesión de DB
            db = next(get_db())
            
            for item in data:
                if 'acf' in item and 'archivo_ley' in item['acf']:
                    # Procesar PDF y guardar en DB
                    self.pdf_processor.process_pdf(
                        pdf_url=item['acf']['archivo_ley'],
                        metadata=item['acf'],
                        db=db
                    )
            
            print("✅ Contexto actualizado en la base de datos")
            
        except Exception as e:
            print(f"❌ Error actualizando contexto: {str(e)}")

    def find_relevant_sections(self, question: str, content: str, chunk_size: int = 1000) -> str:
        """
        Busca secciones relevantes del contenido basado en la pregunta.
        Divide el contenido en chunks y busca palabras clave.
        """
        # Obtener palabras clave de la pregunta
        keywords = re.findall(r'\w+', question.lower())
        
        # Dividir el contenido en chunks
        chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
        relevant_chunks = []
        
        for chunk in chunks:
            # Contar cuántas palabras clave aparecen en este chunk
            relevance_score = sum(1 for keyword in keywords if keyword in chunk.lower())
            if relevance_score > 0:
                relevant_chunks.append((relevance_score, chunk))
        
        # Ordenar por relevancia y tomar los chunks más relevantes
        relevant_chunks.sort(reverse=True)
        selected_chunks = [chunk for score, chunk in relevant_chunks[:3]]  # Tomar los 3 chunks más relevantes
        
        return "\n...\n".join(selected_chunks)

    def ask(self, question):
        try:
            relevant_context = []
            
            for law in self.laws_context:
                # Buscar secciones relevantes del contenido basadas en la pregunta
                relevant_content = self.find_relevant_sections(question, law['content'])
                
                context_piece = {
                    'ley_nro': law['metadata']['ley_nro'],
                    'titulo': law['metadata']['titulo'],
                    'descripcion': law['metadata']['descripcion'],
                    'contenido_relevante': relevant_content
                }
                relevant_context.append(str(context_piece))
            
            context = "\n\n".join(relevant_context)
            
            prompt = f"""Basándote en la siguiente información sobre leyes:
            {context}
            
            Pregunta: {question}
            
            Por favor, proporciona una respuesta detallada basada en la información disponible.
            Si necesitas información adicional o si la información proporcionada no es suficiente, indícalo claramente."""
            
            # Primera llamada para análisis general
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un asistente experto en analizar documentos legales. Proporciona respuestas precisas y detalladas."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error al procesar la pregunta: {str(e)}"

    def ask_specific(self, question: str, selected_pdfs: List[str]):
        """Responde preguntas basadas en PDFs específicos"""
        try:
            db = next(get_db())
            relevant_laws = []
            
            # Buscar documentos en la base de datos
            for law_number in selected_pdfs:
                law = db.query(LawDocument).filter_by(law_number=law_number).first()
                if law:
                    relevant_content = self.find_relevant_sections(question, law.content)
                    relevant_laws.append({
                        'law_number': law.law_number,
                        'title': law.title,
                        'content': relevant_content
                    })
            
            if not relevant_laws:
                return "No se encontraron los documentos seleccionados."
            
            # Construir el prompt
            context_text = "\n\n".join([
                f"Ley {law['law_number']}: {law['title']}\n{law['content']}"
                for law in relevant_laws
            ])
            
            prompt = (
                "Basándote en la siguiente información sobre las leyes seleccionadas:\n"
                f"{context_text}\n\n"
                f"Pregunta: {question}\n\n"
                "Por favor, proporciona una respuesta detallada basada en la información disponible."
            )
            
            # Obtener respuesta de OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un asistente experto en analizar documentos legales."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"❌ Error en ask_specific: {str(e)}")
            return f"Error al procesar la pregunta: {str(e)}"

def main():
    print("🤖 Iniciando ChatBot Legal...")
    chatbot = PDFChatBot()
    
    print("\n¡Bienvenido al ChatBot de documentos legales!")
    print("Escribe 'salir' para terminar")
    print("Escribe 'actualizar' para recargar los documentos")
    
    while True:
        question = input("\n❓ Haz tu pregunta: ")
        
        if question.lower() == 'salir':
            break
        elif question.lower() == 'actualizar':
            chatbot.update_laws_context()
            continue
            
        print("\n🤖 Respuesta:", chatbot.ask(question))

if __name__ == "__main__":
    main() 