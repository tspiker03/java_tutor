import React, { useState, useRef, useEffect } from 'react';

const ChatComponent = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);
    const sessionId = useRef(Math.random().toString(36).substring(2));

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const formatResponse = (text) => {
        // Replace markdown-style code blocks with HTML
        text = text.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        
        // Replace inline code with HTML
        text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // Replace asterisks with HTML
        text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        
        return text;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMessage = input.trim();
        setInput('');
        setIsLoading(true);

        console.log('Sending message:', userMessage);
        console.log('Session ID:', sessionId.current);

        try {
            // Add user message to chat
            setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    message: userMessage,
                    sessionId: sessionId.current
                })
            });

            console.log('Response status:', response.status);
            const contentType = response.headers.get('Content-Type');
            console.log('Response content type:', contentType);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Error response:', errorText);
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Received response:', data);
            
            if (data.error) {
                throw new Error(data.error);
            }

            // Add assistant's response to chat
            setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);

        } catch (error) {
            console.error('Error details:', error);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `Sorry, there was an error processing your message: ${error.message}`
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="chat-interface">
            <div className="chat-messages">
                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`message ${msg.role === 'user' ? 'user-message' : 'bot-message'}`}
                    >
                        {msg.role === 'user' ? (
                            msg.content
                        ) : (
                            <div dangerouslySetInnerHTML={{ __html: formatResponse(msg.content) }} />
                        )}
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>
            <form onSubmit={handleSubmit} className="input-container">
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSubmit(e);
                        }
                    }}
                    placeholder="Ask your Java programming question here..."
                    disabled={isLoading}
                />
                <button type="submit" disabled={isLoading}>
                    {isLoading ? 'Sending...' : 'Send'}
                </button>
            </form>
        </div>
    );
};

export default ChatComponent;
