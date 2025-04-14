import os
from dotenv import load_dotenv # 導入 load_dotenv
from flask import Flask, request, render_template, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

load_dotenv() # 載入 .env 文件中的環境變數

# 從環境變數讀取 API 金鑰
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("找不到 OPENAI_API_KEY 環境變數。請檢查你的 .env 檔案。")

# 使用讀取到的金鑰，並指定 OpenRouter 的 base_url
client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1" 
)

app = Flask(__name__)

def summarize_text(text, summary_language='en', summary_style='default'): # 預設風格為 'default'
    try:
        # 檢查文字長度，避免過長輸入導致 API 錯誤或費用過高
        # OpenAI GPT-3.5 Turbo 的 context window 大約是 4096 tokens
        # 這裡簡單用字數限制，但 token 數更準確
        max_chars = 12000 # 粗略限制，約等於 3000-4000 tokens
        if len(text) > max_chars:
             text = text[:max_chars] + "..." # 截斷過長文字

        # 根據目標語言和風格設定 system prompt
        style_instruction = ""
        if summary_style == 'interesting':
            style_instruction = " Make the summary engaging and highlight surprising or captivating points."
            if summary_language == 'zh-Hant':
                 style_instruction = " 使摘要更引人入勝，並強調令人驚訝或吸引人的觀點。"
        elif summary_style == 'detailed':
            style_instruction = " Provide a more detailed summary, including key arguments and examples."
            if summary_language == 'zh-Hant':
                style_instruction = " 提供更詳細的摘要，包含關鍵論點和例子。"
        elif summary_style == 'concise':
            style_instruction = " Provide a very brief and concise summary, focusing only on the main topic."
            if summary_language == 'zh-Hant':
                 style_instruction = " 提供非常簡短扼要的摘要，僅關注核心主題。"

        if summary_language == 'zh-Hant':
            base_prompt = "你是一個擅長總結 YouTube 影片字幕的 AI 助理。請用繁體中文回答。"
        else: # 預設或其他情況使用英文
            base_prompt = "You are an AI assistant skilled at summarizing YouTube video transcripts. Please respond in English."
        
        system_prompt = base_prompt + style_instruction # 組合基礎提示和風格指示
        print(f"System Prompt: {system_prompt}") # 偵錯用

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Please provide a summary based on the following YouTube transcript content:\n\n{text}"} # User prompt 可以通用
            ],
            max_tokens=1000, # 重新加入長度限制以符合額度
            temperature=0.7 # 控制輸出的隨機性
        )

        # --- 偵錯：列印 API 回應 --- 
        print("--- OpenRouter API Response ---")
        print(response)
        print("-----------------------------")
        # -------------------------------

        # 檢查回應是否有效且包含 choices
        if response and response.choices and len(response.choices) > 0 and response.choices[0].message:
            summary = response.choices[0].message.content
            if summary:
                 return summary.strip()
            else:
                 print("API 返回的訊息內容為空")
                 return "無法產生摘要：API 返回的內容為空。"
        else:
            # 如果回應無效或 choices 為空，返回錯誤訊息
            print(f"無效的回應或空的 choices: {response}") # Log 供偵錯
            error_message = "無法產生摘要：從 AI 模型收到無效的回應。"
            if response and hasattr(response, 'error') and response.error:
                error_message += f" (錯誤詳情: {response.error})"
            elif response and hasattr(response, 'message') and response.message:
                 error_message += f" (訊息: {response.message})"
            return error_message

    except Exception as e:
        print(f"OpenAI API 錯誤: {e}")
        return f"無法產生摘要: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/summary', methods=['POST'])
def summary():
    video_url = request.form['video_url']
    summary_language = request.form.get('summary_language', 'en')
    summary_style = request.form.get('summary_style', 'default') # 獲取選擇的風格，預設為 'default'
    try:
        video_id = ''
        if "v=" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in video_url:
             video_id = video_url.split("youtu.be/")[1].split("?")[0]
        else:
            return jsonify({'error': '無效的 YouTube 網址格式'}), 400

        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # 嘗試獲取中文繁體字幕，如果沒有則獲取英文或其他可用字幕
        try:
            transcript = transcript_list.find_generated_transcript(['zh-Hant', 'zh-TW']).fetch()
        except:
             try:
                 transcript = transcript_list.find_generated_transcript(['en']).fetch()
             except Exception as e:
                 # 如果找不到 zh-Hant 和 en，嘗試獲取任何可用的字幕
                 available_transcripts = [t.language for t in transcript_list]
                 if not available_transcripts:
                     return jsonify({'error': f'找不到該影片的字幕'}), 400
                 transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[available_transcripts[0]])


        # 使用 item.text 而非 item['text'] 來兼容可能的物件類型
        full_transcript = " ".join([item.text for item in transcript])

        # 呼叫 AI 進行摘要，傳入目標語言和風格
        summary_text = summarize_text(full_transcript, summary_language, summary_style)

        return jsonify({'summary': summary_text})

    except Exception as e:
        return jsonify({'error': f'處理時發生錯誤: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
