
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def test_gemini_model(model_name):
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("Skipping Gemini test: No GOOGLE_API_KEY found.")
        return

    print(f"Testing Gemini Model: {model_name}...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello, this is a connectivity test. Respond with 'OK'.")
        print(f"✅ Success! Response: {response.text.strip()}")
        return True
    except Exception as e:
        print(f"❌ Failed to reach {model_name}: {e}")
        return False

if __name__ == "__main__":
    # Test the user-requested model
    test_gemini_model("gemini-2.5-pro")
    
    # Also test the known working one just in case
    # test_gemini_model("gemini-1.5-pro")
