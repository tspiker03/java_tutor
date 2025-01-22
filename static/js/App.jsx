import React from 'react';
import { createRoot } from 'react-dom/client';
import ChatComponent from './ChatComponent';

import './styles.css';

const App = () => {
    return (
        <div className="app-container">
            <div className="instructions">
                <h2>How to Use</h2>
                <ol>
                    <li>Ask any question or describe what you need help with.</li>
                    <li>The AI will show its thinking process before providing the answer.</li>
                    <li>You can see how the AI reasons through your questions step by step.</li>
                    <li>Feel free to ask follow-up questions or request clarification.</li>
                    <li>The AI will maintain context of your conversation.</li>
                </ol>
            </div>
            <ChatComponent />
        </div>
    );
};

const container = document.getElementById('root');
const root = createRoot(container);
root.render(<App />);
