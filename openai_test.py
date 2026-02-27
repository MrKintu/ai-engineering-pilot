import os
from openai import OpenAI
from dotenv import load_dotenv

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables.")
        print("Please ensure you have a .env file with OPENAI_API_KEY set.")
        return

    print("Initializing OpenAI client...")
    client = OpenAI(api_key=api_key)

    try:
        print("Sending test request to OpenAI (gpt-4o-mini)...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Hello! This is a test call. Please respond with a short confirmation."}
            ],
        )
        
        content = response.choices[0].message.content
        print(f"\Success! OpenAI responded: \n\"{content}\"")
        
    except Exception as e:
        print(f"An error occurred during the API call: {e}")

if __name__ == "__main__":
    main()
