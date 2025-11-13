# consultations/services.py
import json
import requests

from django.conf import settings

class LLMService:
    """
    Service to interact with small LLM API.
    Supports: OpenAI, Anthropic, Groq, or any OpenAI-compatible API
    """
    
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.api_url = settings.LLM_API_URL  # e.g., https://api.groq.com/v1/chat/completions
        self.model = settings.LLM_MODEL  # e.g., "llama-3.1-8b-instant"
    
    def create_prompt(self, consultation):
        """Create a structured prompt for the LLM"""
        prompt = f"""You are MedInsight, an AI medical assistant helping clinicians. Based on the patient information below, provide:

1. **SUMMARY**: A concise clinical summary of the case
2. **DIAGNOSIS**: Possible diagnoses (differential diagnosis if applicable)
3. **MANAGEMENT**: Recommended management plan including investigations and treatment

**Patient Information:**
- Name: {consultation.patient_name}
- Age: {consultation.patient_age} years
- Gender: {consultation.patient_gender}
- Chief Complaint: {consultation.chief_complaint}
- Symptoms: {consultation.symptoms_description}
- Duration: {consultation.duration}
"""
        
        if consultation.vital_signs:
            prompt += f"- Vital Signs: {consultation.vital_signs}\n"
        
        if consultation.medical_history:
            prompt += f"- Medical History: {consultation.medical_history}\n"
        
        prompt += """
Respond in the following JSON format:
{
    "summary": "...",
    "diagnosis": "...",
    "management": "..."
}

Respond in """ + consultation.get_language_display() + """ language."""
        
        return prompt
    
    def stream_response(self, consultation):
        """
        Stream the LLM response in real-time
        This is a generator function that yields chunks
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a medical AI assistant. Provide accurate, evidence-based medical information."
                },
                {
                    "role": "user",
                    "content": self.create_prompt(consultation)
                }
            ],
            "stream": True,
            "temperature": 0.3,  # Lower temperature for more focused medical responses
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=60
            )
            response.raise_for_status()
            
            accumulated_text = ""
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        
                        if data == '[DONE]':
                            break
                        
                        try:
                            json_data = json.loads(data)
                            delta = json_data.get('choices', [{}])[0].get('delta', {})
                            content = delta.get('content', '')
                            
                            if content:
                                accumulated_text += content
                                yield content
                        
                        except json.JSONDecodeError:
                            continue
            
            # Parse the final JSON response
            return self._parse_response(accumulated_text)
            
        except Exception as e:
            yield f"Error: {str(e)}"
            return None
    
    def _parse_response(self, text):
        """Parse the LLM response to extract summary, diagnosis, management"""
        try:
            # Try to find JSON in the response
            start = text.find('{')
            end = text.rfind('}') + 1
            
            if start != -1 and end > start:
                json_str = text[start:end]
                data = json.loads(json_str)
                return data
            else:
                # Fallback: parse by sections if JSON parsing fails
                return self._fallback_parse(text)
        
        except json.JSONDecodeError:
            return self._fallback_parse(text)
    
    def _fallback_parse(self, text):
        """Fallback parser if JSON format is not followed"""
        # Simple parsing based on keywords
        summary = ""
        diagnosis = ""
        management = ""
        
        if "SUMMARY" in text or "Summary" in text:
            parts = text.split("DIAGNOSIS" if "DIAGNOSIS" in text else "Diagnosis")
            summary_part = parts[0]
            summary = summary_part.split("SUMMARY")[-1].split("Summary")[-1].strip()
            
            if len(parts) > 1:
                diag_parts = parts[1].split("MANAGEMENT" if "MANAGEMENT" in text else "Management")
                diagnosis = diag_parts[0].strip()
                
                if len(diag_parts) > 1:
                    management = diag_parts[1].strip()
        
        return {
            "summary": summary or text[:len(text)//3],
            "diagnosis": diagnosis or text[len(text)//3:2*len(text)//3],
            "management": management or text[2*len(text)//3:]
        }