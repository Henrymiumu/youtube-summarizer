import os
from dotenv import load_dotenv # To load environment variables from .env file
from flask import Flask, request, render_template, jsonify # Flask web framework components
from youtube_transcript_api import YouTubeTranscriptApi # To fetch YouTube transcripts
from openai import OpenAI # OpenAI client library (used for OpenRouter)

load_dotenv() # Load environment variables from .env file at the start

# Get API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not found. Check your .env file.")

# Initialize the OpenAI client, pointing to OpenRouter's base URL
client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1"
)

app = Flask(__name__)

# Function to summarize text using the AI model
def summarize_text(text, summary_language='en', summary_style='default'): # Default language is English, style is 'default'
    try:
        # Check text length to avoid exceeding API limits or high costs
        # Note: Token count is more accurate than character count
        max_chars = 12000 # Rough character limit (approx. 3000-4000 tokens)
        if len(text) > max_chars:
             text = text[:max_chars] + "..." # Truncate long text

        # Set system prompt based on target language and style
        style_instruction = ""
        if summary_style == 'interesting':
            style_instruction_en = " Make the summary engaging and highlight surprising or captivating points."
            style_instruction_zh = " 使摘要更引人入勝，並強調令人驚訝或吸引人的觀點。"
            style_instruction = style_instruction_zh if summary_language == 'zh-Hant' else style_instruction_en
        elif summary_style == 'detailed':
            style_instruction_en = " Provide a more detailed summary, including key arguments and examples."
            style_instruction_zh = " 提供更詳細的摘要，包含關鍵論點和例子。"
            style_instruction = style_instruction_zh if summary_language == 'zh-Hant' else style_instruction_en
        elif summary_style == 'concise':
            style_instruction_en = " Provide a very brief and concise summary, focusing only on the main topic."
            style_instruction_zh = " 提供非常簡短扼要的摘要，僅關注核心主題。"
            style_instruction = style_instruction_zh if summary_language == 'zh-Hant' else style_instruction_en

        if summary_language == 'zh-Hant':
            base_prompt = "你是一個擅長總結 YouTube 影片字幕的 AI 助理。請用繁體中文回答。"
        else: # Default to English
            base_prompt = "You are an AI assistant skilled at summarizing YouTube video transcripts. Please respond in English."

        system_prompt = base_prompt + style_instruction # Combine base prompt and style instruction
        # print(f"System Prompt: {system_prompt}") # Keep for debugging if needed

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                # User prompt can be generic as the system prompt guides the output language/style
                {"role": "user", "content": f"Please provide a summary based on the following YouTube transcript content:\n\n{text}"}
            ],
            max_tokens=1000, # Limit output tokens to fit budget/free tier
            temperature=0.7 # Controls randomness
        )

        # --- Debug: Print API Response (Optional) ---
        # print("--- OpenRouter API Response ---")
        # print(response)
        # print("-----------------------------")
        # ------------------------------------------

        # Check if the response is valid and contains choices
        if response and response.choices and len(response.choices) > 0 and response.choices[0].message:
            summary = response.choices[0].message.content
            if summary:
                 return summary.strip()
            else:
                 print("API returned empty message content")
                 return "Could not generate summary: API returned empty content."
        else:
            # If response is invalid or choices are empty, return an error message
            print(f"Invalid response or empty choices: {response}") # Log for debugging
            error_message = "Could not generate summary: Received invalid response from AI model."
            # Try to get more specific error details from the response object
            if response and hasattr(response, 'error') and response.error:
                error_message += f" (Details: {response.error})"
            elif response and hasattr(response, 'message') and response.message:
                 error_message += f" (Message: {response.message})"
            return error_message

    except Exception as e:
        print(f"Error during API call: {e}")
        return f"Could not generate summary: {str(e)}"

# Route for the main page
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle the summary generation request
@app.route('/summary', methods=['POST'])
def summary():
    video_url = request.form['video_url']
    summary_language = request.form.get('summary_language', 'en') # Default to 'en'
    summary_style = request.form.get('summary_style', 'default') # Default to 'default'
    try:
        # Extract video ID from URL
        video_id = ''
        if "v=" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in video_url:
             video_id = video_url.split("youtu.be/")[1].split("?")[0]
        else:
            return jsonify({'error': 'Invalid YouTube URL format'}), 400

        # Get available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try fetching preferred languages, fallback to others
        transcript = None
        try:
            # Try zh-Hant first
            transcript = transcript_list.find_generated_transcript(['zh-Hant', 'zh-TW']).fetch()
        except Exception:
             try:
                 # Fallback to English
                 transcript = transcript_list.find_generated_transcript(['en']).fetch()
             except Exception:
                 try:
                     # Fallback to any available transcript
                     available_langs = [t.language for t in transcript_list]
                     if available_langs:
                         transcript = transcript_list.find_transcript(available_langs).fetch()
                     else:
                        return jsonify({'error': 'No transcripts found for this video'}), 400
                 except Exception as e:
                    return jsonify({'error': f'Could not fetch any transcript: {str(e)}'}), 500
        
        if not transcript:
             return jsonify({'error': 'Failed to load transcript data'}), 500

        # Join transcript parts into a single string
        full_transcript = " ".join([item['text'] for item in transcript]) # Reverted based on previous testing? Let's assume item['text'] works now.
        # If item['text'] fails again, change back to item.text

        # Call the AI summarization function
        summary_text = summarize_text(full_transcript, summary_language, summary_style)

        # Return the result as JSON
        return jsonify({'summary': summary_text})

    except YouTubeTranscriptApi.CouldNotRetrieveTranscript:
         return jsonify({'error': 'Could not retrieve transcript. Check video URL or availability.'}), 404
    except Exception as e:
        print(f"Error processing summary request: {e}") # Log the error
        return jsonify({'error': f'An error occurred during processing: {str(e)}'}), 500

# Run the Flask app
if __name__ == '__main__':
    # debug=True enables auto-reload and detailed error pages during development
    # Ensure debug=False for production deployment
    app.run(debug=True)
