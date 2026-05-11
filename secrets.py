from dotenv import load_dotenv
import os
load_dotenv()


def gemini_api_key():
    secret=os.getenv("GEMINI_API_KEY")
    if secret:
        return secret
    else:
        raise EnvironmentError("Secret dose'nt exist.")

if __name__ == "__main__":
    print(gemini_api_key())