"""
Extraction Pipeline - Orchestrates document processing and entity extraction.
"""

from pathlib import Path
from typing import Iterator

from .entities import Person


class ExtractionPipeline:
    """
    Main extraction pipeline for processing documents and extracting entities.
    
    Usage:
        pipeline = ExtractionPipeline()
        for person in pipeline.process_directory("data/reports/"):
            print(person.case_number)
    """
    
    def __init__(
        self,
        llm_model: str = "llama3",
        ollama_url: str = "http://localhost:11434"
    ):
        """
        Initialize the extraction pipeline.
        
        Args:
            llm_model: Ollama model name for extraction.
            ollama_url: URL of the Ollama server.
        """
        self.llm_model = llm_model
        self.ollama_url = ollama_url
    
    def process_file(self, file_path: Path) -> Person | None:
        """
        Process a single document and extract a Person entity.
        
        Args:
            file_path: Path to the document (PDF, TXT, etc.)
            
        Returns:
            Extracted Person entity, or None if extraction fails.
        """
        # TODO: Implement document processing
        # 1. Load document using Unstract
        # 2. Extract text content
        # 3. Call LLM for entity extraction
        # 4. Parse response into Person entity
        raise NotImplementedError("Document processing not yet implemented")
    
    def process_directory(self, directory: Path) -> Iterator[Person]:
        """
        Process all documents in a directory.
        
        Args:
            directory: Path to directory containing documents.
            
        Yields:
            Extracted Person entities.
        """
        directory = Path(directory)
        
        for file_path in directory.glob("**/*"):
            if file_path.suffix.lower() in [".pdf", ".txt", ".docx"]:
                person = self.process_file(file_path)
                if person:
                    yield person
