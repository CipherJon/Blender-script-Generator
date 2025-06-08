from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
import httpx
import os
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional
import time
from datetime import datetime
import json

# Load environment variables
load_dotenv()

app = FastAPI(title="Blender Script Generator")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Rate limiting
RATE_LIMIT_WINDOW = 60  # 1 minute
RATE_LIMIT_MAX_REQUESTS = 10
request_history = {}

class ScriptRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=1000)

    class Config:
        from_attributes = True

class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None

def check_rate_limit(request: Request) -> bool:
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean old requests
    if client_ip in request_history:
        request_history[client_ip] = [t for t in request_history[client_ip] 
                                    if current_time - t < RATE_LIMIT_WINDOW]
    
    # Check rate limit
    if client_ip in request_history and len(request_history[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    
    # Add new request
    if client_ip not in request_history:
        request_history[client_ip] = []
    request_history[client_ip].append(current_time)
    
    return True

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html") as f:
        return f.read()

@app.post("/generate", response_model=dict)
async def generate_script(request: Request, script_request: ScriptRequest):
    # Check rate limit
    if not check_rate_limit(request):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a minute before trying again."
        )

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenRouter API key not configured"
        )

    print(f"Processing request with prompt: {script_request.prompt[:100]}...")  # Log first 100 chars of prompt

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/yourusername/blender-script-generator",
                    "X-Title": "Blender Script Generator"
                },
                json={
                    "model": "google/gemini-2.0-flash-exp:free",
                    "messages": [
                        {
                            "role": "system",
                            "content": """You are a Python Blender script expert. Generate ONLY the Python code for Blender, without any explanations or instructions.
                            The code must:
                            1. Start with 'import bpy' and other necessary imports
                            2. Include proper error handling
                            3. Follow Blender's Python API conventions
                            4. Be properly documented with comments
                            5. Include type hints
                            6. Follow PEP 8 style
                            7. Be production-ready and efficient
                            
                            DO NOT include any markdown formatting, explanations, or instructions in your response.
                            Output ONLY the Python code that can be directly used in Blender."""
                        },
                        {
                            "role": "user",
                            "content": f"Generate a Blender Python script for: {script_request.prompt}"
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000,
                    "top_p": 0.95,
                    "frequency_penalty": 0.1,
                    "presence_penalty": 0.1,
                    "stop": ["```", "'''", '"""']
                }
            )
            response.raise_for_status()
            result = response.json()
            
            # Log the response structure
            print("API Response structure:", json.dumps(result, indent=2))
            
            if not result.get("choices") or not result["choices"][0].get("message", {}).get("content"):
                raise HTTPException(
                    status_code=500,
                    detail="Invalid response format from AI model"
                )
            
            script_content = result["choices"][0]["message"]["content"]
            
            # Log successful generation
            log_generation(script_request.prompt, script_content)
            
            return {
                "script": script_content,
                "model": "google/gemini-2.0-flash-exp:free",
                "timestamp": datetime.now().isoformat()
            }
            
        except httpx.TimeoutException:
            print("Request timed out")
            raise HTTPException(
                status_code=504,
                detail="Request timed out. Please try again."
            )
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {str(e)}")
            error_detail = f"OpenRouter API error: {str(e)}"
            if e.response.status_code == 429:
                error_detail = "Rate limit exceeded. Please try again later."
            raise HTTPException(
                status_code=e.response.status_code,
                detail=error_detail
            )
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred: {str(e)}"
            )

def log_generation(prompt: str, script: str):
    """Log successful script generations to a file."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "script": script
    }
    
    log_file = Path("generation_logs.json")
    try:
        if log_file.exists():
            with open(log_file, "r") as f:
                logs = json.load(f)
        else:
            logs = []
        
        logs.append(log_entry)
        
        # Keep only last 1000 generations
        if len(logs) > 1000:
            logs = logs[-1000:]
        
        with open(log_file, "w") as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"Failed to log generation: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 