
import requests
import json
from typing import Dict, Any, List

class NarrativeGenerator:
    """
    Generates investigative narratives and story lines using Llama 3.2 via Ollama.
    """
    
    def __init__(self, ollama_host: str = "http://localhost:11434", model: str = "llama3.2"):
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
                timeout=600
            )
            response.raise_for_status()
            return response.json().get("response", "Could not generate narrative.")
        except Exception as e:
            return f"Error generating narrative: {str(e)}"
            
    def _build_prompt(self, uhr_data: Dict[str, Any], mp_data: Dict[str, Any], shared_features: List[str]) -> str:
        """Constructs the LLM prompt focused on facts and alignment."""
        features_str = ", ".join(shared_features)
        
        # Extract location info if available
        mp_loc = mp_data.get('last_seen_location_name') or "Unknown"
        uhr_loc = uhr_data.get('discovery_location_name') or "Unknown"
        
        # Extract circumstances if available
        mp_circ = ""
        if "Circumstances:" in mp_data.get('description', ''):
            mp_circ = mp_data['description'].split("Circumstances:")[-1].strip()
        
        uhr_circ = ""
        if "Circumstances:" in uhr_data.get('description', ''):
            uhr_circ = uhr_data['description'].split("Circumstances:")[-1].strip()

        prompt = f"""
As a cold case investigator, write a short, direct investigative hypothesis connecting these two cases.

### MISSION:
Analyze the potential match between Missing Person {mp_data.get('name')} ({mp_data.get('file_number')}) and Unidentified Remains {uhr_data.get('case_number')}.

### CASE DATA:
1. **Missing Person (MP)**:
   - Name: {mp_data.get('name')}
   - Last Seen: {mp_data.get('last_seen_date', 'Unknown date')} at {mp_loc}
   - Circumstances: {mp_circ if mp_circ else "See description"}
   - Description: {mp_data.get('description', '')[:1500]}

2. **Unidentified Human Remains (UHR)**:
   - Case Number: {uhr_data.get('case_number')}
   - Discovered: {uhr_data.get('discovery_date', 'Unknown date')} at {uhr_loc}
   - Circumstances: {uhr_circ if uhr_circ else "See description"}
   - Description: {uhr_data.get('description', '')[:1500]}

3. **Technical Overlaps**: {features_str}

### REQUIRED STRUCTURE:
1. **The Lead**: Start immediately with the MP's story and why it fits this UHR.
2. **Fact Alignment**: Compare age, missing period vs. post-mortem interval (PMI). Do they align?
3. **Contradictions & Misalignment**: Explicitly identify any facts that DO NOT match (e.g., contrasting features, timeline gaps, or conflicting descriptions). Be critical.
4. **Geography**: Analyze the path from last seen location to finding location. Use the specific villages/reservations/landmark names provided in Circumstances.
5. **Hypothesis**: How did they likely end up at the discovery site?

**CRITICAL: DO NOT suggest "Next Steps", "Recommendations", or further investigation.** Keep it concise, professional, and strictly fact-driven. Ensure you highlight both the case for and the case against the match.
"""
        return prompt
