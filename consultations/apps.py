from django.apps import AppConfig
from transformers import T5Tokenizer, T5ForConditionalGeneration

class ConsultationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'consultations'

    # 1. Global variables to hold the model in memory
    model = None
    tokenizer = None

    def ready(self):
        # 2. This runs once when the server starts
        # It prevents reloading the model on every user click
        model_repo = "Nossim/my-t5-finetuned" 
        
        print(f"Downloading/Loading model from {model_repo}...")
        
        try:
            # Load tokenizer and model from your Hugging Face repo
            self.tokenizer = T5Tokenizer.from_pretrained(model_repo)
            self.model = T5ForConditionalGeneration.from_pretrained(model_repo)
            print(" Model loaded successfully!")
        except Exception as e:
            print(f" Error loading model: {e}")