import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5030"))
    print("PORT", port)
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    print("LOG_LEVEL", log_level)
    print("BASE_URL_LLM", os.getenv("BASE_URL_LLM"))
    print("MODEL_NAME", os.getenv("MODEL_NAME"))

    # Start the FastAPI server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level=log_level,
        reload=True
    )
