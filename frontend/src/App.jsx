import { useState } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([
    { role: 'ai', text: 'Hello! I am your Enterprise AI Assistant. How can I help you today?' }
  ]);
  const [input, setInput] = useState('');
  const [executionLog, setExecutionLog] = useState([
    { step: 1, action: 'Understand Intent', status: 'pending' },
    { step: 2, action: 'Plan Execution', status: 'pending' },
    { step: 3, action: 'Execute Actions', status: 'pending' },
    { step: 4, action: 'Respond', status: 'pending' }
  ]);

  const handleSend = async () => {
    if (!input.trim()) return;
    
    const newMsg = { role: 'user', text: input };
    setMessages([...messages, newMsg]);
    const currentInput = input;
    setInput('');

    setExecutionLog([
      { step: 1, action: 'Understand Intent', status: 'active' },
      { step: 2, action: 'Plan Execution', status: 'pending' },
      { step: 3, action: 'Execute Actions', status: 'pending' },
      { step: 4, action: 'Respond', status: 'pending' }
    ]);

    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: currentInput })
      });
      const data = await res.json();
      
      setExecutionLog([
        { step: 1, action: 'Understand Intent', status: 'done' },
        { step: 2, action: 'Plan Execution', status: 'done' },
        { step: 3, action: 'Execute Actions', status: 'done' },
        { step: 4, action: 'Respond', status: 'done' }
      ]);
      setMessages(msgs => [...msgs, { role: 'ai', text: data.message || 'Request processed successfully. Actions executed.' }]);
    } catch (err) {
      setMessages(msgs => [...msgs, { role: 'ai', text: 'Error connecting to the AI agent.' }]);
      setExecutionLog(logs => logs.map(l => ({ ...l, status: 'pending' })));
    }
  };

  return (
    <div className="dashboard-container">
      {/* Top Navbar */}
      <nav className="top-nav">
        <h1>ExecuAI <span className="subtitle">Enterprise Assistant</span></h1>
        <div className="user-profile">
          <div className="avatar">HR</div>
        </div>
      </nav>

      <main className="main-layout">
        {/* Left: Chat Panel */}
        <section className="glass-card chat-panel">
          <div className="card-header">
            <h2>AI Assistant</h2>
            <div className="pulse-dot"></div>
          </div>
          <div className="chat-history">
            {messages.map((m, i) => (
              <div key={i} className={`chat-bubble ${m.role}`}>
                {m.text}
              </div>
            ))}
          </div>
          <div className="chat-input-area">
            <input 
              type="text" 
              placeholder="E.g., Onboard Rahul as Software Engineer..." 
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
            />
            <button className="primary-btn" onClick={handleSend}>Send</button>
          </div>
        </section>

        {/* Center: Execution Log Panel */}
        <section className="glass-card execution-panel">
          <div className="card-header">
            <h2>Execution Log</h2>
          </div>
          <div className="timeline">
            {executionLog.map((log, i) => (
              <div key={i} className={`timeline-item ${log.status}`}>
                <div className="timeline-marker">
                  {log.status === 'done' && '✓'}
                  {log.status === 'active' && <div className="active-dot"></div>}
                </div>
                <div className="timeline-content">
                  <h4>{log.action}</h4>
                  <p>Step {log.step}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Right: Dashboard Data */}
        <section className="data-panel">
          <div className="glass-card stat-card">
            <h3>Total Headcount</h3>
            <div className="stat-value">1,204</div>
            <div className="trend positive">↑ 12 this month</div>
          </div>
          
          <div className="glass-card stat-card">
            <h3>Pending Leaves</h3>
            <div className="stat-value warning">8</div>
            <div className="progress-bar">
              <div className="progress-fill warning-fill" style={{ width: '40%' }}></div>
            </div>
          </div>
          
          <div className="glass-card stat-card">
            <h3>System Access Requests</h3>
            <div className="stat-value">3</div>
            <div className="progress-bar">
              <div className="progress-fill info-fill" style={{ width: '15%' }}></div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
