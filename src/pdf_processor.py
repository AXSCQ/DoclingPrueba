import os
import requests
import json
from typing import List, Dict, Set
from pathlib import Path
import re

class PDFProcessor:
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.pdfs_dir = self.storage_dir / "pdfs"
        self.context_dir = self.storage_dir / "contexts"
        
        # Crear directorios si no existen
        self.pdfs_dir.mkdir(parents=True, exist_ok=True)
        self.context_dir.mkdir(parents=True, exist_ok=True)

    def sanitize_filename(self, filename: str) -> str:
        """Limpia el nombre del archivo para que sea válido"""
        filename = re.sub(r'[\\/*?:"<>|]', "", filename)
        filename = filename.replace(' ', '-').replace('/', '-')
        return filename

    def clean_old_files(self, current_ley_numbers: Set[str]):
        """Elimina PDFs y contextos que ya no existen en la API"""
        # Limpiar PDFs antiguos
        for pdf_file in self.pdfs_dir.glob("*.pdf"):
            ley_nro = pdf_file.stem.replace("PL-", "")
            if ley_nro not in current_ley_numbers:
                print(f"🗑️ Eliminando PDF obsoleto: {pdf_file.name}")
                pdf_file.unlink()

        # Limpiar contextos antiguos
        for context_file in self.context_dir.glob("*.json"):
            ley_nro = context_file.stem.replace("PL-", "")
            if ley_nro not in current_ley_numbers:
                print(f"🗑️ Eliminando contexto obsoleto: {context_file.name}")
                context_file.unlink()

    def download_pdfs_from_api(self, api_url: str, limit: int = 3) -> List[Dict]:
        """
        Descarga PDFs de la API y retorna metadata
        Args:
            api_url: URL de la API
            limit: Número máximo de PDFs a descargar (default: 3)
        """
        print(f"📥 Descargando datos de la API (limitado a {limit} PDFs)...")
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()[:limit]
        except Exception as e:
            print(f"❌ Error accediendo a la API: {str(e)}")
            return []

        downloaded_files = []

        for item in data:
            try:
                if 'acf' not in item or 'archivo_ley' not in item['acf']:
                    continue

                pdf_url = item['acf']['archivo_ley']
                ley_nro = item['acf'].get('ley_nro', '').strip()
                # Corregir formato del nombre
                pdf_name = f"PL-No-{ley_nro}2024-2025.pdf"
                pdf_path = self.pdfs_dir / pdf_name
                context_path = self.context_dir / f"PL-No-{ley_nro}2024-2025.json"

                # Solo descargar si el PDF no existe o si el contexto no existe
                if not pdf_path.exists() or not context_path.exists():
                    print(f"📥 Descargando {pdf_name}...")
                    try:
                        pdf_response = requests.get(pdf_url, timeout=30)
                        pdf_response.raise_for_status()
                        
                        with open(pdf_path, 'wb') as f:
                            f.write(pdf_response.content)
                        print(f"✅ Descargado: {pdf_name}")
                    except requests.exceptions.RequestException as e:
                        print(f"❌ Error descargando {pdf_name}: {str(e)}")
                        continue
                else:
                    print(f"ℹ️ Ya existe el PDF y el contexto para: {pdf_name}")

                downloaded_files.append({
                    'pdf_path': str(pdf_path),
                    'ley_nro': ley_nro,
                    'titulo': item['acf'].get('titulo', ''),
                    'descripcion': item['acf'].get('descripcion', '')
                })

            except Exception as e:
                print(f"❌ Error procesando ley {item.get('id', 'unknown')}: {str(e)}")

        print(f"✅ Total de PDFs procesados: {len(downloaded_files)}")
        return downloaded_files

    def process_pdfs_with_docling(self, pdf_files: List[Dict]):
        """Procesa los PDFs con DocLing y guarda el contexto"""
        from docling.document_converter import DocumentConverter
        
        for pdf_file in pdf_files:
            context_path = self.context_dir / f"PL-No-{pdf_file['ley_nro']}2024-2025.json"
            
            print(f"🔄 Procesando PL No {pdf_file['ley_nro']}...")
            try:
                converter = DocumentConverter()
                result = converter.convert(pdf_file['pdf_path'])
                
                context = {
                    'metadata': pdf_file,
                    'content': result.document.export_to_markdown(),
                    'last_updated': str(Path(pdf_file['pdf_path']).stat().st_mtime)
                }
                
                with open(context_path, 'w', encoding='utf-8') as f:
                    json.dump(context, f, ensure_ascii=False, indent=2)
                print(f"✅ Procesado: {pdf_file['ley_nro']}")
                    
            except Exception as e:
                print(f"❌ Error procesando {pdf_file['ley_nro']}: {str(e)}")

    def get_all_contexts(self) -> List[Dict]:
        """Retorna todos los contextos procesados"""
        contexts = []
        for context_file in self.context_dir.glob("*.json"):
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    contexts.append(json.load(f))
            except Exception as e:
                print(f"❌ Error leyendo contexto {context_file}: {str(e)}")
        return contexts

    def get_available_pdfs(self) -> List[Dict]:
        """Retorna lista de PDFs disponibles con metadata"""
        try:
            available_pdfs = []
            print("\n🔍 Buscando PDFs en:", self.pdfs_dir)
            
            # Listar todos los archivos PDF con el nuevo patrón
            pdf_files = list(self.pdfs_dir.glob("PL-PLNo*.pdf"))
            print(f"📁 PDFs encontrados: {[pdf.name for pdf in pdf_files]}")
            
            # Listar todos los archivos de contexto
            context_files = list(self.context_dir.glob("PL-No-*.json"))
            print(f"📄 Contextos encontrados: {[ctx.name for ctx in context_files]}")
            
            for pdf_file in pdf_files:
                try:
                    # Extraer número de ley del nuevo formato
                    ley_nro = pdf_file.stem.replace("PL-PLNo", "").split("-")[0]
                    print(f"📌 Procesando ley número: {ley_nro}")
                    
                    # Buscar contexto correspondiente (formato antiguo)
                    context_file = self.context_dir / f"PL-No-{ley_nro}2024-2025.json"
                    print(f"🔎 Buscando contexto: {context_file}")
                    
                    if context_file.exists():
                        print(f"✅ Contexto encontrado para {pdf_file.name}")
                        with open(context_file, 'r', encoding='utf-8') as f:
                            context = json.load(f)
                            available_pdfs.append({
                                'ley_nro': ley_nro,
                                'titulo': context['metadata']['titulo'],
                                'descripcion': context['metadata']['descripcion'],
                                'pdf_url': str(pdf_file)
                            })
                    else:
                        print(f"❌ No se encontró contexto para {pdf_file.name}")
                
                except Exception as e:
                    print(f"❌ Error procesando {pdf_file.name}: {str(e)}")
                    continue
            
            print(f"\n📚 Total PDFs disponibles: {len(available_pdfs)}")
            if len(available_pdfs) == 0:
                print("⚠️  No se encontraron PDFs con sus contextos correspondientes")
            return available_pdfs
            
        except Exception as e:
            print(f"❌ Error general en get_available_pdfs: {str(e)}")
            return []

    def get_specific_contexts(self, ley_numbers: List[str]) -> List[Dict]:
        """Retorna contextos específicos basados en números de ley"""
        contexts = []
        for ley_nro in ley_numbers:
            context_path = self.context_dir / f"PL-No-{ley_nro}2024-2025.json"
            if context_path.exists():
                try:
                    with open(context_path, 'r', encoding='utf-8') as f:
                        contexts.append(json.load(f))
                except Exception as e:
                    print(f"❌ Error leyendo contexto {context_path}: {str(e)}")
        return contexts 