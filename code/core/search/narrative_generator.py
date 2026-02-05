
import requests
import json
from typing import Dict, Any, List

class NarrativeGenerator:
    """
    Generates investigative narratives and story lines using Llama 3.2 via Ollama.
    """
    
    def __init__(self, ollama_host: str = "http://ollama:11434", model: str = "llama3.2"):
        self.ollama_host = ollama_host
        self.model = model
        
    def generate_story_line(self, uhr_data: Dict[str, Any], mp_data: Dict[str, Any], shared_features: List[str]) -> str:
        """
        Constructs a prompt and generates a narrative explanation of the potential connection.
        """
        prompt = self._build_prompt(uhr_data, mp_data, shared_features)
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 500
                    }
                },
                timeout=180
            )
            response.raise_for_status()
            return response.json().get("response", "Could not generate narrative.")
        except Exception as e:
            return f"Error generating narrative: {str(e)}"
            
    def _build_prompt(self, uhr_data: Dict[str, Any], mp_data: Dict[str, Any], shared_features: List[str]) -> str:
        """Constructs the LLM prompt."""
        features_str = ", ".join(shared_features)
        
        prompt = f"""
As a forensic investigator, analyze the following Unidentified Human Remains (UHR) case and Missing Person (MP) case for potential links. 

### CASE DETAILS: UNIDENTIFIED HUMAN REMAINS
- Case Number: {uhr_data.get('case_number')}
- Description: {uhr_data.get('description')}
- Discovery Context: {uhr_data.get('discovery_date', 'Unknown date')}

### CASE DETAILS: MISSING PERSON
- Name: {mp_data.get('name')}
- File Number: {mp_data.get('file_number')}
- Description: {mp_data.get('description')}
- Disappearance Context: {uhr_data.get('last_seen_date', 'Unknown date')}

### IDENTIFIED OVERLAPS:
The matching algorithm detected these significant shared keywords/features: {features_str}

### TASK:
Write a concise but compelling investigative narrative (2-3 paragraphs) that builds a "story line" explaining how these two cases could be connected. Focus on the physical evidence, the timeline, and the specific rare identifiers. Explain WHY these details matter in the context of a cold case investigation.

Respond only with the investigative narrative.
"""
        return prompt
