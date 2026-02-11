import { useState } from 'react';
import { MessageCircleQuestion } from 'lucide-react';

const HitlModal = ({ isOpen, question, onSubmit, sessionId }) => {
    const [input, setInput] = useState('');

    if (!isOpen) return null;

    const handleSubmit = () => {
        if (!input.trim()) return;
        onSubmit(sessionId, input);
        setInput('');
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            handleSubmit();
        }
    };

    return (
        <div className="modal-overlay">
            <div className="modal-content hitl-modal">
                <div className="hitl-header">
                    <div className="hitl-icon">
                        <MessageCircleQuestion size={24} />
                    </div>
                    <h3>Input Required</h3>
                </div>

                <p className="hitl-question">{question}</p>

                <div className="hitl-input-group">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Type your response..."
                        autoFocus
                    />
                    <button onClick={handleSubmit} disabled={!input.trim()}>
                        Submit
                    </button>
                </div>
            </div>
        </div>
    );
};

export default HitlModal;
