
import requests
import json
from typing import Dict, Any, List

class NarrativeGenerator:
    """
    Generates investigative narratives and story lines using DeepSeek-R1 via Ollama.
    """
    
    def __init__(self, ollama_host: str = "http://localhost:11434", model: str = "deepseek-r1:1.5b"):
        self.ollama_host = ollama_host
        self.model = model
        
    def generate_story_line(self, uhr_data: Dict[str, Any], mp_data: Dict[str, Any], shared_features: List[str]) -> str:
        """
        Constructs a prompt and generates a narrative explanation of the potential connection.
        """
        prompt = self._build_prompt(uhr_data, mp_data, shared_features)
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 2500,
                            "num_ctx": 4096
                        }
                    },
                    timeout=600
                )
                resp_json = response.json()
                narrative = resp_json.get("response", "")
                
                if not narrative or narrative.strip() == "":
                    # Fallback to thinking field if response is empty (common with DeepSeek-R1)
                    narrative = resp_json.get("thinking", "")
                    
                if not narrative:
                    return "Could not generate narrative (DeepSeek-R1 returned empty response)."
                
                return narrative
                
            except requests.exceptions.HTTPError as e:
                # If model is not found (404), it might be loading. Retry.
                if e.response is not None and e.response.status_code == 404:
                    print(f"[WARN] Model check failed (404). Retrying in {retry_delay}s... (Attempt {attempt+1}/{max_retries})")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                
                # For other HTTP errors, return details
                error_msg = f"Error generating narrative: {e}"
                if e.response is not None:
                    error_msg += f"\nResponse Body: {e.response.text}"
                return error_msg
                
            except Exception as e:
                return f"Error generating narrative: {str(e)}"
        
        return "Error: Failed to generate narrative after retries (Model not found)."
            
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
As a cold case investigator and forensic analyst, write a structured Explainable AI (XAI) report evaluating the potential match between these two cases.

### MISSION:
Analyze the potential match between Missing Person {mp_data.get('name')} ({mp_data.get('file_number')}) and Unidentified Remains {uhr_data.get('case_number')}. Evaluate both supporting and contradicting evidence.

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

### REQUIRED OUTPUT FORMAT (Markdown):

### 1. Match Confidence
- **Score**: (Provide a qualitative score: Very Low, Low, Moderate, High, or Very High)
- **Primary Reason**: (One sentence explaining why this is or isn't a good lead)

### 2. Supporting Evidence
- (List 2-3 bullet points of explicit factual alignment, e.g., age ranges, specific tattoos, logical timelines. Do not invent facts.)

### 3. Contradicting Evidence & Misalignments
- (List any conflicting facts, e.g., race mismatch, PMI inconsistencies, diverging physical traits. BE CRITICAL.)

### 4. Geographic Feasibility
- (Analyze the physical distance and plausible transit from the last seen location to the discovery site.)

### 5. Final Investigative Hypothesis
- (A concise 2-3 sentence paragraph theorizing how the MP could equal the UHR, assuming the match is true.)

**CRITICAL RULES**: Do not invent information. If an attribute (like eye color) is not mentioned in the case data, do not assume it matches. Do not make recommendations for law enforcement.
"""
        return prompt
