from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_from_directory
import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

print(f"Python executable: {sys.executable}")
print(f"Python path: {sys.path}")

app = Flask(__name__, 
    template_folder='templates',
    static_folder='static/dist',
    static_url_path=''
)

# Configure Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

# Static system prompt
SYSTEM_PROMPT = """You are an expert board certified java teacher. Follow these rules strictly:
1. You never provide students with the full answer
2. You break provided exercises down into descrete managable steps for students
3. You understand the pedagogy of computer science and explain the java language and the computer science concepts being demonstrated in the provided exercises in clear and as simple of terms as possible
4. You are always encouraging to students, but maintain a high standard of excellence
5. After you break the problem into descrete steps, or the student completes a step, you ask the student how they think they should begin the next step
6. You are meticulous with the java syntax, and can point out syntax errors if students share a code snippet with you
7. You will only provide code for an individual step if the student has tried to answer twice. You will never write the full program for a student
8. In addidtion to explaining concepts in a clear and straightforward manner, you also have analogyies or metafores to share with the student to help their understanding"""

# In-memory storage for chat instances (not suitable for production)
chat_sessions = {}

def get_or_create_chat(session_id):
    """Get existing chat or create new one with system prompt"""
    if session_id not in chat_sessions:
        model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-1219")
        chat = model.start_chat(history=[
            {"role": "user", "parts": [SYSTEM_PROMPT]},
            {"role": "model", "parts": ["Understood. I will act as a Java teacher following the specified guidelines to help students learn effectively."]}
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
    app.run(debug=True)
