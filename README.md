# Java Tutor Chat Application

An interactive chat application powered by Google's Gemini AI model, designed to help students learn Java programming through guided, step-by-step assistance.

## Features

- **Interactive Chat Interface**: Clean and intuitive chat interface for real-time communication with the AI tutor
- **Contextual Learning**: The AI maintains conversation context to provide consistent and relevant assistance
- **Step-by-Step Guidance**: Instead of providing complete solutions, the tutor breaks down problems into manageable steps
- **Encouraging Environment**: Positive reinforcement for correct answers and supportive guidance for improvements
- **Real-time Responses**: Powered by Google's Gemini model for quick and accurate responses

## Technology Stack

- **Backend**: Python Flask server
- **Frontend**: React with modern JavaScript
- **AI Model**: Google's Gemini 2.0 Flash Thinking model
- **Build Tool**: Webpack for frontend asset bundling

## Prerequisites

- Python 3.12 or higher
- Node.js and npm
- Google API key for Gemini AI

## Setup

1. Clone the repository:
```bash
git clone https://github.com/tspiker03/java_tutor.git
cd java_tutor
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install Node.js dependencies:
```bash
npm install
```

4. Create a `.env` file based on `.env.template` and add your configuration:
```
# Google API Configuration
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL=gemini-2.0-flash-thinking-exp

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key
```

5. Build the frontend assets:
```bash
npm run build
```

6. Start the development server:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Usage

1. Open the application in your web browser
2. Type your Java-related questions in the chat input
3. The AI tutor will:
   - Help break down complex problems into steps
   - Guide you through solutions without giving direct answers
   - Provide hints and encouragement
   - Maintain context of your conversation

## Development

- The Flask server runs in debug mode by default
- Frontend changes require rebuilding assets with `npm run build`
- The application uses an in-memory session store (not suitable for production)

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
