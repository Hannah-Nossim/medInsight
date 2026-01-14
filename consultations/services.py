import os
import re
import json
import sys
from django.conf import settings
from huggingface_hub import InferenceClient

class LLMService:
    """Service for Hugging Face Inference API"""
    
    def __init__(self):
        # Get token from environment
        self.api_token = os.environ.get("HF_TOKEN")
        self.repo_id = "Nossim/my-t5-finetuned"
        
        if not self.api_token:
            print("WARNING: HF_TOKEN not set!", file=sys.stderr)
            self.client = None
        else:
            print(f"[HF] Initializing client for {self.repo_id}", file=sys.stderr)
            self.client = InferenceClient(model=self.repo_id, token=self.api_token)

    def create_prompt(self, consultation):
        """Create prompt from clinical case"""
        return f"summarize: {consultation.clinical_case}"

    def stream_response(self, consultation):
        """
        Stream response from Hugging Face API
        Yields individual tokens
        """
        if not self.client:
            raise Exception("HF_TOKEN not configured. Set it in Railway environment variables.")

        prompt = self.create_prompt(consultation)
        print(f"[HF] Sending prompt ({len(prompt)} chars)", file=sys.stderr)
        
        full_response = ""

        try:
            # Call Hugging Face API with streaming
            stream = self.client.text_generation(
                prompt, 
                max_new_tokens=512,
                temperature=0.7,
                stream=True
            )

            token_count = 0
            for token in stream:
                # Handle different token formats
                if isinstance(token, str):
                    content = token
                else:
                    content = token.token.text
                
                yield content
                full_response += content
                token_count += 1
            
            print(f"[HF] Received {token_count} tokens", file=sys.stderr)

            # Parse and save to database
            parsed = self._parse_response(full_response)
            
            consultation.summary = parsed['summary']
            consultation.diagnosis = parsed['diagnosis']
            consultation.management = parsed['management']
            consultation.save()
            
            print(f"[HF] Saved consultation #{consultation.pk}", file=sys.stderr)

        except Exception as e:
            print(f"[HF ERROR] {str(e)}", file=sys.stderr)
            raise Exception(f"Hugging Face API failed: {str(e)}")

    def _parse_response(self, text):
        """Parse model output into structured sections"""
        text = text.strip()
        
        summary = ""
        diagnosis = ""
        management = ""

        # Case-insensitive regex
        diag_match = re.search(r'diagnosis[:\s]*', text, re.IGNORECASE)
        mgmt_match = re.search(r'management[:\s]*', text, re.IGNORECASE)

        if diag_match and mgmt_match:
            # All three sections found
            summary = text[:diag_match.start()].replace("Summary:", "").replace("SUMMARY:", "").strip()
            diagnosis = text[diag_match.end():mgmt_match.start()].strip()
            management = text[mgmt_match.end():].strip()
            
        elif diag_match:
            # Only summary and diagnosis
            summary = text[:diag_match.start()].replace("Summary:", "").replace("SUMMARY:", "").strip()
            diagnosis = text[diag_match.end():].strip()
            
        else:
            # No structure found, put everything in summary
            summary = text

        return {
            "summary": summary,
            "diagnosis": diagnosis,
            "management": management
        }
