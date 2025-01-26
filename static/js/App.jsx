import React from 'react';
import { createRoot } from 'react-dom/client';
import ChatComponent from './ChatComponent';

import './styles.css';

const App = () => {
    return (
        <div className="app-container">
            <div className="instructions">
                <div className="title">How to use the Python Programming Tutor:</div>

                1. Clearly explain in a conversational manner what you want.
                Example: Can you help me with the exercise: [insert full exercise]? Here is what I have so far: [insert code].

                2. Follow along with the steps the chatbot gives you and answer the questions the chatbot asks.

                3. If you do not understand the reason behind an answer or result, ask the chatbot to explain it further.

                4. If you get an error in your code, feel free to paste your code into the chatbot and ask it to help you find the error, then paste the error message you are receiving.
                Example: In this code [insert code here], I get this error: [insert error message], can you help me identify and fix the error?

                5. Do not cut and paste code from the chatbot into your IDE. Take the time to type the code. It really does help you learn.

                6. Chatbots, like your teachers, and like you, can sometimes be wrong. If you do end up with a wrong answer, be patient, reset the chatbot session, and try again.
            </div>
            <ChatComponent />
        </div>
    );
};

const container = document.getElementById('root');
const root = createRoot(container);
root.render(<App />);
