from docling.document_converter import DocumentConverter
import os

def main():
    # Ruta al archivo PDF
    pdf_path = "data/PL-010-2024-2025.pdf"
    
    # Verificar si el archivo existe
    if not os.path.exists(pdf_path):
        print(f"Error: No se encontró el archivo en {pdf_path}")
        return
    
    try:
        # Crear una instancia del convertidor
        converter = DocumentConverter()
        
        # Convertir el documento
        result = converter.convert(pdf_path)
        
        # Extraer el texto
        texto = result.document.export_to_markdown()
        print("Texto extraído del PDF:")
        print("-" * 50)
        print(texto)
        
        # Guardar como markdown
        with open("data/salida.md", "w") as f:
            f.write(texto)
        print("\nDocumento convertido exitosamente a markdown!")
        
    except Exception as e:
        print(f"Error al procesar el documento: {str(e)}")

if __name__ == "__main__":
    main()
