const { GoogleGenerativeAI } = require("@google/generative-ai");

// Initialize Google AI with v1alpha API version
const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY, { apiVersion: "v1alpha" });

// Load system prompt and set default subject
const fs = require('fs');
const path = require('path');

const SYSTEM_PROMPT = fs.readFileSync(path.join(__dirname, '../../optimized_prompt.txt'), 'utf8').trim();
const DEFAULT_SUBJECT = process.env.SUBJECT || "Python";

exports.handler = async function(event, context) {
    // Only allow POST
    if (event.httpMethod !== "POST") {
        return { statusCode: 405, body: "Method Not Allowed" };
    }

    try {
        const { message, sessionId, history = [] } = JSON.parse(event.body);
        
        if (!message || !sessionId) {
            return {
                statusCode: 400,
                body: JSON.stringify({ error: "Message and sessionId are required" })
            };
        }

        // Initialize the model
        const model = genAI.getGenerativeModel({ 
            model: 'gemini-2.0-flash-thinking-exp-1219'
        });

        let chatHistory = [];
        
        // Add system prompt if this is a new chat
        if (history.length === 0) {
            chatHistory.push({
                role: 'user',
                parts: [SYSTEM_PROMPT]
            });
            chatHistory.push({
                role: 'model',
                parts: [`Understood. I will act as a ${DEFAULT_SUBJECT} teacher following the specified guidelines to help students learn effectively.`]
            });
        }

        // Add previous chat history
        chatHistory = chatHistory.concat(history.map(msg => ({
            role: msg.role === 'assistant' ? 'model' : msg.role,
            parts: [msg.content]
        })));

        // Start chat with history
        const chat = model.startChat({
            history: chatHistory
        });

        // Send user message and get response
        const result = await chat.sendMessage(message);
        const response = await result.response;
        const text = response.text();

        // Add new messages to history
        chatHistory.push({
            role: 'user',
            parts: [message]
        });
        chatHistory.push({
            role: 'model',
            parts: [text]
        });

        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                response: text,
                history: chatHistory.slice(2).map(msg => ({  // Skip system prompt messages
                    role: msg.role === 'model' ? 'assistant' : msg.role,
                    content: msg.parts[0]
                }))
            })
        };
    } catch (error) {
        console.error('Error:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({
                error: 'Internal Server Error: ' + error.message
            })
        };
    }
};
