import { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([
    { role: 'ai', text: 'Hello! I am **ExecuAI** — your Enterprise AI Assistant. Try asking anything or initiate live peer messaging via:\n\n• "lets chat @[colleague name]"\n• Direct queries on system records' }
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
  const [peerChatUser, setPeerChatUser] = useState(null);

  // Input typing feedback state
  const [isFocused, setIsFocused] = useState(false);
  const [showTypingDots, setShowTypingDots] = useState(false);

  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  // Fetch accounts on mount and periodically refresh online presence status
  useEffect(() => {
    const fetchAccounts = () => {
      fetch('http://localhost:8000/api/auth/employees')
        .then(res => res.json())
        .then(data => setSeedAccounts(data))
        .catch(err => console.log('Failed to fetch seed accounts', err));
    };
    fetchAccounts();
    const interval = setInterval(fetchAccounts, 3000);
    return () => clearInterval(interval);
  }, []);

  // Poll for live incoming real-time peer-to-peer messages
  useEffect(() => {
    if (!user) return;

    const pollInterval = setInterval(() => {
      fetch(`http://localhost:8000/api/chat/peer/poll?email=${encodeURIComponent(user.email)}`)
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data) && data.length > 0) {
            data.forEach(msg => {
              setMessages(prev => [...prev, {
                role: 'peer',
                peerName: msg.sender_name,
                peerRole: msg.sender_role,
                text: msg.text
              }]);
            });
          }
        })
        .catch(() => {});
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [user]);

  // Auto-scroll chat history
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

  const availablePeers = seedAccounts.filter(acc => acc.email !== user?.email);
  const showPeerMenu = input.toLowerCase().includes('lets chat') && input.includes('@') && !peerChatUser;

  const selectPeerUser = (peer) => {
    // Check real presence status: if offline, AI informs user and prevents fake auto-replies
    if (!peer.is_online) {
      setMessages(prev => [...prev, {
        role: 'ai',
        text: `⚠️ **Personnel Unavailable:** The colleague you are trying to reach (**${peer.name}**) is currently offline/unavailable. Real-time direct feed connection cannot be established until they authenticate their terminal.`
      }]);
      setInput('');
      return;
    }

    setPeerChatUser(peer);
    setInput('');
    setMessages(prev => [...prev, {
      role: 'ai',
      text: `🔗 **Direct Channel Established:** Interfacing live one-on-one direct feed with **${peer.name}** (${peer.role}). Broadcast message below.`
    }]);
    inputRef.current?.focus();
  };

  const handleFocus = () => {
    setIsFocused(true);
    if (input.length === 0) {
      setShowTypingDots(true);
      const timer = setTimeout(() => setShowTypingDots(false), 1200);
      return () => clearTimeout(timer);
    }
  };

  const handleBlur = () => {
    setIsFocused(false);
    setShowTypingDots(false);
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();

    // If live peer-to-peer chat mode is active, transmit over backend feed directly
    if (peerChatUser) {
      setMessages(prev => [...prev, { role: 'user', text: userMessage, isPeer: true }]);
      setInput('');

      fetch('http://localhost:8000/api/chat/peer/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sender_email: user.email,
          sender_name: user.name,
          sender_role: user.role,
          recipient_email: peerChatUser.email,
          text: userMessage
        })
      }).catch(err => console.log('Failed to broadcast peer message', err));

      return;
    }

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

  const formatMessage = (text) => {
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

  const handleLogout = () => {
    if (user) {
      fetch('http://localhost:8000/api/auth/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: user.email })
      }).catch(() => {});
    }
    setUser(null);
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

  // Login Authentication shell screen
  if (!user) {
    return (
      <div className="login-wrapper">
        <div className="login-card">
          <div className="login-header">
            <h2>ExecuAI Access Portal</h2>
            <p>Secure Enterprise Portal Authentication</p>
          </div>

          <form onSubmit={handleLogin}>
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
            <div style={{ marginTop: '20px', textAlign: 'center' }}>
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.26)' }}>Quick Demo Accounts (Password: <strong>admin123</strong>)</span>
              <div className="account-pills">
                {seedAccounts.map((acc) => (
                  <div
                    key={acc.id}
                    className="account-pill"
                    onClick={() => { setLoginEmail(acc.email); setLoginPassword('admin123'); }}
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
    <div className="shell">
      <div className="glow-orb"></div>
      <div className="glow-orb2"></div>

      <div className="topbar">
        <div className="brand">
          <div className="brand-icon">⚡</div>
          <span className="brand-name">ExecuAI</span>
          <div className="brand-sep"></div>
          <span className="brand-sub">Enterprise Assistant</span>
        </div>
        <div className="topbar-right">
          <div className="avatar" title={user?.role || 'Guest'}>
            {user ? user.name.split(' ').map(n => n[0]).join('') : 'SK'}
          </div>
          <button className="btn-ghost" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </div>

      <div className="body">
        {/* Leftmost panel: AI Chat Stream */}
        <div className="panel">
          <div className="panel-top">
            <span className="panel-title">AI Assistant</span>
            <span className="status-dot">
              <span className="dot"></span>
              {isLoading ? 'Processing...' : 'Ready'}
            </span>
          </div>

          <div className="context-card">
            Logged in as <strong>{user?.role || 'Executive'}</strong> ({user?.department || 'Operations'}). Your security-level toolset has been loaded.
          </div>

          <div className="spacer">
            <div className="chat-history" id="chat-history">
              {messages.map((m, i) => (
                <div key={i} className={`chat-bubble ${m.role} ${m.isPeer ? 'peer-user' : ''}`}>
                  {m.role === 'peer' && (
                    <div className="peer-badge">
                      <span className="peer-icon">💬</span> {m.peerName} <span className="peer-role-tag">({m.peerRole})</span>
                    </div>
                  )}
                  {m.intent && intentLabels[m.intent] && (
                    <span
                      className="msg-intent-tag"
                      style={{ borderColor: intentLabels[m.intent].color + '66', color: intentLabels[m.intent].color }}
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
          </div>

          {/* Interactive Chat Input Area with Live Peer Overlays */}
          <div className="chat-input-wrapper">
            {/* Peer Auto-Complete Dropdown Menu */}
            {showPeerMenu && availablePeers.length > 0 && (
              <div className="peer-menu-overlay">
                <div className="peer-menu-header">Select Colleague to Live Chat:</div>
                <div className="peer-menu-list">
                  {availablePeers.map(peer => (
                    <div
                      key={peer.id}
                      className="peer-menu-item"
                      onClick={() => selectPeerUser(peer)}
                    >
                      <div className="peer-item-avatar">{peer.name[0]}</div>
                      <div className="peer-item-info">
                        <div className="peer-item-name">
                          {peer.name}
                          <span style={{
                            display: 'inline-block',
                            width: '6px', height: '6px',
                            borderRadius: '50%',
                            background: peer.is_online ? '#10b981' : 'rgba(255,255,255,0.2)',
                            marginLeft: '6px',
                            boxShadow: peer.is_online ? '0 0 6px #10b981' : 'none'
                          }} title={peer.is_online ? "Online" : "Offline"} />
                        </div>
                        <div className="peer-item-role">{peer.role} • {peer.department}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Typing Area Indicator for Peer Chat */}
            {peerChatUser && (
              <div className="active-peer-status">
                <div className="peer-status-left">
                  <span className="live-dot"></span>
                  <span>Live Channel: <strong>@{peerChatUser.name.split(' ')[0]}</strong></span>
                </div>
                <button
                  className="exit-peer-btn"
                  onClick={() => {
                    setPeerChatUser(null);
                    setMessages(prev => [...prev, { role: 'ai', text: 'Switched back to **ExecuAI Enterprise Assistant** mode.' }]);
                  }}
                  title="Switch back to AI Assistant"
                >
                  Exit Chat ✕
                </button>
              </div>
            )}

            <div className="input-wrap">
              <div className={`typing-dots ${showTypingDots && input.length === 0 ? 'visible' : ''}`}>
                <span></span><span></span><span></span>
              </div>
              <input
                ref={inputRef}
                className={`input-field ${input.length > 0 ? 'typing' : ''}`}
                id="mainInput"
                type="text"
                placeholder={peerChatUser ? `Direct Message @${peerChatUser.name.split(' ')[0]}...` : "Ask anything… (e.g. lets chat @)"}
                maxLength={200}
                autoComplete="off"
                value={input}
                onFocus={handleFocus}
                onBlur={handleBlur}
                onChange={e => {
                  setInput(e.target.value);
                  if (e.target.value.length > 0) setShowTypingDots(false);
                }}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
                disabled={isLoading}
              />
              <button
                className={`btn-send ${input.length > 0 ? 'active' : ''}`}
                id="sendBtn"
                onClick={handleSend}
                disabled={isLoading}
                aria-label="Send"
              >
                ↑
              </button>
            </div>
            <div className={`char-counter ${input.length > 0 ? 'visible' : ''}`}>
              {input.length} / 200
            </div>
          </div>
        </div>

        {/* Right panel: Execution Pipeline & Metadata stats */}
        <div className="pipeline-panel">
          <div className="pipeline-header-stats">
            <div className="stat-row">
              <span className="stat-label">Current Intent:</span>
              <span className="intent-pill" style={{ padding: '2px 8px', fontSize: '11px' }}>
                {currentIntent ? (intentLabels[currentIntent]?.label || currentIntent) : 'Awaiting input'}
              </span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Steps Executed:</span>
              <span className="stat-val">{executionSteps.filter((_, i) => i <= activeStep).length} / {executionSteps.length}</span>
            </div>
            {executionTime !== null && (
              <div className="stat-row">
                <span className="stat-label">Execution Time:</span>
                <span className="stat-val">{executionTime.toFixed(2)}s</span>
              </div>
            )}
          </div>

          <div className="divider" style={{ margin: '14px 0 18px 0' }}></div>

          <div className="sec-title">Execution pipeline</div>
          {executionSteps.length === 0 ? (
            <div className="pipeline-empty">
              <div className="pipeline-icon-wrap">
                🚀
              </div>
              <p className="pipeline-hint">Send a message to see the agent's execution pipeline</p>
            </div>
          ) : (
            executionSteps.map((step, i) => {
              const isDone = i <= activeStep;
              const isActive = i === activeStep && isLoading;
              const statusClass = isDone ? 'done' : isActive ? 'active' : '';
              const cleanStep = step.replace(/^[✅❌⏭️🔍🧠📋]\s*/, '');

              return (
                <div key={i} className={`timeline-item ${statusClass}`}>
                  <div className="timeline-marker">
                    {isDone ? '✓' : isActive ? '•' : i + 1}
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
      </div>
    </div>
  );
}

export default App;
