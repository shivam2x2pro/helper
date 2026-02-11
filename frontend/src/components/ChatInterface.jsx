import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Bot, Terminal, Copy, Check, ChevronRight, ExternalLink, Star, MapPin, CreditCard, Home, Briefcase, Plus, List, AlertTriangle, Info, Zap, Package, CheckCircle, XCircle, Clock, Loader } from 'lucide-react';

// Inline Product Choices Component (appears in logs)
const InlineProductChoices = ({ message, products, sessionId, onSelect }) => {
    const [selectedIndex, setSelectedIndex] = useState(null);
    const [copiedIndex, setCopiedIndex] = useState(null);

    const handleSelect = (index, product) => {
        setSelectedIndex(index);
        onSelect(sessionId, index, product);
    };

    const handleCopyLink = async (index, url) => {
        if (url) {
            await navigator.clipboard.writeText(url);
            setCopiedIndex(index);
            setTimeout(() => setCopiedIndex(null), 2000);
        }
    };

    return (
        <div className="inline-product-choices">
            <div className="choices-header">
                <ChevronRight size={16} className="prompt-icon" />
                <span>{message}</span>
            </div>
            <div className="choices-grid">
                {products.map((product, index) => (
                    <div
                        key={index}
                        className={`choice-card ${selectedIndex === index ? 'selected' : ''}`}
                    >
                        <div className="choice-info">
                            <h4 className="choice-name">{product.product_name}</h4>
                            <div className="choice-meta">
                                <span className="choice-price">{product.price}</span>
                                <span className="choice-rating">
                                    <Star size={12} fill="currentColor" />
                                    {product.rating}
                                </span>
                            </div>
                        </div>
                        <div className="choice-actions">
                            {product.product_url && (
                                <>
                                    <button
                                        onClick={() => handleCopyLink(index, product.product_url)}
                                        className="copy-link-btn"
                                        title="Copy product link"
                                    >
                                        {copiedIndex === index ? <Check size={14} /> : <Copy size={14} />}
                                    </button>
                                    <a
                                        href={product.product_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="choice-link"
                                        title="View product"
                                    >
                                        <ExternalLink size={14} />
                                    </a>
                                </>
                            )}
                            <button
                                onClick={() => handleSelect(index, product)}
                                disabled={selectedIndex !== null}
                                className="choice-select-btn"
                            >
                                {selectedIndex === index ? 'Selected' : 'Select'}
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

// Inline Address Choices Component (appears in logs during checkout)
const InlineAddressChoices = ({ message, addresses, sessionId, onSelect }) => {
    const [selectedIndex, setSelectedIndex] = useState(null);

    const handleSelect = (index, address) => {
        setSelectedIndex(index);
        onSelect(sessionId, index, address);
    };

    const getAddressIcon = (type) => {
        const t = (type || '').toLowerCase();
        if (t.includes('new')) return <Plus size={14} />;
        if (t.includes('work') || t.includes('office')) return <Briefcase size={14} />;
        return <Home size={14} />;
    };

    const isNewAddressOption = (address) => {
        return address.address_type === 'NEW' || address.name?.includes('Add New Address');
    };

    return (
        <div className="inline-address-choices">
            <div className="choices-header">
                <MapPin size={16} className="prompt-icon" />
                <span>{message}</span>
            </div>
            <div className="choices-grid">
                {addresses.map((address, index) => (
                    <div
                        key={index}
                        className={`choice-card address-card ${selectedIndex === index ? 'selected' : ''} ${isNewAddressOption(address) ? 'new-address-option' : ''}`}
                    >
                        <div className="choice-info">
                            <div className="address-header">
                                <h4 className="choice-name">{address.name}</h4>
                                {address.address_type && !isNewAddressOption(address) && (
                                    <span className="address-type-badge">
                                        {getAddressIcon(address.address_type)}
                                        {address.address_type}
                                    </span>
                                )}
                            </div>
                            {address.phone && !isNewAddressOption(address) && (
                                <span className="address-phone">{address.phone}</span>
                            )}
                            <p className="address-text">{address.address}</p>
                        </div>
                        <div className="choice-actions">
                            <button
                                onClick={() => handleSelect(index, address)}
                                disabled={selectedIndex !== null}
                                className={`choice-select-btn ${isNewAddressOption(address) ? 'new-address-btn' : ''}`}
                            >
                                {selectedIndex === index ? 'Selected' : (isNewAddressOption(address) ? 'Add New' : 'Deliver Here')}
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

// Inline Payment Choices Component (appears in logs during checkout)
const InlinePaymentChoices = ({ message, payments, sessionId, onSelect }) => {
    const [selectedIndex, setSelectedIndex] = useState(null);

    const handleSelect = (index, payment) => {
        setSelectedIndex(index);
        onSelect(sessionId, index, payment);
    };

    return (
        <div className="inline-payment-choices">
            <div className="choices-header">
                <CreditCard size={16} className="prompt-icon" />
                <span>{message}</span>
            </div>
            <div className="choices-grid payment-grid">
                {payments.map((payment, index) => (
                    <div
                        key={index}
                        className={`choice-card payment-card ${selectedIndex === index ? 'selected' : ''}`}
                    >
                        <div className="choice-info">
                            <h4 className="choice-name">{payment.method}</h4>
                            {payment.description && (
                                <p className="payment-description">{payment.description}</p>
                            )}
                        </div>
                        <div className="choice-actions">
                            <button
                                onClick={() => handleSelect(index, payment)}
                                disabled={selectedIndex !== null}
                                className="choice-select-btn"
                            >
                                {selectedIndex === index ? 'Selected' : 'Select'}
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

// General Inline Options Component (for any MCQ-style selection)
const InlineOptions = ({ message, options, optionType, sessionId, onSelect }) => {
    const [selectedIndex, setSelectedIndex] = useState(null);

    const handleSelect = (index, option) => {
        setSelectedIndex(index);
        onSelect(sessionId, index, option);
    };

    const getIcon = () => {
        switch (optionType) {
            case 'warning': return <AlertTriangle size={16} className="prompt-icon warning" />;
            case 'info': return <Info size={16} className="prompt-icon info" />;
            case 'action': return <Zap size={16} className="prompt-icon action" />;
            default: return <List size={16} className="prompt-icon" />;
        }
    };

    return (
        <div className={`inline-options inline-options-${optionType}`}>
            <div className="choices-header">
                {getIcon()}
                <span>{message}</span>
            </div>
            <div className="choices-grid options-grid">
                {options.map((option, index) => (
                    <div
                        key={index}
                        className={`choice-card option-card ${selectedIndex === index ? 'selected' : ''}`}
                    >
                        <div className="choice-info">
                            <h4 className="choice-name">{option.label}</h4>
                            {option.description && (
                                <p className="option-description">{option.description}</p>
                            )}
                        </div>
                        <div className="choice-actions">
                            <button
                                onClick={() => handleSelect(index, option)}
                                disabled={selectedIndex !== null}
                                className="choice-select-btn"
                            >
                                {selectedIndex === index ? 'Selected' : 'Select'}
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

const ProductCard = ({ data }) => {
    const [copied, setCopied] = useState(false);

    const handleCopyLink = async () => {
        if (data.product_url) {
            await navigator.clipboard.writeText(data.product_url);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    if (data.product_name) {
        return (
            <div className="product-card">
                <h3>{data.product_name}</h3>
                <div className="product-details">
                    <span className="price">{data.price}</span>
                    <span className="rating">★ {data.rating}</span>
                </div>
                {data.product_url && (
                    <div className="product-actions">
                        <a href={data.product_url} target="_blank" rel="noopener noreferrer" className="view-product-btn">
                            View Product
                        </a>
                        <button onClick={handleCopyLink} className="copy-link-btn">
                            {copied ? <Check size={16} /> : <Copy size={16} />}
                            {copied ? 'Copied!' : 'Copy Link'}
                        </button>
                    </div>
                )}
            </div>
        );
    }
    return <pre className="json-dump">{JSON.stringify(data, null, 2)}</pre>;
};

const InlineInput = ({ question, sessionId, onSubmit }) => {
    const [input, setInput] = useState('');
    const inputRef = useRef(null);

    useEffect(() => {
        inputRef.current?.focus();
    }, []);

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
        <div className="inline-input-container">
            <div className="inline-input-question">
                <ChevronRight size={16} className="prompt-icon" />
                <span>{question}</span>
            </div>
            <div className="inline-input-row">
                <span className="input-prompt">›</span>
                <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type your response and press Enter..."
                    className="inline-terminal-input"
                />
                <button onClick={handleSubmit} disabled={!input.trim()} className="inline-submit-btn">
                    Submit
                </button>
            </div>
        </div>
    );
};

// Batch Status Panel Component
const BatchStatusPanel = ({ batchStatus }) => {
    if (!batchStatus || batchStatus.length === 0) return null;

    const getStatusIcon = (status) => {
        switch (status) {
            case 'success': return <CheckCircle size={16} className="status-icon success" />;
            case 'failed': return <XCircle size={16} className="status-icon failed" />;
            case 'in_progress': return <Loader size={16} className="status-icon in-progress spinning" />;
            default: return <Clock size={16} className="status-icon pending" />;
        }
    };

    const successCount = batchStatus.filter(item => item.status === 'success').length;
    const failedCount = batchStatus.filter(item => item.status === 'failed').length;
    const pendingCount = batchStatus.filter(item => item.status === 'pending').length;
    const inProgressCount = batchStatus.filter(item => item.status === 'in_progress').length;

    return (
        <div className="batch-status-panel">
            <div className="batch-status-header">
                <Package size={18} />
                <span>Batch Order Progress</span>
                <div className="batch-summary">
                    <span className="summary-item success">{successCount} done</span>
                    <span className="summary-item failed">{failedCount} failed</span>
                    <span className="summary-item pending">{pendingCount + inProgressCount} remaining</span>
                </div>
            </div>
            <div className="batch-items-status">
                {batchStatus.map((item, idx) => (
                    <div key={idx} className={`batch-item-row ${item.status}`}>
                        <div className="batch-item-index">#{item.index + 1}</div>
                        {getStatusIcon(item.status)}
                        <div className="batch-item-url" title={item.product_url}>
                            {item.product_url.length > 50
                                ? item.product_url.substring(0, 50) + '...'
                                : item.product_url}
                        </div>
                        <div className="batch-item-meta">
                            <span>Qty: {item.quantity}</span>
                            {item.color && <span>{item.color}</span>}
                        </div>
                        <div className="batch-item-status-text">
                            {item.status === 'success' && item.message && (
                                <span className="success-msg" title={item.message}>Completed</span>
                            )}
                            {item.status === 'failed' && item.error && (
                                <span className="error-msg" title={item.error}>Failed</span>
                            )}
                            {item.status === 'in_progress' && (
                                <span className="progress-msg">Processing...</span>
                            )}
                            {item.status === 'pending' && (
                                <span className="pending-msg">Waiting</span>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

const ChatInterface = ({
    logs,
    hitlData,
    onHitlSubmit,
    productChoices,
    onProductSelect,
    addressChoices,
    onAddressSelect,
    paymentChoices,
    onPaymentSelect,
    generalOptions,
    onOptionSelect,
    batchStatus
}) => {
    const endRef = useRef(null);

    const hasActiveChoice = hitlData?.isOpen || productChoices?.isOpen || addressChoices?.isOpen || paymentChoices?.isOpen || generalOptions?.isOpen;

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs, hitlData?.isOpen, productChoices?.isOpen, addressChoices?.isOpen, paymentChoices?.isOpen, generalOptions?.isOpen]);

    const hasBatchStatus = batchStatus && batchStatus.length > 0;

    return (
        <div className="chat-interface">
            {/* Batch Status Panel */}
            {hasBatchStatus && <BatchStatusPanel batchStatus={batchStatus} />}

            <div className={`logs-container ${logs.length === 0 && !hasActiveChoice && !hasBatchStatus ? 'empty' : 'filled'}`}>
                {logs.length === 0 && !hasActiveChoice && !hasBatchStatus && (
                    <div className="empty-state">
                        <div className="icon-circle">
                            <Bot size={48} />
                        </div>
                        <h3>Agent Ready</h3>
                        <p>Select a platform and start a task to see real-time logs here.</p>
                    </div>
                )}
                {logs.map((log, index) => (
                    <div key={index} className={`log-entry ${log.type}`}>
                        <span className="timestamp">[{log.timestamp ? log.timestamp.toLocaleTimeString() : new Date().toLocaleTimeString()}]</span>
                        <div className="content">
                            {log.type === 'image' ? (
                                <img src={log.content} alt="Screenshot" />
                            ) : log.type === 'result-json' ? (
                                <ProductCard data={log.content} />
                            ) : (
                                <ReactMarkdown>{log.content}</ReactMarkdown>
                            )}
                        </div>
                    </div>
                ))}

                {/* Inline Product Choices */}
                {productChoices?.isOpen && (
                    <InlineProductChoices
                        message={productChoices.message}
                        products={productChoices.products}
                        sessionId={productChoices.sessionId}
                        onSelect={onProductSelect}
                    />
                )}

                {/* Inline Address Choices */}
                {addressChoices?.isOpen && (
                    <InlineAddressChoices
                        message={addressChoices.message}
                        addresses={addressChoices.addresses}
                        sessionId={addressChoices.sessionId}
                        onSelect={onAddressSelect}
                    />
                )}

                {/* Inline Payment Choices */}
                {paymentChoices?.isOpen && (
                    <InlinePaymentChoices
                        message={paymentChoices.message}
                        payments={paymentChoices.payments}
                        sessionId={paymentChoices.sessionId}
                        onSelect={onPaymentSelect}
                    />
                )}

                {/* General Inline Options */}
                {generalOptions?.isOpen && (
                    <InlineOptions
                        message={generalOptions.message}
                        options={generalOptions.options}
                        optionType={generalOptions.optionType}
                        sessionId={generalOptions.sessionId}
                        onSelect={onOptionSelect}
                    />
                )}

                {/* Inline HITL Input */}
                {hitlData?.isOpen && (
                    <InlineInput
                        question={hitlData.question}
                        sessionId={hitlData.sessionId}
                        onSubmit={onHitlSubmit}
                    />
                )}

                <div ref={endRef} />
            </div>
        </div>
    );
};

export default ChatInterface;
