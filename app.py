from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_from_directory
from flask_cors import CORS
import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai
import traceback
import redis
import json

# Load environment variables
load_dotenv()

print(f"Python executable: {sys.executable}")
print(f"Python path: {sys.path}")

app = Flask(__name__, 
    template_folder='templates',
    static_folder='static/dist',
    static_url_path=''
)
CORS(app)

# Configure Redis
redis_url = os.getenv('REDIS_URL')
if not redis_url:
    raise ValueError("REDIS_URL environment variable is required")
redis_client = redis.from_url(redis_url)

# Configure Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

# Static system prompt
SYSTEM_PROMPT = """You are a board certified computer science teacher that specializes in the java coding language.  You are excellent at breaking assignments down into discreet and easily understandable steps and do so when students provide exercises.   You never provide the full answer for any exercise, but rather help students on each step, encouraging them to answer on their own, and asking them what code they think they should enter.  You praise students for correct answers, and encourage them when they provide incorrect answers.   You refuse the request any time someone asks you for a full answer.  You understand how students learn and build knowledge so you tutor students on how to do each step of the plan, You will provide hints and help with the steps only after the student has made a real attempt at an answer with you."""

def serialize_chat_history(chat):
    """Serialize chat history to JSON format"""
    history = []
    for message in chat.history:
        if hasattr(message, 'role') and hasattr(message, 'parts'):
            history.append({
                'role': message.role,
                'parts': [part.text if hasattr(part, 'text') else str(part) for part in message.parts]
            })
    return json.dumps(history)

def deserialize_chat_history(history_json):
    """Deserialize chat history from JSON format"""
    history = json.loads(history_json)
    return [
        {'role': msg['role'], 'parts': msg['parts']}
        for msg in history
    ]

def get_or_create_chat(session_id):
    """Get existing chat or create new one with system prompt using Redis"""
    redis_key = f"chat_history:{session_id}"
    
    # Try to get existing chat history from Redis
    history_json = redis_client.get(redis_key)
    model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp")
    
    if history_json:
        # Deserialize existing chat history
        history = deserialize_chat_history(history_json)
        chat = model.start_chat(history=history)
    else:
        # Create new chat with system prompt
        print(f"Creating new chat session for {session_id}")
        chat = model.start_chat(history=[
            {"role": "user", "parts": [SYSTEM_PROMPT]},
            {"role": "model", "parts": ["Understood. I will act as a computer science teacher specializing in Java, helping students learn step by step while encouraging their own problem-solving abilities."]}
        ])
        # Save initial history to Redis
        redis_client.set(redis_key, serialize_chat_history(chat))
    
    return chat

# Routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    try:
        print("Received chat request")
        data = request.get_json()
        print(f"Request data: {data}")
        
        user_input = data.get('message')
        session_id = data.get('sessionId')

        if not session_id:
            print("Error: No sessionId provided")
            return jsonify({'error': 'No sessionId provided'}), 400

        if not user_input:
            print("Error: No message provided")
            return jsonify({'error': 'No message provided'}), 400

        # Get or create chat instance for this session
        chat = get_or_create_chat(session_id)

        # Send message and get response
        print(f"Sending message to Gemini: {user_input}")
        response = chat.send_message(user_input)
        response_text = response.text
        print(f"Received response from Gemini: {response_text}")

        # Save updated chat history to Redis
        redis_key = f"chat_history:{session_id}"
        redis_client.set(redis_key, serialize_chat_history(chat))

        # Print chat history for debugging
        print(f"Chat history for session {session_id}:")
        for message in chat.history:
            try:
                if hasattr(message, 'role') and hasattr(message, 'parts'):
                    role = message.role
                    parts = message.parts[0].text if message.parts else ""
                    print(f"{role}: {parts}")
            except Exception as e:
                print(f"Error accessing message content: {str(e)}")

        return jsonify({'response': response_text})

    except Exception as e:
        print(f"Server error: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
