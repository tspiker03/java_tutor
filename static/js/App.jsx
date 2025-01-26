import React, { useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import ChatComponent from './ChatComponent';

import './styles.css';

const App = () => {
    const [subject, setSubject] = useState('Python');

    useEffect(() => {
        const fetchSubject = async () => {
            try {
                const response = await fetch('/api/subject');
                if (response.ok) {
                    const data = await response.json();
                    if (data.subject !== subject) {
                        setSubject(data.subject);
                        // Clear any existing chat state if subject changes
                        localStorage.removeItem('chatHistory');
                    }
                }
            } catch (error) {
                console.error('Error fetching subject:', error);
            }
        };

        // Initial fetch
        fetchSubject();

        // Poll for subject changes every 5 seconds
        const interval = setInterval(fetchSubject, 5000);

        return () => clearInterval(interval);
    }, [subject]);

    return (
        <div className="app-container">
            <div className="instructions">
                <h2>How to use the {subject} Programming Tutor:</h2>
                <ol>
                    <li>Clearly explain in a conversational manner what you want.
                        <div className="example">Example: Can you help me with the exercise: [insert full exercise]? Here is what I have so far: [insert code].</div>
                    </li>
                    <li>Follow along with the steps the chatbot gives you and answer the questions the chatbot asks.</li>
                    <li>If you do not understand the reason behind an answer or result, ask the chatbot to explain it further.</li>
                    <li>If you get an error in your code, feel free to paste your code into the chatbot and ask it to help you find the error, then paste the error message you are receiving.
                        <div className="example">Example: In this code [insert code here], I get this error: [insert error message], can you help me identify and fix the error?</div>
                    </li>
                    <li>Do not cut and paste code from the chatbot into your IDE. Take the time to type the code. It really does help you learn.</li>
                    <li>Chatbots, like your teachers, and like you, can sometimes be wrong. If you do end up with a wrong answer, be patient, reset the chatbot session, and try again.</li>
                </ol>
            </div>
            <ChatComponent />
        </div>
    );
};

const container = document.getElementById('root');
const root = createRoot(container);
root.render(<App />);
