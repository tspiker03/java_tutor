from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_from_directory, redirect, url_for
import os
import sys
import redis
from dotenv import load_dotenv
import google.generativeai as genai
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, set_access_cookies, unset_jwt_cookies, verify_jwt_in_request
from functools import wraps
from datetime import timedelta

# Initialize Redis with fallback to in-memory storage
redis_client = None
in_memory_prompts = {}
in_memory_current_prompt = DEFAULT_SYSTEM_PROMPT = """You are a board certified computer science teacher that specializes in teaching Java programming. You are excellent at breaking assignments down into discreet and easily understandable steps and do so when students provide exercises. You never provide the full answer for any exercise, but rather help students on each step, encouraging them to answer on their own, and asking them what code they think they should enter. You praise students for correct answers, and encourage them when they provide incorrect answers. You refuse the request any time someone asks you for a full answer. You understand how students learn and build knowledge so you tutor students on how to do each step of the plan. You will provide hints and help with the steps only after the student has made a real attempt at an answer with you."""
in_memory_current_subject = "Java"

# Load environment variables
load_dotenv()

try:
    redis_url = os.getenv('REDIS_URL')  # Railway provides Redis URL
    if redis_url:
        redis_client = redis.from_url(redis_url, decode_responses=True)
    else:
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True
        )
    # Test connection
    redis_client.ping()
    print("Successfully connected to Redis")
except (redis.ConnectionError, redis.ResponseError) as e:
    print(f"Redis connection failed, falling back to in-memory storage: {str(e)}")
    redis_client = None

def load_saved_prompts():
    """Load saved prompts from Redis or memory"""
    if redis_client:
        try:
            prompts = redis_client.hgetall('prompts')
            print(f"Loaded prompts from Redis: {prompts}")
            return prompts if prompts else {}
        except Exception as e:
            print(f"Error loading prompts from Redis: {str(e)}")
            print(f"Falling back to in-memory prompts: {in_memory_prompts}")
            return in_memory_prompts
    print(f"Using in-memory prompts: {in_memory_prompts}")
    return in_memory_prompts

def save_prompt(name, prompt):
    """Save a prompt to Redis or memory"""
    global in_memory_prompts
    if redis_client:
        try:
            redis_client.hset('prompts', name, prompt)
            print(f"Saved prompt '{name}' to Redis")
        except Exception as e:
            print(f"Error saving prompt to Redis: {str(e)}")
            in_memory_prompts[name] = prompt
            print(f"Saved prompt '{name}' to memory")
    else:
        in_memory_prompts[name] = prompt
        print(f"Saved prompt '{name}' to memory")

def delete_prompt(name):
    """Delete a prompt from Redis or memory"""
    global in_memory_prompts
    if redis_client:
        try:
            redis_client.hdel('prompts', name)
            print(f"Deleted prompt '{name}' from Redis")
        except Exception as e:
            print(f"Error deleting prompt from Redis: {str(e)}")
            in_memory_prompts.pop(name, None)
            print(f"Deleted prompt '{name}' from memory")
    else:
        in_memory_prompts.pop(name, None)
        print(f"Deleted prompt '{name}' from memory")

print(f"Java executable: {sys.executable}")
print(f"Java path: {sys.path}")

app = Flask(__name__, 
    template_folder='templates',
    static_folder='static/dist',
    static_url_path=''
)

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')  # Change in production
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = False  # Set to True in production
app.config['JWT_COOKIE_CSRF_PROTECT'] = True
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

jwt = JWTManager(app)

# Admin credentials (move to environment variables in production)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password"

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            # Verify JWT token
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except:
            # Redirect to login if no valid token
            return redirect(url_for('admin_login'))
    return wrapper

# Configure Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

def get_system_prompt():
    """Get current system prompt from Redis or memory"""
    global in_memory_current_prompt
    if redis_client:
        try:
            prompt = redis_client.get('current_prompt')
            if prompt:
                print(f"Got current prompt from Redis")
                return prompt
            print(f"No current prompt in Redis, using default")
            return DEFAULT_SYSTEM_PROMPT
        except Exception as e:
            print(f"Error getting prompt from Redis: {str(e)}")
            print(f"Using in-memory prompt: {in_memory_current_prompt}")
            return in_memory_current_prompt or DEFAULT_SYSTEM_PROMPT
    print(f"Using in-memory prompt: {in_memory_current_prompt}")
    return in_memory_current_prompt or DEFAULT_SYSTEM_PROMPT

def get_current_subject():
    """Get current subject from Redis or memory"""
    global in_memory_current_subject
    if redis_client:
        try:
            subject = redis_client.get('current_subject')
            if subject:
                print(f"Got current subject from Redis: {subject}")
                return subject
            print(f"No current subject in Redis, using default")
            return 'Java'
        except Exception as e:
            print(f"Error getting subject from Redis: {str(e)}")
            print(f"Using in-memory subject: {in_memory_current_subject}")
            return in_memory_current_subject
    print(f"Using in-memory subject: {in_memory_current_subject}")
    return in_memory_current_subject

# In-memory storage for chat sessions only
chat_sessions = {}

def get_or_create_chat(session_id):
    """Get existing chat or create new one with system prompt"""
    if session_id not in chat_sessions:
        model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-1219")
        current_prompt = get_system_prompt()
        chat = model.start_chat(history=[
            {"role": "user", "parts": [current_prompt]},
            {"role": "model", "parts": ["Understood. I will act as a teacher following the specified guidelines to help students learn effectively."]}
        ])
        chat_sessions[session_id] = chat
    return chat_sessions[session_id]

# Routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return render_template('chat.html')

def generate_response(chat, message):
    """Generate streaming response from chat"""
    try:
        response = chat.send_message(message, stream=True)
        accumulated_response = []
        
        for chunk in response:
            if chunk.text:
                accumulated_response.append(chunk.text)
                # Yield each chunk for streaming
                yield f"data: {chunk.text}\n\n"
        
        # Store the complete response for history
        return "".join(accumulated_response)
    except Exception as e:
        print(f"Error generating response: {str(e)}")
        yield f"data: Error: {str(e)}\n\n"
        return str(e)

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.get_json()
        user_input = data.get('message')
        session_id = data.get('sessionId')

        if not session_id:
            return jsonify({'error': 'No sessionId provided'}), 400

        if not user_input:
            return jsonify({'error': 'No message provided'}), 400

        # Get or create chat instance for this session
        chat = get_or_create_chat(session_id)

        def generate():
            response_text = yield from generate_response(chat, user_input)
            
            # After generating response, you can access chat history
            print(f"Chat history for session {session_id}:")
            for message in chat.history:
                print(f"{message['role']}: {message['parts']}")

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream'
        )

    except Exception as e:
        print(f"Server error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            access_token = create_access_token(identity=username)
            response = redirect(url_for('admin_prompt'))
            set_access_cookies(response, access_token)
            return response
        
        return render_template('admin_login.html', error='Invalid credentials')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    response = redirect(url_for('admin_login'))
    unset_jwt_cookies(response)
    return response

@app.route('/admin/prompt', methods=['GET'])
@admin_required
def admin_prompt():
    saved_prompts = load_saved_prompts()
    current_prompt = get_system_prompt()
    print(f"Current prompt in admin_prompt: {current_prompt}")
    return render_template('admin_prompt.html',
                         default_prompt=DEFAULT_SYSTEM_PROMPT,
                         current_prompt=current_prompt,
                         current_subject=get_current_subject(),
                         saved_prompts=saved_prompts)

@app.route('/admin/prompt', methods=['POST'])
@admin_required
def update_prompt():
    try:
        global in_memory_current_prompt, in_memory_current_subject
        
        prompt_name = request.form.get('prompt_name')
        new_prompt = request.form.get('prompt')
        new_subject = request.form.get('subject')
        set_as_default = request.form.get('set_as_default') == 'true'
        
        print(f"Received update request:")
        print(f"prompt_name: {prompt_name}")
        print(f"new_prompt: {new_prompt}")
        print(f"new_subject: {new_subject}")
        print(f"set_as_default: {set_as_default}")
        
        if not new_prompt:
            return jsonify({'error': 'Prompt cannot be empty'}), 400
            
        # Update current subject
        if new_subject:
            print(f"New subject: {new_subject}")
            if redis_client:
                try:
                    redis_client.set('current_subject', new_subject)
                    print(f"Updated subject in Redis to: {new_subject}")
                except Exception as e:
                    print(f"Error updating subject in Redis: {str(e)}")
                    in_memory_current_subject = new_subject
                    print(f"Updated subject in memory to: {new_subject}")
            else:
                in_memory_current_subject = new_subject
                print(f"Updated subject in memory to: {new_subject}")
        
        # Save prompt if name provided
        if prompt_name:
            save_prompt(prompt_name, new_prompt)
        
        # Set as current system prompt if requested
        if set_as_default:
            if redis_client:
                try:
                    redis_client.set('current_prompt', new_prompt)
                    print(f"Updated current prompt in Redis")
                except Exception as e:
                    print(f"Error updating current prompt in Redis: {str(e)}")
                    in_memory_current_prompt = new_prompt
                    print(f"Updated current prompt in memory")
            else:
                in_memory_current_prompt = new_prompt
                print(f"Updated current prompt in memory")
            
        return jsonify({'message': 'Settings updated successfully'}), 200
    except Exception as e:
        print(f"Error in update_prompt: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/prompts', methods=['DELETE'])
@admin_required
def delete_prompt():
    prompt_name = request.args.get('name')
    if not prompt_name:
        return jsonify({'error': 'No prompt name provided'}), 400
        
    saved_prompts = load_saved_prompts()
    if prompt_name not in saved_prompts:
        return jsonify({'error': 'Prompt not found'}), 404
        
    delete_prompt(prompt_name)
    
    return jsonify({'message': f'Prompt "{prompt_name}" deleted successfully'}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
