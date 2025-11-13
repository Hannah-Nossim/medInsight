import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from django.conf import settings
import json
import os


class LocalModelService:
    """
    Service for local FLAN-T5 model inference
    Handles loading, inference, and response parsing
    """
    
    _instance = None
    _model = None
    _tokenizer = None
    _model_loaded = False
    
    def __new__(cls):
        """Singleton pattern to load model once"""
        if cls._instance is None:
            cls._instance = super(LocalModelService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.model_path = getattr(settings, 'LOCAL_MODEL_PATH', None)
        self.device = self._get_device()
        self.max_length = getattr(settings, 'MODEL_MAX_LENGTH', 512)
        self.generation_max_length = getattr(settings, 'GENERATION_MAX_LENGTH', 1024)
    
    def _get_device(self):
        """Determine if GPU is available"""
        if torch.cuda.is_available():
            return 'cuda'
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return 'mps'  # Apple Silicon
        else:
            return 'cpu'
    
    def load_model(self):
        """Load model and tokenizer into memory"""
        if self._model_loaded:
            return True
        
        if not self.model_path or not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Model not found at {self.model_path}. "
                "Please set LOCAL_MODEL_PATH in settings.py"
            )
        
        try:
            print(f"Loading model from {self.model_path}...")
            print(f"Using device: {self.device}")
            
            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            
            # Load model
            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_path,
                device_map=self.device if self.device != 'cpu' else None
            )
            
            if self.device == 'cpu':
                self._model = self._model.to(self.device)
            
            self._model.eval()  # Set to evaluation mode
            self._model_loaded = True
            
            print("Model loaded successfully!")
            return True
            
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            raise
    
    def is_model_loaded(self):
        """Check if model is loaded"""
        return self._model_loaded
    
    def create_prompt(self, consultation):
        """Create a structured prompt for the model"""
        
        # Build the input text
        prompt = f"""You are a medical AI assistant. Analyze the following patient case and provide:
1. A clinical SUMMARY
2. Possible DIAGNOSIS (differential diagnosis if applicable)
3. MANAGEMENT plan (investigations and treatment)

Patient Information:
- Age: {consultation.patient_age} years
- Gender: {consultation.patient_gender}
- Chief Complaint: {consultation.chief_complaint}
- Symptoms: {consultation.symptoms_description}
- Duration: {consultation.duration}"""
        
        if consultation.vital_signs:
            prompt += f"\n- Vital Signs: {consultation.vital_signs}"
        
        if consultation.medical_history:
            prompt += f"\n- Medical History: {consultation.medical_history}"
        
        # Get language name
        language_map = dict(consultation.LANGUAGE_CHOICES)
        language = language_map.get(consultation.language, 'English')
        
        prompt += f"\n\nProvide response in {language} language."
        prompt += "\n\nResponse format:\nSUMMARY: ...\nDIAGNOSIS: ...\nMANAGEMENT: ..."
        
        return prompt
    
    # def generate_response(self, consultation):
    #     """
    #     Generate clinical insights for a consultation
    #     Returns: dict with summary, diagnosis, management
    #     """
    #     if not self._model_loaded:
    #         self.load_model()
        
    #     # Create prompt
    #     prompt = self.create_prompt(consultation)
        
    #     # Tokenize input
    #     inputs = self._tokenizer(
    #         prompt,
    #         return_tensors="pt",
    #         max_length=self.max_length,
    #         truncation=True
    #     ).to(self.device)
        
    #     # Generate response
    #     with torch.no_grad():
    #         outputs = self._model.generate(
    #             **inputs,
    #             max_length=self.generation_max_length,
    #             num_beams=4,
    #             temperature=0.7,
    #             do_sample=True,
    #             top_p=0.9,
    #             early_stopping=True
    #         )
        
    #     # Decode response
    #     response_text = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        
    #     # Parse response into structured format
    #     parsed = self._parse_response(response_text)
        
    #     return parsed
    
    def generate_response(self, consultation):
        """
        Generate clinical insights for a consultation
        CPU-OPTIMIZED version
        Returns: dict with summary, diagnosis, management
        """
        if not self._model_loaded:
            self.load_model()
        
        # Create prompt
        prompt = self.create_prompt(consultation)
        
        # Tokenize input
        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
            max_length=self.max_length,
            truncation=True,
            padding=True
        ).to(self.device)
        
        # CPU-OPTIMIZED: Generate response with speed settings
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_length=512,           # Shorter for speed
                min_length=100,           # Ensure decent output
                num_beams=2,              # Reduced from 4 (faster)
                do_sample=False,          # Deterministic (faster)
                early_stopping=True,      # Stop when done
                no_repeat_ngram_size=3,   # Avoid repetition
                length_penalty=1.0,
                num_return_sequences=1
            )
        
        # Decode response
        response_text = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Parse response into structured format
        parsed = self._parse_response(response_text)
        
        return parsed


    def stream_response(self, consultation):
        """
        Generator function for streaming response
        Yields chunks of text as they're generated
        """
        if not self._model_loaded:
            self.load_model()
        
        # Create prompt
        prompt = self.create_prompt(consultation)
        
        # Tokenize input
        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
            max_length=self.max_length,
            truncation=True
        ).to(self.device)
        
        # Generate with streaming
        generated_tokens = []
        
        with torch.no_grad():
            # Generate tokens one by one
            for _ in range(self.generation_max_length):
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=1,
                    num_beams=1,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9
                )
                
                # Get new token
                new_token = outputs[0][-1]
                generated_tokens.append(new_token)
                
                # Decode and yield
                partial_text = self._tokenizer.decode(generated_tokens, skip_special_tokens=True)
                
                # Yield the new chunk
                if len(generated_tokens) > 1:
                    previous_text = self._tokenizer.decode(generated_tokens[:-1], skip_special_tokens=True)
                    new_chunk = partial_text[len(previous_text):]
                    if new_chunk:
                        yield new_chunk
                else:
                    yield partial_text
                
                # Check for end of sequence
                if new_token == self._tokenizer.eos_token_id:
                    break
                
                # Update inputs for next iteration
                inputs = {
                    'input_ids': outputs,
                    'attention_mask': torch.ones_like(outputs)
                }
        
        # Return full text for final parsing
        full_text = self._tokenizer.decode(generated_tokens, skip_special_tokens=True)
        return full_text
    
    def _parse_response(self, text):
        """
        Parse model output into structured format
        Looks for SUMMARY, DIAGNOSIS, MANAGEMENT sections
        """
        text = text.strip()
        
        summary = ""
        diagnosis = ""
        management = ""
        
        # Try to find sections by keywords
        text_upper = text.upper()
        
        # Find SUMMARY
        if "SUMMARY" in text_upper or "CLINICAL SUMMARY" in text_upper:
            summary_start = max(
                text_upper.find("SUMMARY:"),
                text_upper.find("CLINICAL SUMMARY:")
            )
            if summary_start == -1:
                summary_start = text_upper.find("SUMMARY")
            
            diag_start = text_upper.find("DIAGNOSIS", summary_start)
            if diag_start > summary_start and summary_start != -1:
                summary = text[summary_start:diag_start]
                summary = summary.replace("SUMMARY:", "").replace("CLINICAL SUMMARY:", "").strip()
        
        # Find DIAGNOSIS
        if "DIAGNOSIS" in text_upper:
            diag_start = text_upper.find("DIAGNOSIS")
            mgmt_start = text_upper.find("MANAGEMENT", diag_start)
            
            if mgmt_start > diag_start:
                diagnosis = text[diag_start:mgmt_start]
                diagnosis = diagnosis.replace("DIAGNOSIS:", "").strip()
        
        # Find MANAGEMENT
        if "MANAGEMENT" in text_upper:
            mgmt_start = text_upper.find("MANAGEMENT")
            management = text[mgmt_start:]
            management = management.replace("MANAGEMENT:", "").replace("MANAGEMENT PLAN:", "").strip()
        
        # If structured parsing failed, split by length
        if not summary and not diagnosis and not management:
            lines = text.split('\n')
            third = len(lines) // 3
            summary = '\n'.join(lines[:third])
            diagnosis = '\n'.join(lines[third:2*third])
            management = '\n'.join(lines[2*third:])
        
        return {
            "summary": summary.strip(),
            "diagnosis": diagnosis.strip(),
            "management": management.strip()
        }
    
    def test_model(self):
        """Test if model can generate output"""
        try:
            if not self._model_loaded:
                self.load_model()
            
            # Simple test input
            test_input = "A 30 year old patient with fever and cough for 3 days."
            inputs = self._tokenizer(
                test_input,
                return_tensors="pt",
                max_length=128,
                truncation=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_length=100,
                    num_beams=2
                )
            
            response = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
            return True, f"Model working! Test output: {response[:100]}..."
            
        except Exception as e:
            return False, f"Model test failed: {str(e)}"
    
    def get_model_info(self):
        """Get information about the loaded model"""
        if not self._model_loaded:
            return {
                'loaded': False,
                'path': self.model_path,
                'device': self.device
            }
        
        return {
            'loaded': True,
            'path': self.model_path,
            'device': self.device,
            'model_type': self._model.config.model_type,
            'vocab_size': self._model.config.vocab_size,
            'max_length': self.max_length
        }