from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from config import Base

class LawDocument(Base):
    __tablename__ = 'law_documents'
    
    id = Column(Integer, primary_key=True)
    law_number = Column(String, unique=True)  # Número único de ley
    year = Column(String)                     # Año legislativo
    title = Column(String)                    # Título del proyecto
    description = Column(String)              # Descripción
    content = Column(String)                  # Contenido procesado
    pdf_path = Column(String)                 # Ruta al archivo PDF
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<LawDocument(law_number='{self.law_number}', title='{self.title}')>" 