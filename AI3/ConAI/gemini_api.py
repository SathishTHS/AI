import google.generativeai as genai
import os

from dotenv import load_dotenv
load_dotenv()

from django.contrib import messages

class genai():
    try:
        genai.configure(api_key=os.environ['GEMINI_API_KEY'])
                
        model_name = 'gemini-1.5-flash'
        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 200,
            "response_mime_type": "text/plain",
        }

        model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)
    except Exception as e:
        err = 'Error message: Invalid API {str(e)}'
        messages.error(err)
    