import os
import re
import json
from django.conf import settings
from huggingface_hub import InferenceClient

class LLMService:
    """
    Service to interact with Hugging Face Inference API.
    Refactored to support the single 'clinical_case' input field.
    """
    
    def __init__(self):
        # 1. Get Token: Try environment variable first, then Django settings
        self.api_token = os.environ.get("HF_TOKEN") or getattr(settings, 'HF_API_TOKEN', None)
        
        # 2. Your specific model repo on Hugging Face
        self.repo_id = "Nossim/my-t5-finetuned"
        
        if self.api_token:
            self.client = InferenceClient(model=self.repo_id, token=self.api_token)
        else:
            self.client = None
            print("Warning: HF_TOKEN not found. LLMService will fail if called.")

    def create_prompt(self, consultation):
        """
        Create the prompt using the single clinical case text.
        """
        # T5 models usually work best with a simple prefix
        return f"summarize: {consultation.clinical_case}"

    def stream_response(self, consultation):
        """
        Stream the LLM response in real-time.
        Yields text chunks for the frontend and saves the final result to DB.
        """
        if not self.client:
            yield 'data: {"type": "error", "message": "Server Config Error: HF_TOKEN missing"}\n\n'
            return

        prompt = self.create_prompt(consultation)
        full_response = ""

        try:
            # Call HF API with streaming
            stream = self.client.text_generation(
                prompt, 
                max_new_tokens=512, 
                stream=True
            )

            for token in stream:
                # Handle different token formats (string vs object)
                content = token if isinstance(token, str) else token.token.text
                
                # Yield pure text content for the view to wrap in JSON
                yield content
                full_response += content

            # After streaming is done, parse and save to Database
            parsed_data = self._parse_response(full_response)
            
            consultation.summary = parsed_data['summary']
            consultation.diagnosis = parsed_data['diagnosis']
            consultation.management = parsed_data['management']
            consultation.save()

        except Exception as e:
            # Propagate error string
            raise Exception(f"HF API Error: {str(e)}")

    def _parse_response(self, text):
        """
        Parse the raw model output text using Regex.
        Matches: 'Summary: ... Diagnosis: ... Management: ...'
        """
        text = text.strip()
        
        summary = ""
        diagnosis = ""
        management = ""

        # Case-insensitive Regex search
        diag_match = re.search(r'diagnosis[:\s]+', text, re.IGNORECASE)
        mgmt_match = re.search(r'management[:\s]+', text, re.IGNORECASE)

        if diag_match and mgmt_match:
            # 1. Summary (Start -> Diagnosis)
            summary_end = diag_match.start()
            summary = text[:summary_end].replace("Summary:", "").strip()
            
            # 2. Diagnosis (Diagnosis -> Management)
            diag_start = diag_match.end()
            diag_end = mgmt_match.start()
            diagnosis = text[diag_start:diag_end].strip()
            
            # 3. Management (Management -> End)
            mgmt_start = mgmt_match.end()
            management = text[mgmt_start:].strip()
            
        elif diag_match:
            # Fallback: Diagnosis found, but no Management
            summary_end = diag_match.start()
            summary = text[:summary_end].replace("Summary:", "").strip()
            diagnosis = text[diag_match.end():].strip()
            
        else:
            # Fallback: No keywords found, treat whole text as summary
            summary = text

        return {
            "summary": summary,
            "diagnosis": diagnosis,
            "management": management
        }