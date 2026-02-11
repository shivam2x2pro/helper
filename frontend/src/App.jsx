import React, { useState } from 'react';
import ControlPanel from './components/ControlPanel';
import ChatInterface from './components/ChatInterface';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [platform, setPlatform] = useState('amazon');
  const [action, setAction] = useState('search');
  const [userMessage, setUserMessage] = useState('');
  const [productUrl, setProductUrl] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [logs, setLogs] = useState([]);
  const [isRunning, setIsRunning] = useState(false);

  // Batch Order State
  const [isBatchMode, setIsBatchMode] = useState(false);
  const [csvData, setCsvData] = useState([]);
  const [batchStatus, setBatchStatus] = useState([]);

  // HITL State
  const [hitlData, setHitlData] = useState({ isOpen: false, question: '', sessionId: '' });

  // Product Choices State
  const [productChoices, setProductChoices] = useState({ isOpen: false, message: '', products: [], sessionId: '' });

  // Address Choices State
  const [addressChoices, setAddressChoices] = useState({ isOpen: false, message: '', addresses: [], sessionId: '' });

  // Payment Choices State
  const [paymentChoices, setPaymentChoices] = useState({ isOpen: false, message: '', payments: [], sessionId: '' });

  // General Options State
  const [generalOptions, setGeneralOptions] = useState({ isOpen: false, message: '', options: [], optionType: 'general', sessionId: '' });

  const runAgent = async () => {
    setIsRunning(true);
    setLogs([]); // Clear previous logs

    try {
      const response = await fetch(`${API_BASE_URL}/agent/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform,
          action,
          user_message: userMessage,
          product_url: productUrl || undefined,
          quantity: action === 'order' ? quantity : undefined
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6);
              if (!jsonStr) continue;
              const event = JSON.parse(jsonStr);

              handleEvent(event);
            } catch (e) {
              console.error("Error parsing SSE:", e);
            }
          }
        }
      }
    } catch (error) {
      console.error("Stream error:", error);
      setLogs(prev => [...prev, { type: 'error', content: `Connection error: ${error.message}` }]);
    } finally {
      setIsRunning(false);
    }
  };

  const runBatchAgent = async () => {
    setIsRunning(true);
    setLogs([]);
    setBatchStatus([]);

    try {
      const response = await fetch(`${API_BASE_URL}/agent/batch-order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform,
          items: csvData,
          additional_instructions: userMessage || undefined
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6);
              if (!jsonStr) continue;
              const event = JSON.parse(jsonStr);
              handleEvent(event);
            } catch (e) {
              console.error("Error parsing SSE:", e);
            }
          }
        }
      }
    } catch (error) {
      console.error("Batch stream error:", error);
      setLogs(prev => [...prev, { type: 'error', content: `Connection error: ${error.message}` }]);
    } finally {
      setIsRunning(false);
    }
  };

  const handleEvent = (event) => {
    if (!event) return;

    if (event.type === 'config') {
      // Log the agent configuration (temperature, etc.)
      const config = event.content;
      setLogs(prev => [...prev, {
        type: 'text',
        content: `Agent started: ${config.platform}/${config.action} (temperature: ${config.temperature})`,
        timestamp: new Date()
      }]);
    } else if (event.type === 'batch_start') {
      // Batch order started
      const config = event.content;
      setLogs(prev => [...prev, {
        type: 'batch-start',
        content: `Batch order started: ${config.total_items} items on ${config.platform}`,
        timestamp: new Date()
      }]);
    } else if (event.type === 'batch_status') {
      // Update batch status
      setBatchStatus(event.content);
    } else if (event.type === 'batch_complete') {
      // Batch order completed
      const result = event.content;
      setLogs(prev => [...prev, {
        type: 'batch-complete',
        content: `Batch completed: ${result.success}/${result.total} succeeded, ${result.failed} failed`,
        results: result.results,
        timestamp: new Date()
      }]);
    } else if (event.type === 'log') {
      setLogs(prev => [...prev, { type: 'text', content: event.content, timestamp: new Date() }]);
    } else if (event.type === 'request_input') {
      setHitlData({
        isOpen: true,
        question: event.content,
        sessionId: event.session_id
      });
    } else if (event.type === 'product_choices') {
      setProductChoices({
        isOpen: true,
        message: event.content.message,
        products: event.content.products,
        sessionId: event.session_id
      });
      setLogs(prev => [...prev, { type: 'text', content: `Found ${event.content.products.length} products. Please select one...`, timestamp: new Date() }]);
    } else if (event.type === 'address_choices') {
      setAddressChoices({
        isOpen: true,
        message: event.content.message,
        addresses: event.content.addresses,
        sessionId: event.session_id
      });
      setLogs(prev => [...prev, { type: 'text', content: `Found ${event.content.addresses.length} delivery addresses. Please select one...`, timestamp: new Date() }]);
    } else if (event.type === 'payment_choices') {
      setPaymentChoices({
        isOpen: true,
        message: event.content.message,
        payments: event.content.payments,
        sessionId: event.session_id
      });
      setLogs(prev => [...prev, { type: 'text', content: `Available payment methods. Please select one...`, timestamp: new Date() }]);
    } else if (event.type === 'options') {
      setGeneralOptions({
        isOpen: true,
        message: event.content.message,
        options: event.content.options,
        optionType: event.content.option_type || 'general',
        sessionId: event.session_id
      });
      setLogs(prev => [...prev, { type: 'text', content: `${event.content.message}`, timestamp: new Date() }]);
    } else if (event.type === 'result') {
      try {
        const parsed = JSON.parse(event.content);
        setLogs(prev => [...prev, { type: 'result-json', content: parsed, timestamp: new Date() }]);
      } catch (e) {
        setLogs(prev => [...prev, { type: 'success', content: `**Result:** ${event.content}`, timestamp: new Date() }]);
      }
    } else if (event.type === 'error') {
      setLogs(prev => [...prev, { type: 'error', content: `**Error:** ${event.content}`, timestamp: new Date() }]);
    }
  };

  const handleHitlSubmit = async (sessionId, input) => {
    try {
      const response = await fetch(`${API_BASE_URL}/agent/input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, input_data: input })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const result = await response.json();
      if (result.status === 'error') {
        throw new Error(result.message || 'Unknown error');
      }

      setHitlData(prev => ({ ...prev, isOpen: false }));
    } catch (error) {
      console.error("Failed to submit input:", error);
      setLogs(prev => [...prev, { type: 'error', content: `Failed to submit input: ${error.message}`, timestamp: new Date() }]);
    }
  };

  const handleProductSelect = async (sessionId, selectedIndex, product) => {
    try {
      const response = await fetch(`${API_BASE_URL}/agent/input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, input_data: String(selectedIndex) })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const result = await response.json();
      if (result.status === 'error') {
        throw new Error(result.message || 'Unknown error');
      }

      setProductChoices(prev => ({ ...prev, isOpen: false }));
      setLogs(prev => [...prev, { type: 'text', content: `Selected: ${product.product_name}`, timestamp: new Date() }]);
    } catch (error) {
      console.error("Failed to submit selection:", error);
      setLogs(prev => [...prev, { type: 'error', content: `Failed to submit selection: ${error.message}`, timestamp: new Date() }]);
    }
  };

  const handleAddressSelect = async (sessionId, selectedIndex, address) => {
    try {
      const response = await fetch(`${API_BASE_URL}/agent/input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, input_data: String(selectedIndex) })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const result = await response.json();
      if (result.status === 'error') {
        throw new Error(result.message || 'Unknown error');
      }

      setAddressChoices(prev => ({ ...prev, isOpen: false }));
      setLogs(prev => [...prev, { type: 'text', content: `Selected address: ${address.name} - ${address.address}`, timestamp: new Date() }]);
    } catch (error) {
      console.error("Failed to submit address selection:", error);
      setLogs(prev => [...prev, { type: 'error', content: `Failed to submit selection: ${error.message}`, timestamp: new Date() }]);
    }
  };

  const handlePaymentSelect = async (sessionId, selectedIndex, payment) => {
    try {
      const response = await fetch(`${API_BASE_URL}/agent/input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, input_data: String(selectedIndex) })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const result = await response.json();
      if (result.status === 'error') {
        throw new Error(result.message || 'Unknown error');
      }

      setPaymentChoices(prev => ({ ...prev, isOpen: false }));
      setLogs(prev => [...prev, { type: 'text', content: `Selected payment: ${payment.method}`, timestamp: new Date() }]);
    } catch (error) {
      console.error("Failed to submit payment selection:", error);
      setLogs(prev => [...prev, { type: 'error', content: `Failed to submit selection: ${error.message}`, timestamp: new Date() }]);
    }
  };

  const handleOptionSelect = async (sessionId, selectedIndex, option) => {
    try {
      const response = await fetch(`${API_BASE_URL}/agent/input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, input_data: String(selectedIndex) })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const result = await response.json();
      if (result.status === 'error') {
        throw new Error(result.message || 'Unknown error');
      }

      setGeneralOptions(prev => ({ ...prev, isOpen: false }));
      setLogs(prev => [...prev, { type: 'text', content: `Selected: ${option.label}`, timestamp: new Date() }]);
    } catch (error) {
      console.error("Failed to submit option selection:", error);
      setLogs(prev => [...prev, { type: 'error', content: `Failed to submit selection: ${error.message}`, timestamp: new Date() }]);
    }
  };

  return (
    <div className="app-container">
      <div className="main-layout">
        <ControlPanel
          platform={platform} setPlatform={setPlatform}
          action={action} setAction={setAction}
          userMessage={userMessage} setUserMessage={setUserMessage}
          productUrl={productUrl} setProductUrl={setProductUrl}
          quantity={quantity} setQuantity={setQuantity}
          onRun={runAgent}
          isRunning={isRunning}
          isBatchMode={isBatchMode} setIsBatchMode={setIsBatchMode}
          csvData={csvData} setCsvData={setCsvData}
          onRunBatch={runBatchAgent}
        />

        <ChatInterface
          logs={logs}
          hitlData={hitlData}
          onHitlSubmit={handleHitlSubmit}
          productChoices={productChoices}
          onProductSelect={handleProductSelect}
          addressChoices={addressChoices}
          onAddressSelect={handleAddressSelect}
          paymentChoices={paymentChoices}
          onPaymentSelect={handlePaymentSelect}
          generalOptions={generalOptions}
          onOptionSelect={handleOptionSelect}
          batchStatus={batchStatus}
        />
      </div>
    </div>
  );
}

export default App;
