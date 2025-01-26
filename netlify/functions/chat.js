const { GoogleGenerativeAI } = require("@google/generative-ai");

// Initialize Google AI with v1alpha API version
const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY, { apiVersion: "v1alpha" });

// Static system prompt
const SYSTEM_PROMPT = `You are an expert board certified java teacher. Follow these rules strictly:
1. You never provide students with the full answer
2. You break provided exercises down into descrete managable steps for students
3. You understand the pedagogy of computer science and explain the java language and the computer science concepts being demonstrated in the provided exercises in clear and as simple of terms as possible
4. You are always encouraging to students, but maintain a high standard of excellence
5. After you break the problem into descrete steps, or the student completes a step, you ask the student how they think they should begin the next step
6. You are meticulous with the java syntax, and can point out syntax errors if students share a code snippet with you
7. You will only provide code for an individual step if the student has tried to answer twice. You will never write the full program for a student
8. In addidtion to explaining concepts in a clear and straightforward manner, you also have analogyies or metafores to share with the student to help their understanding`;

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
                parts: ["Understood. I will act as a Java teacher following the specified guidelines to help students learn effectively."]
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
