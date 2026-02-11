import React, { useRef } from 'react';
import { Search, ShoppingCart, Upload, FileSpreadsheet, X } from 'lucide-react';

const ControlPanel = ({
    platform,
    setPlatform,
    action,
    setAction,
    onRun,
    userMessage,
    setUserMessage,
    productUrl,
    setProductUrl,
    quantity,
    setQuantity,
    isRunning,
    // Batch order props
    isBatchMode,
    setIsBatchMode,
    csvData,
    setCsvData,
    onRunBatch
}) => {
    const fileInputRef = useRef(null);

    const handleFileUpload = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            const text = event.target.result;
            const lines = text.split('\n').filter(line => line.trim());

            if (lines.length < 2) {
                alert('CSV file must have a header row and at least one data row');
                return;
            }

            // Parse header
            const header = lines[0].split(',').map(h => h.trim().toLowerCase());
            const urlIndex = header.findIndex(h => h.includes('url') || h === 'product_url');
            const qtyIndex = header.findIndex(h => h.includes('qty') || h.includes('quantity'));
            const colorIndex = header.findIndex(h => h.includes('color') || h.includes('variant'));

            if (urlIndex === -1) {
                alert('CSV must have a column containing "url" or "product_url"');
                return;
            }

            // Parse data rows
            const items = [];
            for (let i = 1; i < lines.length; i++) {
                const values = lines[i].split(',').map(v => v.trim());
                if (values[urlIndex]) {
                    items.push({
                        product_url: values[urlIndex],
                        quantity: qtyIndex !== -1 && values[qtyIndex] ? parseInt(values[qtyIndex]) || 1 : 1,
                        color: colorIndex !== -1 ? values[colorIndex] || null : null
                    });
                }
            }

            setCsvData(items);
        };
        reader.readAsText(file);
    };

    const removeItem = (index) => {
        setCsvData(prev => prev.filter((_, i) => i !== index));
    };

    const clearCsv = () => {
        setCsvData([]);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };
    return (
        <div className="control-panel">
            <div className="panel-header">
                <h2>Control Panel</h2>
                <div className="status-indicator">
                    <span className={`status-dot ${isRunning ? 'running' : 'idle'}`}></span>
                    {isRunning ? 'Agent Active' : 'Ready'}
                </div>
            </div>

            <div className="section platform-section">
                <label>Select Platform</label>
                <div className="toggle-group">
                    <button
                        className={`platform-btn ${platform === 'amazon' ? 'active' : ''}`}
                        onClick={() => setPlatform('amazon')}
                    >
                        Amazon
                    </button>
                    <button
                        className={`platform-btn ${platform === 'flipkart' ? 'active' : ''}`}
                        onClick={() => setPlatform('flipkart')}
                    >
                        Flipkart
                    </button>
                </div>
            </div>

            <div className="section action-section">
                <label>Choose Action</label>
                <div className="action-buttons">
                    <button
                        className={`action-btn ${action === 'search' ? 'active' : ''}`}
                        onClick={() => setAction('search')}
                    >
                        <Search size={18} />
                        <span>Search Product</span>
                    </button>
                    <button
                        className={`action-btn ${action === 'order' ? 'active' : ''}`}
                        onClick={() => setAction('order')}
                    >
                        <ShoppingCart size={18} />
                        <span>Place Order</span>
                    </button>
                </div>
            </div>

            <div className="section input-section">
                {action === 'search' ? (
                    <>
                        <label>What are you looking for?</label>
                        <textarea
                            value={userMessage}
                            onChange={(e) => setUserMessage(e.target.value)}
                            placeholder="E.g., iPhone 15 Pro Max 256GB Natural Titanium..."
                            rows={4}
                            className="input-area"
                        />
                    </>
                ) : (
                    <>
                        {/* Batch Mode Toggle */}
                        <div className="batch-toggle">
                            <label className="toggle-label">
                                <input
                                    type="checkbox"
                                    checked={isBatchMode}
                                    onChange={(e) => setIsBatchMode(e.target.checked)}
                                />
                                <span className="toggle-text">
                                    <FileSpreadsheet size={16} />
                                    Batch Order (CSV Upload)
                                </span>
                            </label>
                        </div>

                        {isBatchMode ? (
                            <>
                                {/* CSV Upload Section */}
                                <div className="csv-upload-section">
                                    <label>Upload CSV File</label>
                                    <p className="csv-hint">
                                        CSV columns: product_url (required), quantity, color (optional)
                                    </p>
                                    <div className="file-upload-wrapper">
                                        <input
                                            type="file"
                                            ref={fileInputRef}
                                            accept=".csv"
                                            onChange={handleFileUpload}
                                            className="file-input"
                                        />
                                        <button
                                            className="upload-btn"
                                            onClick={() => fileInputRef.current?.click()}
                                        >
                                            <Upload size={18} />
                                            Choose CSV File
                                        </button>
                                    </div>

                                    {/* CSV Preview */}
                                    {csvData.length > 0 && (
                                        <div className="csv-preview">
                                            <div className="csv-preview-header">
                                                <span>{csvData.length} items loaded</span>
                                                <button className="clear-btn" onClick={clearCsv}>
                                                    Clear All
                                                </button>
                                            </div>
                                            <div className="csv-items-list">
                                                {csvData.map((item, idx) => (
                                                    <div key={idx} className="csv-item">
                                                        <div className="csv-item-info">
                                                            <span className="item-index">#{idx + 1}</span>
                                                            <span className="item-url" title={item.product_url}>
                                                                {item.product_url.length > 40
                                                                    ? item.product_url.substring(0, 40) + '...'
                                                                    : item.product_url}
                                                            </span>
                                                            <span className="item-qty">Qty: {item.quantity}</span>
                                                            {item.color && (
                                                                <span className="item-color">{item.color}</span>
                                                            )}
                                                        </div>
                                                        <button
                                                            className="remove-item-btn"
                                                            onClick={() => removeItem(idx)}
                                                        >
                                                            <X size={14} />
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <label style={{ marginTop: '1rem' }}>Additional Instructions (Optional)</label>
                                <textarea
                                    value={userMessage}
                                    onChange={(e) => setUserMessage(e.target.value)}
                                    placeholder="E.g., Use COD for all orders..."
                                    rows={2}
                                    className="input-area"
                                />
                            </>
                        ) : (
                            <>
                                <label>Product URL to Order</label>
                                <input
                                    type="text"
                                    value={productUrl}
                                    onChange={(e) => setProductUrl(e.target.value)}
                                    placeholder="Paste the full product URL here..."
                                    className="input-field"
                                />
                                <label style={{ marginTop: '1rem' }}>Quantity</label>
                                <input
                                    type="number"
                                    value={quantity}
                                    onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
                                    placeholder="Enter quantity"
                                    min="1"
                                    className="input-field"
                                    style={{ width: '150px' }}
                                />
                                <label style={{ marginTop: '1rem' }}>Additional Instructions (Optional)</label>
                                <textarea
                                    value={userMessage}
                                    onChange={(e) => setUserMessage(e.target.value)}
                                    placeholder="E.g., Any specific delivery instructions..."
                                    rows={2}
                                    className="input-area"
                                />
                            </>
                        )}
                    </>
                )}
            </div>

            <button
                className={`run-btn ${isRunning ? 'running' : ''}`}
                onClick={action === 'order' && isBatchMode ? onRunBatch : onRun}
                disabled={isRunning || (action === 'search' ? !userMessage : (isBatchMode ? csvData.length === 0 : !productUrl))}
            >
                {isRunning
                    ? 'Agent is Working...'
                    : action === 'search'
                        ? 'Start Search'
                        : isBatchMode
                            ? `Start Batch Order (${csvData.length} items)`
                            : 'Start Order'}
            </button>
        </div>
    );
};

export default ControlPanel;
