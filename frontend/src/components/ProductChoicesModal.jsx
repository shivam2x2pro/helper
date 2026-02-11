import { useState } from 'react';
import { Check, ExternalLink, Copy } from 'lucide-react';

const ProductChoicesModal = ({ isOpen, message, products, sessionId, onSelect }) => {
    const [copiedIndex, setCopiedIndex] = useState(null);

    if (!isOpen) return null;

    const handleCopyLink = async (url, index) => {
        await navigator.clipboard.writeText(url);
        setCopiedIndex(index);
        setTimeout(() => setCopiedIndex(null), 2000);
    };

    return (
        <div className="modal-overlay">
            <div className="product-choices-modal">
                <h3>Choose a Product</h3>
                <p className="modal-message">{message}</p>

                <div className="product-choices-list">
                    {products.map((product, index) => (
                        <div key={index} className="product-choice-item">
                            <div className="product-choice-info">
                                <h4>{product.product_name}</h4>
                                <div className="product-choice-details">
                                    <span className="price">{product.price}</span>
                                    <span className="rating">★ {product.rating}</span>
                                </div>
                            </div>
                            <div className="product-choice-actions">
                                <button
                                    className="copy-btn"
                                    onClick={() => handleCopyLink(product.product_url, index)}
                                    title="Copy link"
                                >
                                    {copiedIndex === index ? <Check size={16} /> : <Copy size={16} />}
                                </button>
                                <a
                                    href={product.product_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="view-btn"
                                    title="View product"
                                >
                                    <ExternalLink size={16} />
                                </a>
                                <button
                                    className="select-btn"
                                    onClick={() => onSelect(sessionId, index, product)}
                                >
                                    Select
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default ProductChoicesModal;
