# YouTube Summarizer

A simple Flask web application to fetch YouTube video transcripts and generate summaries using an AI model via OpenRouter.

## Features

*   Fetches transcripts for YouTube videos.
*   Generates summaries using a configurable AI model (defaults to gpt-4o-mini via OpenRouter).
*   Supports multiple summary languages (English and Traditional Chinese).
*   Allows choosing different summary styles (Default, Interesting, Detailed, Concise).
*   Simple web interface.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/henrymiumu/youtube-summarizer.git
    cd youtube-summarizer
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create a `.env` file:**
    Create a file named `.env` in the project root directory and add your OpenRouter API key:
    ```
    OPENAI_API_KEY='YOUR_OPENROUTER_API_KEY'
    ```
    Replace `YOUR_OPENROUTER_API_KEY` with your actual key.
    *(This file is ignored by git via `.gitignore` to protect your key)*

## Running the Application

1.  **Start the Flask development server:**
    ```bash
    python app.py
    ```

2.  **Open your web browser** and navigate to `http://127.0.0.1:5000` (or the URL provided in the terminal).

## Usage

1.  Select the desired interface and summary language using the dropdown at the top right.
2.  Paste a valid YouTube video URL into the input field.
3.  Choose the desired summary style using the buttons below the input field.
4.  Click the "Generate Summary" button.
5.  The summary will appear in the "Summary Result" section below.

## Note

*   The application relies on the `youtube-transcript-api` library, which may not be able to fetch transcripts for all videos (e.g., if captions are disabled or auto-generation failed).
*   AI summary generation uses OpenRouter. Ensure you have sufficient credits in your OpenRouter account, especially if requesting long or detailed summaries. The free tier has limitations. 
