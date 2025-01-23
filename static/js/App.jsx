import React from 'react';
import { createRoot } from 'react-dom/client';
import ChatComponent from './ChatComponent';

import './styles.css';

const App = () => {
    return (
        <div className="app-container">
            <div className="instructions">
                <h2>Java Programming Tutor</h2>
                <ol>
                    <li>Ask any Java programming question or describe the Java concept you need help with.</li>
                    <li>The tutor will guide you through Java concepts step by step.</li>
                    <li>Practice writing Java code with guided assistance.</li>
                    <li>Get feedback on your Java code and solutions.</li>
                    <li>Learn Java programming through interactive problem-solving.</li>
                </ol>
            </div>
            <ChatComponent />
        </div>
    );
};

const container = document.getElementById('root');
const root = createRoot(container);
root.render(<App />);
