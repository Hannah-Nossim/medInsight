from django.apps import AppConfig
class ConsultationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'consultations'

    def ready(self):
        print("System ready. Using Hugging Face Inference API for predictions.")
        pass