import os
import uuid
import re
import requests
import logging
from typing import List, Dict, Any, Generator

try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False
    
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

logger = logging.getLogger(__name__)

class DocumentSplitter:
    """
    Intelligently splits large text documents into smaller chunks suitable for 
    embedding and LLM context windows (e.g., RecursiveCharacterTextSplitter).
    """
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        """Splits text by double newlines, then by newlines, then by spaces if necessary."""
        # Clean the text
        text = re.sub(r'\s+', ' ', text).strip()
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            
            # If we're at the end of the text, just take the rest
            if end >= text_length:
                chunks.append(text[start:])
                break
                
            # Try to find a good breaking point (period, newline, or space)
            break_point = end
            for char in ['. ', '? ', '! ', '\n', ' ']:
                last_idx = text.rfind(char, start, end)
                if last_idx != -1:
                    break_point = last_idx + 1 # Include the breaking character
                    break
                    
            chunks.append(text[start:break_point].strip())
            
            # Move the start pointer, accounting for overlap
            start = break_point - self.chunk_overlap
            
            # Prevent infinite loops if overlap is too large
            if start <= 0 or break_point == start + self.chunk_overlap:
                start = break_point
                
        return chunks


class PDFConnector:
    """Extracts text from sustainability reports (PDFs)."""
    
    @staticmethod
    def load(file_path: str) -> List[Dict[str, Any]]:
        if not HAS_PDF:
            logger.error("pdfplumber is required to parse PDFs.")
            return []
            
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return []
            
        documents = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        documents.append({
                            "text": text,
                            "metadata": {
                                "source": file_path,
                                "page": i + 1,
                                "type": "pdf"
                            }
                        })
        except Exception as e:
            logger.error(f"Failed to read PDF {file_path}: {e}")
            
        return documents


class WebConnector:
    """Scrapes sustainability blogs and research papers from the web."""
    
    @staticmethod
    def load(url: str) -> List[Dict[str, Any]]:
        if not HAS_BS4:
            # We can do a basic parse if bs4 isn't installed
            pass
            
        try:
            headers = {'User-Agent': 'EcoBuddy/1.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            if HAS_BS4:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Extract text from paragraphs
                paragraphs = soup.find_all('p')
                text = " ".join([p.get_text() for p in paragraphs])
                title = soup.title.string if soup.title else url
            else:
                # Naive regex stripping
                text = re.sub(r'<[^>]+>', ' ', response.text)
                title = url
                
            # Clean up white space
            text = re.sub(r'\s+', ' ', text).strip()
            
            if text:
                return [{
                    "text": text,
                    "metadata": {
                        "source": url,
                        "title": title,
                        "type": "web"
                    }
                }]
        except requests.RequestException as e:
            logger.error(f"Failed to scrape URL {url}: {e}")
            
        return []


class EcoDataIngestionPipeline:
    """
    Orchestrates the loading, splitting, and formatting of documents 
    before they are passed to the EcoRAGEngine for embedding.
    """
    
    def __init__(self, chunk_size: int = 500):
        self.splitter = DocumentSplitter(chunk_size=chunk_size)
        
    def ingest_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Reads a PDF, chunks it, and assigns UUIDs."""
        raw_docs = PDFConnector.load(file_path)
        return self._process_raw_docs(raw_docs)
        
    def ingest_url(self, url: str) -> List[Dict[str, Any]]:
        """Scrapes a URL, chunks it, and assigns UUIDs."""
        raw_docs = WebConnector.load(url)
        return self._process_raw_docs(raw_docs)
        
    def _process_raw_docs(self, raw_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        processed = []
        for doc in raw_docs:
            chunks = self.splitter.split_text(doc["text"])
            for i, chunk in enumerate(chunks):
                if len(chunk) > 20: # Ignore tiny fragments
                    processed.append({
                        "id": str(uuid.uuid4()),
                        "text": chunk,
                        "metadata": {
                            **doc["metadata"],
                            "chunk_index": i
                        }
                    })
        return processed
