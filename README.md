# Blender Script Generator

A web application that generates Python Blender scripts using AI models through OpenRouter.

## Features

- Generate Blender scripts using AI
- Modern web interface
- Real-time script generation
- Copy to clipboard functionality
- Syntax highlighting

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory with your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```
4. Run the application:
   ```bash
   uvicorn main:app --reload
   ```

## Usage

1. Open your browser and navigate to `http://localhost:8000`
2. Enter your prompt describing the Blender script you want to generate
3. Click "Generate" and wait for the AI to create your script
4. Copy the generated script and use it in Blender

## Requirements

- Python 3.8+
- OpenRouter API key
- Modern web browser

## License

MIT License
