from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_from_directory
from flask_cors import CORS
import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai
import traceback
import json
from datetime import datetime, timedelta

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

# Try to initialize Redis if available
try:
    import redis
    REDIS_URL = os.getenv('REDIS_URL')
    if REDIS_URL:
        redis_client = redis.from_url(REDIS_URL)
        print("Successfully connected to Redis")
        USE_REDIS = True
    else:
        print("No REDIS_URL provided, falling back to in-memory storage")
        USE_REDIS = False
except Exception as e:
    print(f"Failed to connect to Redis, falling back to in-memory storage: {str(e)}")
    USE_REDIS = False

# Configure Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is required")

genai.configure(api_key=GOOGLE_API_KEY)

# Static system prompt
SYSTEM_PROMPT = """You are a board certified computer science teacher that specializes in the java coding language.  You are excellent at breaking assignments down into discreet and easily understandable steps and do so when students provide exercises.   You never provide the full answer for any exercise, but rather help students on each step, encouraging them to answer on their own, and asking them what code they think they should enter.  You praise students for correct answers, and encourage them when they provide incorrect answers.   You refuse the request any time someone asks you for a full answer.  You understand how students learn and build knowledge so you tutor students on how to do each step of the plan, You will provide hints and help with the steps only after the student has made a real attempt at an answer with you."""

# In-memory storage fallback
chat_sessions = {}

class ChatSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp")
        self.history = [
            {"role": "user", "parts": [SYSTEM_PROMPT]},
            {"role": "model", "parts": ["Understood. I will act as a computer science teacher specializing in Java, helping students learn step by step while encouraging their own problem-solving abilities."]}
        ]
        self.last_accessed = datetime.utcnow()

    def to_dict(self):
        return {
            'history': self.history,
            'last_accessed': self.last_accessed.isoformat()
        }

    @classmethod
    def from_dict(cls, session_id, data):
        session = cls(session_id)
        session.history = data['history']
        session.last_accessed = datetime.fromisoformat(data['last_accessed'])
        return session

def get_or_create_chat(session_id):
    """Get existing chat or create new one with system prompt"""
    try:
        chat_session = None
        
        if USE_REDIS:
            # Try to get existing session from Redis
            session_data = redis_client.get(f"chat_session:{session_id}")
            if session_data:
                session_dict = json.loads(session_data)
                chat_session = ChatSession.from_dict(session_id, session_dict)
        else:
            # Use in-memory storage
            if session_id in chat_sessions:
                chat_session = chat_sessions[session_id]
                
        if not chat_session:
            # Create new session
            print(f"Creating new chat session for {session_id}")
            chat_session = ChatSession(session_id)
            
            if USE_REDIS:
                # Save to Redis
                redis_client.set(
                    f"chat_session:{session_id}",
                    json.dumps(chat_session.to_dict())
                )
            else:
                # Save to in-memory
                chat_sessions[session_id] = chat_session

        # Update last accessed time
        chat_session.last_accessed = datetime.utcnow()

        # Initialize chat with current history
        model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp")
        chat = model.start_chat(history=chat_session.history)
        
        return chat, chat_session

    except Exception as e:
        print(f"Error in get_or_create_chat: {str(e)}")
        traceback.print_exc()
        raise

def cleanup_old_sessions():
    """Remove expired sessions"""
    try:
        if USE_REDIS:
            pattern = "chat_session:*"
            for key in redis_client.scan_iter(match=pattern):
                session_data = redis_client.get(key)
                if session_data:
                    session_dict = json.loads(session_data)
                    last_accessed = datetime.fromisoformat(session_dict['last_accessed'])
                    if datetime.utcnow() - last_accessed > timedelta(hours=24):
                        redis_client.delete(key)
        else:
            # Cleanup in-memory sessions
            current_time = datetime.utcnow()
            expired_sessions = [
                session_id for session_id, session in chat_sessions.items()
                if current_time - session.last_accessed > timedelta(hours=24)
            ]
            for session_id in expired_sessions:
                del chat_sessions[session_id]
    except Exception as e:
        print(f"Error in cleanup_old_sessions: {str(e)}")

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
        try:
            chat, chat_session = get_or_create_chat(session_id)
        except Exception as e:
            print(f"Error getting/creating chat: {str(e)}")
            return jsonify({'error': f'Failed to initialize chat: {str(e)}'}), 500

        # Send message and get response
        print(f"Sending message to Gemini: {user_input}")
        try:
            response = chat.send_message(user_input)
            response_text = response.text
            print(f"Received response from Gemini: {response_text}")

            # Update history
            chat_session.history.append({"role": "user", "parts": [user_input]})
            chat_session.history.append({"role": "model", "parts": [response_text]})

            # Save updated session
            if USE_REDIS:
                redis_client.set(
                    f"chat_session:{session_id}",
                    json.dumps(chat_session.to_dict())
                )
            else:
                chat_sessions[session_id] = chat_session

        except Exception as e:
            print(f"Error sending message to Gemini: {str(e)}")
            traceback.print_exc()
            return jsonify({'error': f'Failed to get response from Gemini: {str(e)}'}), 500

        # Clean up old sessions periodically
        cleanup_old_sessions()

        return jsonify({'response': response_text})

    except Exception as e:
        print(f"Server error: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
