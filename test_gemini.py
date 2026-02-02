from dotenv import load_dotenv
import os
import traceback

load_dotenv()
GEMINI_KEY = os.getenv('GEMINI_KEY')

print('GEMINI_KEY set:', bool(GEMINI_KEY))
if not GEMINI_KEY:
    print('No GEMINI_KEY in environment; skipping test.')
    exit(0)

try:
    from google import genai
except Exception as e:
    print('Failed importing google.genai:', e)
    traceback.print_exc()
    exit(2)

try:
    client = genai.Client(api_key=GEMINI_KEY)
    print('Client initialized')
    # Try a small generation; prefer newer model name if available
    for model in ['gemini-2.5-flash', 'gemini-2.1', 'gemini-1.5-flash', 'gemini-1.0']:
        try:
            print('Trying model:', model)
            res = client.models.generate_content(model=model, contents="Say 'OK' only")
            # different library versions expose output differently
            text = getattr(res, 'text', None) or (res.get('output') if isinstance(res, dict) else None)
            print('Model', model, 'response:', text)
            break
        except Exception as me:
            print('Model', model, 'failed:', me)

except Exception as e:
    print('Error during test:', e)
    traceback.print_exc()
    exit(3)

print('Done')
