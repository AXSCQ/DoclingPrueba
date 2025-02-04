from config import engine, Base, init_vector_extension
from models import LawDocument

def create_tables():
    print("🔄 Inicializando extensión pgvector...")
    init_vector_extension()
    
    print("🔄 Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas exitosamente")

if __name__ == "__main__":
    create_tables() 