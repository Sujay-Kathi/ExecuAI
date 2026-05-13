import { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([
    { role: 'ai', text: 'Hello! I am **ExecuAI** — your Enterprise AI Assistant. Try commands like:\n\n• "Onboard Rahul as Software Engineer"\n• "Schedule meeting about Sprint Planning"\n• "Give access to GitHub for Priya"\n• "Apply for sick leave"\n• "System status"\n• "Reset password for Amit"' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [executionSteps, setExecutionSteps] = useState([]);
  const [currentIntent, setCurrentIntent] = useState(null);
  const [executionTime, setExecutionTime] = useState(null);
  const [activeStep, setActiveStep] = useState(-1);

  // Authentication State
  const [user, setUser] = useState(null);
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [seedAccounts, setSeedAccounts] = useState([]);

  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  // Fetch accounts on mount to allow one-click premium testing
  useEffect(() => {
    fetch('http://localhost:8000/api/auth/employees')
      .then(res => res.json())
      .then(data => setSeedAccounts(data))
      .catch(err => console.log('Failed to fetch seed accounts', err));
  }, []);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Animate execution steps one by one
  useEffect(() => {
    if (isLoading && executionSteps.length > 0 && activeStep < executionSteps.length - 1) {
      const timer = setTimeout(() => {
        setActiveStep(prev => prev + 1);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [isLoading, activeStep, executionSteps]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setMessages(prev => [...prev, { role: 'user', text: userMessage }]);
    setInput('');
    setIsLoading(true);
    setExecutionSteps([]);
    setCurrentIntent(null);
    setExecutionTime(null);
    setActiveStep(-1);

    // Show "thinking" steps
    setExecutionSteps([
      '🔍 Analyzing your request...',
      '🧠 Classifying intent...',
      '📋 Building execution plan...',
    ]);
    setActiveStep(0);

    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage, user_role: user?.role || 'employee' })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Update with real execution steps
      setExecutionSteps(data.execution_log || []);
      setCurrentIntent(data.intent || null);
      setExecutionTime(data.execution_time || null);
      setActiveStep(data.execution_log?.length || 0);
      setIsLoading(false);

      setMessages(prev => [...prev, {
        role: 'ai',
        text: data.reply || 'Request processed successfully.',
        intent: data.intent,
        entities: data.entities,
      }]);

    } catch (err) {
      setIsLoading(false);
      setExecutionSteps(['❌ Connection failed']);
      setActiveStep(0);
      setMessages(prev => [...prev, {
        role: 'ai',
        text: `⚠️ Error connecting to the AI agent: ${err.message}. Make sure the backend is running on port 8000.`
      }]);
    }
  };

  const quickActions = [
    { label: '👤 Onboard', prompt: 'Onboard Rahul as Software Engineer' },
    { label: '🔑 Reset Pwd', prompt: 'Reset password for Amit' },
    { label: '📅 Meeting', prompt: 'Schedule meeting about Sprint Planning' },
    { label: '🏥 Leave', prompt: 'Apply for sick leave from tomorrow' },
    { label: '📊 Attrition', prompt: 'Who is likely to leave the company?' },
    { label: '💚 Health', prompt: 'Check system status' },
    { label: '📋 Tasks', prompt: 'What are my tasks for today?' },
    { label: '📝 Summary', prompt: 'What did I do today?' },
    { label: '📅 Plan Leave', prompt: 'Plan my leave for next month' },
    { label: '📈 Performance', prompt: 'Show my performance insights' },
    { label: '💡 How-To', prompt: 'How to apply for reimbursement?' },
    { label: '⚡ Optimize', prompt: 'Optimize my schedule' },
    { label: '💻 Software', prompt: 'I need IntelliJ IDEA software' },
    { label: '🔔 Updates', prompt: 'What are my important updates?' },
    { label: '🚀 Master Demo', prompt: 'Run a deep audit and retention analysis for Rahul' },
  ];

  const formatMessage = (text) => {
    // Simple markdown-lite: bold, line breaks, bullets
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br/>')
      .replace(/• /g, '<span class="bullet">•</span> ');
  };

  const handleLogin = async (e) => {
    e?.preventDefault();
    if (!loginEmail.trim() || !loginPassword) return;
    setIsLoggingIn(true);
    setLoginError('');
    try {
      const res = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: loginEmail.trim(), password: loginPassword })
      });
      if (!res.ok) {
        throw new Error('Invalid email or password');
      }
      const data = await res.json();
      setUser(data);
      setMessages([
        { role: 'ai', text: `Welcome back, **${data.name}**! 👋\n\nLogged in as **${data.role}** (${data.department}). Depending on your security clearance, your specific toolset has been loaded.` }
      ]);
    } catch (err) {
      setLoginError(err.message);
    } finally {
      setIsLoggingIn(false);
    }
  };

  const getFilteredActions = () => {
    if (!user) return [];
    const r = user.role.toLowerCase();
    const d = user.department.toLowerCase();

    // CEO / Exec / Manager: Sees everything
    if (r.includes('ceo') || r.includes('architect') || d.includes('executive') || r.includes('manager')) {
      return quickActions;
    }
    // HR Specialist / HR
    if (r.includes('hr') || d.includes('human resources')) {
      return quickActions.filter(a => ['👤 Onboard', '🏥 Leave', '📊 Attrition', '🚀 Master Demo'].includes(a.label));
    }
    // IT Administrator / IT Ops
    if (r.includes('it') || d.includes('it operations')) {
      return quickActions.filter(a => ['🔑 Reset Pwd', '💚 Health', '💻 Software'].includes(a.label));
    }
    // Regular Employee
    return quickActions.filter(a => ['🏥 Leave', '📋 Tasks', '📝 Summary', '📅 Plan Leave', '📈 Performance', '💡 How-To', '⚡ Optimize', '💻 Software', '🔔 Updates'].includes(a.label));
  };

  const intentLabels = {
    employee_onboarding: { label: 'Onboarding', color: '#1edce0' },
    it_provisioning: { label: 'IT Provisioning', color: '#d7a4ff' },
    access_management: { label: 'Access Mgmt', color: '#f5b041' },
    leave_request: { label: 'Leave Request', color: '#82e0aa' },
    meeting_scheduling: { label: 'Meeting', color: '#85c1e9' },
    it_ticket: { label: 'IT Ticket', color: '#ffb4ab' },
    password_reset: { label: 'Password Reset', color: '#f9e79f' },
    attrition_prediction: { label: 'ML Prediction', color: '#c39bd3' },
    notification: { label: 'Notification', color: '#abebc6' },
    system_health: { label: 'System Health', color: '#76d7c4' },
    task_management: { label: 'Tasks', color: '#ffcc00' },
    work_summary: { label: 'Activity', color: '#ff9966' },
    smart_leave_planning: { label: 'Leave Plan', color: '#33ccff' },
    performance_insight: { label: 'Performance', color: '#cc99ff' },
    knowledge_assistant: { label: 'Knowledge', color: '#99ff99' },
    workload_optimization: { label: 'Optimize', color: '#ff66ff' },
    it_request_assistant: { label: 'IT Request', color: '#6699ff' },
    notification_intelligence: { label: 'Intelligence', color: '#ff3366' },
    retention_analysis: { label: 'Master Demo', color: '#f39c12' },
    general: { label: 'General', color: '#8b90a0' },
  };

  // If not logged in, render Login View
  if (!user) {
    return (
      <div className="login-wrapper">
        <div className="glass-card login-card">
          <div className="login-header">
            <div className="logo-icon">⚡</div>
            <h2>ExecuAI Access Portal</h2>
            <p>Secure Enterprise Portal Authentication</p>
          </div>

          <form className="login-form" onSubmit={handleLogin}>
            <div className="form-group">
              <label htmlFor="email">Work Email</label>
              <input
                id="email"
                type="email"
                placeholder="name@enterprise.com"
                value={loginEmail}
                onChange={e => setLoginEmail(e.target.value)}
                required
                disabled={isLoggingIn}
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                placeholder="••••••••"
                value={loginPassword}
                onChange={e => setLoginPassword(e.target.value)}
                required
                disabled={isLoggingIn}
              />
            </div>

            {loginError && <div className="login-error">{loginError}</div>}

            <button className="primary-btn" type="submit" disabled={isLoggingIn}>
              {isLoggingIn ? 'Verifying identity...' : 'Authenticate Identity'}
            </button>
          </form>

          {seedAccounts.length > 0 && (
            <div className="login-footer">
              <span>Quick Login Demo Accounts (Password: <strong>password123</strong>)</span>
              <div className="account-pills">
                {seedAccounts.map((acc) => (
                  <div
                    key={acc.id}
                    className="account-pill"
                    onClick={() => { setLoginEmail(acc.email); setLoginPassword('password123'); }}
                    title={`Role: ${acc.role}`}
                  >
                    {acc.name.split(' ')[0]} ({acc.role.split(' ')[0]})
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Top Navbar */}
      <nav className="top-nav">
        <div className="nav-left">
          <div className="logo-icon">⚡</div>
          <h1>ExecuAI <span className="subtitle">Enterprise Assistant</span></h1>
        </div>
        <div className="nav-right">
          {currentIntent && intentLabels[currentIntent] && (
            <div
              className="intent-badge"
              style={{ borderColor: intentLabels[currentIntent].color, color: intentLabels[currentIntent].color }}
            >
              {intentLabels[currentIntent].label}
            </div>
          )}
          <div className="avatar" title={user?.role || 'Guest'}>
            {user ? user.name.split(' ').map(n => n[0]).join('') : '🔒'}
          </div>
          {user && (
            <button
              className="quick-btn"
              style={{ borderColor: 'var(--crimson)', color: 'var(--crimson)' }}
              onClick={() => setUser(null)}
            >
              Sign Out
            </button>
          )}
        </div>
      </nav>

      <main className="main-layout">
        {/* Left: Chat Panel */}
        <section className="glass-card chat-panel" id="chat-panel">
          <div className="card-header">
            <h2>AI Assistant</h2>
            <div className={`status-indicator ${isLoading ? 'processing' : 'idle'}`}>
              <div className="pulse-dot"></div>
              <span>{isLoading ? 'Processing...' : 'Ready'}</span>
            </div>
          </div>

          <div className="chat-history" id="chat-history">
            {messages.map((m, i) => (
              <div key={i} className={`chat-bubble ${m.role} ${m.role === 'ai' ? 'fade-in' : ''}`}>
                {m.intent && intentLabels[m.intent] && (
                  <span
                    className="msg-intent-tag"
                    style={{ background: intentLabels[m.intent].color + '22', color: intentLabels[m.intent].color }}
                  >
                    {intentLabels[m.intent].label}
                  </span>
                )}
                <span dangerouslySetInnerHTML={{ __html: formatMessage(m.text) }} />
              </div>
            ))}
            {isLoading && (
              <div className="chat-bubble ai typing-indicator">
                <span className="dot"></span>
                <span className="dot"></span>
                <span className="dot"></span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Quick Actions */}
          <div className="quick-actions" id="quick-actions">
            {getFilteredActions().map((qa, i) => (
              <button
                key={i}
                className="quick-btn"
                onClick={() => { setInput(qa.prompt); inputRef.current?.focus(); }}
                disabled={isLoading}
              >
                {qa.label}
              </button>
            ))}
          </div>

          <div className="chat-input-area">
            <input
              ref={inputRef}
              id="chat-input"
              type="text"
              placeholder="E.g., Onboard Rahul as Software Engineer..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              disabled={isLoading}
            />
            <button className="primary-btn" onClick={handleSend} disabled={isLoading} id="send-btn">
              {isLoading ? '⏳' : 'Send'}
            </button>
          </div>
        </section>

        {/* Center: Dynamic Execution Log Panel */}
        <section className="glass-card execution-panel" id="execution-panel">
          <div className="card-header">
            <h2>Execution Pipeline</h2>
            {executionTime !== null && (
              <span className="exec-time">{executionTime.toFixed(2)}s</span>
            )}
          </div>
          <div className="timeline" id="execution-timeline">
            {executionSteps.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">🚀</div>
                <p>Send a message to see the agent's execution pipeline</p>
              </div>
            ) : (
              executionSteps.map((step, i) => {
                const isDone = i <= activeStep;
                const isActive = i === activeStep && isLoading;
                const statusClass = isDone ? 'done' : isActive ? 'active' : 'pending';
                const icon = step.startsWith('✅') ? '✅' :
                             step.startsWith('❌') ? '❌' :
                             step.startsWith('⏭️') ? '⏭️' :
                             step.startsWith('🔍') || step.startsWith('🧠') || step.startsWith('📋') ? step.charAt(0) + step.charAt(1) :
                             isDone ? '✓' : '';
                const cleanStep = step.replace(/^[✅❌⏭️🔍🧠📋]\s*/, '');

                return (
                  <div key={i} className={`timeline-item ${statusClass}`} style={{ animationDelay: `${i * 0.08}s` }}>
                    <div className="timeline-marker">
                      {isActive ? <div className="active-dot"></div> :
                       isDone ? <span className="check-mark">{icon || '✓'}</span> :
                       <span className="step-num">{i + 1}</span>}
                    </div>
                    <div className="timeline-content">
                      <h4>{cleanStep}</h4>
                      <p>Step {i + 1} of {executionSteps.length}</p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>

        {/* Right: Dashboard Stats */}
        <section className="data-panel" id="stats-panel">
          <div className="glass-card stat-card">
            <h3>Agent Capabilities</h3>
            <div className="stat-value accent-teal">10</div>
            <div className="trend positive">Workflows active</div>
          </div>

          <div className="glass-card stat-card">
            <h3>Current Intent</h3>
            <div className="intent-display">
              {currentIntent ? (
                <span
                  className="intent-pill"
                  style={{
                    background: (intentLabels[currentIntent]?.color || '#8b90a0') + '22',
                    color: intentLabels[currentIntent]?.color || '#8b90a0',
                    borderColor: (intentLabels[currentIntent]?.color || '#8b90a0') + '44',
                  }}
                >
                  {intentLabels[currentIntent]?.label || currentIntent}
                </span>
              ) : (
                <span className="intent-pill idle-pill">Awaiting input</span>
              )}
            </div>
          </div>

          <div className="glass-card stat-card">
            <h3>Steps Executed</h3>
            <div className="stat-value">{executionSteps.filter((_, i) => i <= activeStep).length}</div>
            <div className="progress-bar">
              <div
                className="progress-fill info-fill"
                style={{ width: executionSteps.length ? `${((activeStep + 1) / executionSteps.length) * 100}%` : '0%' }}
              ></div>
            </div>
          </div>

          <div className="glass-card stat-card">
            <h3>Execution Time</h3>
            <div className="stat-value accent-purple">
              {executionTime !== null ? `${executionTime.toFixed(2)}s` : '—'}
            </div>
            <div className="trend positive">
              {executionTime !== null && executionTime < 1 ? '⚡ Blazing fast' : executionTime !== null ? '✓ Completed' : 'Waiting...'}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
