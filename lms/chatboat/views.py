import os
import logging
import markdown
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import google.generativeai as genai

# Load the API key (ensure your settings.py or environment is configured)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@csrf_exempt
def chatAPI(request):
    if request.method != "POST":
        return HttpResponse("Bad Request", status=400)

    try:
        prompt = request.POST.get("prompt", "").strip()
        if not prompt:
            return JsonResponse({"error": "Prompt cannot be empty."}, status=400)

        # Use a supported Gemini model
        model = genai.GenerativeModel("gemini-2.5-flash")  # <-- updated model ID

        logger.info(f"User prompt: {prompt}")

        response = model.generate_content(prompt)
        ai_response = (response.text or "").strip()

        if not ai_response:
            logger.warning("Empty response from Gemini API.")
            return JsonResponse({"error": "No response generated."}, status=500)

        ai_response_html = markdown.markdown(ai_response)
        logger.info(f"Gemini response (preview): {ai_response[:100]}...")

        return JsonResponse({"response": ai_response_html})

    except Exception as e:
        logger.exception(f"Error in chatAPI: {str(e)}")
        return JsonResponse({"error": "Internal Server Error"}, status=500)
