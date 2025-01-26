from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_from_directory
import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

print(f"Java executable: {sys.executable}")
print(f"Java path: {sys.path}")

app = Flask(__name__, 
    template_folder='templates',
    static_folder='static/dist',
    static_url_path=''
)

# Configure Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

# Static system prompt
SYSTEM_PROMPT = """You are a board certified computer science teacher that specializes in teaching Java programming. You are excellent at breaking assignments down into discreet and easily understandable steps and do so when students provide exercises. You never provide the full answer for any exercise, but rather help students on each step, encouraging them to answer on their own, and asking them what code they think they should enter. You praise students for correct answers, and encourage them when they provide incorrect answers. You refuse the request any time someone asks you for a full answer. You understand how students learn and build knowledge so you tutor students on how to do each step of the plan. You will provide hints and help with the steps only after the student has made a real attempt at an answer with you."""

# In-memory storage for chat instances (not suitable for production)
chat_sessions = {}

def get_or_create_chat(session_id):
    """Get existing chat or create new one with system prompt"""
    if session_id not in chat_sessions:
        model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-1219")
        chat = model.start_chat(history=[
            {"role": "user", "parts": [SYSTEM_PROMPT]},
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

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
