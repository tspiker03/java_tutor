from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_from_directory
from flask_cors import CORS
import os
import sys
import subprocess
from dotenv import load_dotenv
import google.generativeai as genai
import traceback
import json
from datetime import datetime, timedelta
from functools import wraps

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

# Load default system prompt and subject from file
with open('optimized_prompt.txt', 'r') as file:
    DEFAULT_SYSTEM_PROMPT = file.read().strip()

# Default subject
DEFAULT_SUBJECT = "Python"

# Admin credentials
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'password')

# In-memory storage for non-Redis environments
in_memory_storage = {
    'system_prompt': None,
    'subject': None
}

def rebuild_frontend():
    """Rebuild the frontend using webpack"""
    try:
        # Get the current working directory
        cwd = os.getcwd()
        print(f"Current working directory: {cwd}")
        
        # List files in current directory
        print("Files in current directory:")
        for file in os.listdir(cwd):
            print(f"- {file}")
        
        # Check if package.json exists
        if not os.path.exists('package.json'):
            print("Error: package.json not found")
            return False
            
        # Run npm build with explicit error output
        result = subprocess.run(
            ['npm', 'run', 'build'],
            capture_output=True,
            text=True,
            check=False
        )
        
        # Log the output
        print("Build output:")
        print(result.stdout)
        if result.stderr:
            print("Build errors:")
            print(result.stderr)
            
        # Check if build was successful
        if result.returncode != 0:
            print(f"Build failed with return code: {result.returncode}")
            return False
            
        return True
    except Exception as e:
        print(f"Error rebuilding frontend: {str(e)}")
        traceback.print_exc()
        return False

def get_system_prompt():
    """Get system prompt from Redis/memory or fallback to default"""
    try:
        if USE_REDIS:
            prompt = redis_client.get('system_prompt')
            if prompt:
                return prompt.decode('utf-8')
        elif in_memory_storage['system_prompt']:
            return in_memory_storage['system_prompt']
        return DEFAULT_SYSTEM_PROMPT
    except Exception as e:
        print(f"Error getting system prompt: {str(e)}")
        return DEFAULT_SYSTEM_PROMPT

def get_subject():
    """Get subject from Redis/memory or fallback to default"""
    try:
        if USE_REDIS:
            subject = redis_client.get('subject')
            if subject:
                return subject.decode('utf-8')
        elif in_memory_storage['subject']:
            return in_memory_storage['subject']
        return DEFAULT_SUBJECT
    except Exception as e:
        print(f"Error getting subject: {str(e)}")
        return DEFAULT_SUBJECT

def set_system_prompt(prompt, set_as_default=False):
    """Set system prompt in Redis/memory and optionally as default"""
    try:
        if set_as_default:
            # Write to optimized_prompt.txt
            with open('optimized_prompt.txt', 'w') as file:
                file.write(prompt)
        
        if USE_REDIS:
            redis_client.set('system_prompt', prompt)
        else:
            in_memory_storage['system_prompt'] = prompt
        return True
    except Exception as e:
        print(f"Error setting system prompt: {str(e)}")
        return False

def set_subject(subject):
    """Set subject in Redis/memory and trigger rebuild"""
    try:
        # First store the subject
        if USE_REDIS:
            redis_client.set('subject', subject)
        else:
            in_memory_storage['subject'] = subject
        
        # Attempt rebuild but don't fail if it doesn't work
        # This allows subject changes to work even if rebuild fails
        try:
            rebuild_success = rebuild_frontend()
            if not rebuild_success:
                print("Warning: Frontend rebuild failed but subject was updated")
        except Exception as rebuild_error:
            print(f"Warning: Frontend rebuild error: {str(rebuild_error)}")
            traceback.print_exc()
        
        return True
    except Exception as e:
        print(f"Error setting subject: {str(e)}")
        return False

def check_auth(username, password):
    """Check if username and password are valid"""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def requires_auth(f):
    """Decorator for requiring HTTP Basic auth"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response(
                'Could not verify your access level for that URL.\n'
                'You have to login with proper credentials', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated

# In-memory storage fallback
chat_sessions = {}

class ChatSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp")
        system_prompt = get_system_prompt()
        subject = get_subject()
        self.history = [
            {"role": "user", "parts": [system_prompt]},
            {"role": "model", "parts": [f"Understood. I will act as a teacher specializing in {subject}, helping students learn step by step while encouraging their own problem-solving abilities."]}
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

@app.route('/api/rebuild', methods=['POST'])
@requires_auth
def rebuild_endpoint():
    """Endpoint to manually trigger frontend rebuild"""
    try:
        if rebuild_frontend():
            return jsonify({'status': 'success', 'message': 'Frontend rebuilt successfully'})
        return jsonify({'status': 'error', 'message': 'Failed to rebuild frontend'}), 500
    except Exception as e:
        print(f"Error in rebuild endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subject', methods=['GET'])
def get_subject_endpoint():
    """Get current subject"""
    try:
        subject = get_subject()
        return jsonify({'subject': subject})
    except Exception as e:
        print(f"Error getting subject: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/prompt', methods=['GET', 'POST'])
@requires_auth
def admin_prompt():
    if request.method == 'GET':
        current_prompt = get_system_prompt()
        current_subject = get_subject()
        return render_template('admin_prompt.html', 
                             current_prompt=current_prompt,
                             default_prompt=DEFAULT_SYSTEM_PROMPT,
                             current_subject=current_subject)
    else:
        new_prompt = request.form.get('prompt')
        new_subject = request.form.get('subject')
        set_as_default = request.form.get('set_as_default') == 'true'
        
        success = True
        message = []
        
        if new_prompt:
            if set_system_prompt(new_prompt, set_as_default):
                message.append('Prompt updated successfully')
            else:
                success = False
                message.append('Failed to update prompt')
        
        if new_subject:
            if set_subject(new_subject):
                message.append('Subject updated successfully')
            else:
                success = False
                message.append('Failed to update subject')
        
        if not (new_prompt or new_subject):
            return jsonify({'status': 'error', 'message': 'No updates provided'}), 400
            
        return jsonify({
            'status': 'success' if success else 'error',
            'message': ' and '.join(message)
        }), 200 if success else 500

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
