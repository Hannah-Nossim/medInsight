import os
import sys
import json
import re
from django.conf import settings
from gradio_client import Client  # <--- MUST use this for Spaces

class MLService:
    """
    Service for connecting to your Hugging Face Gradio Space.
    """
    
    def __init__(self):
        # 1. Point to your SPACE name (not the URL, just 'username/space')
        self.space_id = "sankaire/MedInsight-App" 
        
        # Load Token
        self.api_token = os.environ.get("HF_TOKEN")
        
        print(f"[ML Service] Connecting to Space: {self.space_id}...", file=sys.stderr)
        
        try:
            # Initialize Gradio Client
            self.client = Client(self.space_id, hf_token=self.api_token)
            print("[ML Service] Connected successfully!", file=sys.stderr)
        except Exception as e:
            self.client = None
            print(f"[ML Service] Connection Failed: {e}", file=sys.stderr)

    def stream_response(self, consultation):
        """
        Sends text to the Gradio Space and returns the result.
        """
        if not self.client:
            yield "Error: Could not connect to AI Service."
            return

        # 2. Prepare the input
        # Note: We don't need the "Bossy Prompt" here if your Gradio App 
        # already adds it inside app.py. Just send the case.
        input_text = consultation.clinical_case
        
        print(f"[ML Service] Sending case...", file=sys.stderr)
        full_response = ""

        try:
            # 3. Call the Gradio Function
            # CHECK: Does your Space use /predict or /medinsight_response?
            # Go to your Space -> Footer -> "Use via API" to check.
            result = self.client.predict(
                input_text,           
                api_name="/predict"   
            )

            # Gradio Client returns the full string at once.
            full_response = str(result)
            
            # Send to frontend
            yield full_response

            # 4. Save to Database
            parsed_data = self._parse_response(full_response)
            consultation.summary = parsed_data['summary']
            consultation.diagnosis = parsed_data['diagnosis']
            consultation.management = parsed_data['management']
            consultation.save()
            print(f"[ML Service] Saved consultation #{consultation.pk}", file=sys.stderr)

        except Exception as e:
            print(f"[ML Service Error] {str(e)}", file=sys.stderr)
            raise Exception(f"AI Service Failed: {str(e)}")

    def _parse_response(self, text):
        """
        Parses the output into sections (Summary, Diagnosis, Management).
        """
        text = text.strip()
        summary = ""
        diagnosis = ""
        management = ""

        # Case-insensitive search
        diag_match = re.search(r'diagnosis[:\s]+', text, re.IGNORECASE)
        mgmt_match = re.search(r'management[:\s]+', text, re.IGNORECASE)

        if diag_match and mgmt_match:
            summary = text[:diag_match.start()].replace("Summary:", "").strip()
            diagnosis = text[diag_match.end():mgmt_match.start()].strip()
            management = text[mgmt_match.end():].strip()
        elif diag_match:
            summary = text[:diag_match.start()].replace("Summary:", "").strip()
            diagnosis = text[diag_match.end():].strip()
        else:
            summary = text

        return {
            "summary": summary,
            "diagnosis": diagnosis,
            "management": management
        }