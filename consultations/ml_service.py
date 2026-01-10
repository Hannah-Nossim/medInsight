import os
import json
import re
from django.conf import settings
from huggingface_hub import InferenceClient

class MLService:
    """
    Service for Hugging Face Inference API.
    Replaces the local PyTorch model with cloud API calls.
    """
    
    def __init__(self):
        # Load token from environment or settings
        self.api_token = os.environ.get("HF_TOKEN") or getattr(settings, 'HF_API_TOKEN', None)
        # Your specific fine-tuned model on Hugging Face
        self.repo_id = "Nossim/my-t5-finetuned"  
        
        if self.api_token:
            self.client = InferenceClient(model=self.repo_id, token=self.api_token)
        else:
            self.client = None
            print("Warning: HF_TOKEN not found. MLService will fail if called.")

    def create_prompt(self, consultation):
        """
        Create the prompt for the T5 model using the single clinical_case field.
        """
        # T5-base usually expects a specific prefix like "summarize: "
        return f"summarize: {consultation.clinical_case}"

    def stream_response(self, consultation):
        """
        Generator that streams the response from Hugging Face API.
        Yields chunks of text for the frontend.
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
                # Some versions of the library return an object, others a string. Handle both.
                content = token if isinstance(token, str) else token.token.text
                
                # Yield content to the view loop
                yield content
                full_response += content

            # After streaming is done, parse and save the full result
            parsed_data = self._parse_response(full_response)
            
            # Save to Database
            consultation.summary = parsed_data['summary']
            consultation.diagnosis = parsed_data['diagnosis']
            consultation.management = parsed_data['management']
            consultation.save()

        except Exception as e:
            # Raise exception so the view can capture it
            raise Exception(f"HF API Error: {str(e)}")

    def _parse_response(self, text):
        """
        Parse the raw model output text into structured dictionary.
        Expects format like: "Summary: ... Diagnosis: ... Management: ..."
        """
        text = text.strip()
        
        summary = ""
        diagnosis = ""
        management = ""

        # Use Regex to extract sections safely (Case Insensitive)
        diag_match = re.search(r'diagnosis[:\s]+', text, re.IGNORECASE)
        mgmt_match = re.search(r'management[:\s]+', text, re.IGNORECASE)

        if diag_match and mgmt_match:
            # Summary is everything before Diagnosis
            summary_end = diag_match.start()
            summary = text[:summary_end].replace("Summary:", "").strip()
            
            # Diagnosis is everything between Diagnosis and Management
            diag_start = diag_match.end()
            diag_end = mgmt_match.start()
            diagnosis = text[diag_start:diag_end].strip()
            
            # Management is everything after Management
            mgmt_start = mgmt_match.end()
            management = text[mgmt_start:].strip()
            
        elif diag_match:
            # Fallback: Found Diagnosis but not Management
            summary_end = diag_match.start()
            summary = text[:summary_end].replace("Summary:", "").strip()
            diagnosis = text[diag_match.end():].strip()
            
        else:
            # Fallback: No structure found, put everything in Summary
            summary = text

        return {
            "summary": summary,
            "diagnosis": diagnosis,
            "management": management
        }