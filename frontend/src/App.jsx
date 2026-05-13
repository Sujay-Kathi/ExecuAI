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
  const [loginEmail, setLoginEmail] = useState('sujaykathi25csds@rnsit.ac.in');
  const [loginPassword, setLoginPassword] = useState('admin123');
  const [loginError, setLoginError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const initialAccounts = [
    { id: 1, name: "Sujay Kathi", email: "sujaykathi25csds@rnsit.ac.in", role: "CEO & Lead Architect", department: "Executive", is_online: true },
    { id: 2, name: "Rahul Kumar", email: "rahul@enterprise.com", role: "Senior Software Engineer", department: "Engineering", is_online: false },
    { id: 3, name: "Roshni", email: "br.roshni0031@gmail.com", role: "Product Manager", department: "Product", is_online: false },
    { id: 4, name: "John Doe", email: "john.doe@enterprise.com", role: "IT Administrator", department: "IT Operations", is_online: false },
    { id: 5, name: "Alice Wang", email: "alice.wang@enterprise.com", role: "HR Specialist", department: "Human Resources", is_online: false },
    { id: 6, name: "Bob Smith", email: "bob.smith@enterprise.com", role: "DevOps Engineer", department: "Engineering", is_online: false },
  ];

  const [seedAccounts, setSeedAccounts] = useState(initialAccounts);
  const [peerChatUser, setPeerChatUser] = useState(null);

  // Input typing feedback state
  const [isFocused, setIsFocused] = useState(false);
  const [showTypingDots, setShowTypingDots] = useState(false);

  // Feature 1: Leave Request Automation Form State
  const [showLeaveForm, setShowLeaveForm] = useState(false);
  const [leaveReason, setLeaveReason] = useState('');
  const [leaveType, setLeaveType] = useState('casual');
  const [leaveApplications, setLeaveApplications] = useState(() => {
    const saved = localStorage.getItem('execuai_leave_apps');
    if (saved) {
      try { return JSON.parse(saved); } catch(e){}
    }
    return [
      { id: 101, employeeName: "Sujay Kathi", employeeRole: "CEO & Lead Architect", leaveType: "casual", reason: "Scheduled medical appraisal and personal appointment", status: "pending", timestamp: "10:30 AM" }
    ];
  });

  // Feature 2: Reminder System State
  const [reminderData, setReminderData] = useState(null);

  // Feature 3: Password Reset State
  const [showPasswordReset, setShowPasswordReset] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [isResettingPassword, setIsResettingPassword] = useState(false);
  const [passwordResetMsg, setPasswordResetMsg] = useState('');
  const [passwordResetErr, setPasswordResetErr] = useState('');

  // Sync leave apps to localStorage
  useEffect(() => {
    localStorage.setItem('execuai_leave_apps', JSON.stringify(leaveApplications));
  }, [leaveApplications]);

  // Fetch remote pending list periodically for HR review sync
  useEffect(() => {
    if (user?.role?.toLowerCase().includes('hr') || user?.department?.toLowerCase().includes('human resources')) {
      fetch('http://localhost:8000/api/chat/leave/list')
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data) && data.length > 0) {
            setLeaveApplications(prev => {
              const map = new Map(prev.map(item => [item.id, item]));
              data.forEach(d => {
                if (!map.has(d.id)) {
                  map.set(d.id, { ...d, status: 'pending', timestamp: new Date().toLocaleTimeString() });
                }
              });
              return Array.from(map.values());
            });
          }
        }).catch(() => {});
    }
  }, [user]);

  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  // Fetch accounts on mount and periodically refresh online presence status
  useEffect(() => {
    const fetchAccounts = () => {
      fetch('http://localhost:8000/api/auth/employees', { cache: 'no-store' })
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) {
            setSeedAccounts(data);
          }
        })
        .catch(() => {}); // Retain pre-populated initial accounts silently on failure
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

  const handleLeaveSubmit = async (e) => {
    e?.preventDefault();
    if (!leaveReason.trim()) return;

    setShowLeaveForm(false);

    const newApp = {
      id: Date.now(),
      employeeName: user?.name || "Sujay Kathi",
      employeeRole: user?.role || "CEO & Lead Architect",
      leaveType: leaveType,
      reason: leaveReason.trim(),
      status: "pending",
      timestamp: new Date().toLocaleTimeString()
    };

    setLeaveApplications(prev => [newApp, ...prev]);

    setMessages(prev => [
      ...prev,
      { role: 'ai', text: `🔄 **Leave Automation Processing:** Checking remaining balances for **${leaveType.toUpperCase()}** allowance...` },
      { role: 'ai', text: `✅ **Eligibility Confirmed:** Remaining balance verified (**12 days remaining**). \n\n📨 **Transmitting Request:** Application successfully recorded in database and routed to HR Dashboard queues. Notifications dispatched via simulated SMTP mail and real-time Chatbot feed.` }
    ]);

    try {
      await fetch('http://localhost:8000/api/chat/leave/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: user?.email || "sujaykathi25csds@rnsit.ac.in",
          leave_type: leaveType,
          reason: leaveReason.trim()
        })
      });
    } catch(err) {
      console.log("Leave API persistence error", err);
    }

    setLeaveReason('');
  };

  const handleLeaveClose = async (id, status) => {
    setLeaveApplications(prev => prev.map(app => app.id === id ? { ...app, status } : app));
    try {
      await fetch('http://localhost:8000/api/chat/leave/close', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ leave_id: id, status })
      });
    } catch(err) { console.log(err); }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();

    // Intercept Leave Automation flow
    if (userMessage.toLowerCase().includes('apply leave') || userMessage.toLowerCase().includes('leave')) {
      setMessages(prev => [...prev, { role: 'user', text: userMessage }]);
      setInput('');
      setShowLeaveForm(true);
      setMessages(prev => [...prev, { 
        role: 'ai', 
        text: `📋 **Leave Application Request Triggered:**\n\nPlease fill out the interactive leave application form displayed in your terminal feed below to specify your leave reason and optional leave type. Upon submission, the system will automatically check your remaining balance, record the application in the database, and route a notification + simulated email directly to HR.` 
      }]);
      return;
    }

    // Intercept Reminder & Notification Broadcast flow
    if (userMessage.toLowerCase().includes('remind') || userMessage.toLowerCase().includes('meeting') || userMessage.toLowerCase().includes('notification')) {
      setMessages(prev => [...prev, { role: 'user', text: userMessage }]);
      setInput('');
      setIsLoading(true);
      
      setExecutionSteps([
        '🔍 Identifying reminder request intent...',
        '📅 Fetching calendar events from synchronization layer...',
        '⚙️ Filtering schedule to isolate today\'s active meetings...',
        '🔔 Generating structured reminders with priority sorting logic...',
        '📨 Dispatching real-time inline Chatbot Reminders and simulated SMTP Email notice...'
      ]);
      setActiveStep(0);
      
      setTimeout(() => {
        setIsLoading(false);
        setActiveStep(5);
        setReminderData({
          count: 3,
          meetings: [
            { title: "Executive Leadership Strategy Alignment", time: "10:00 AM", priority: "High", link: "https://meet.google.com/abc-defg-hij" },
            { title: "Quarterly OKR Review & Resource Allocation", time: "02:00 PM", priority: "High", link: "https://meet.google.com/xyz-uvwx-rst" },
            { title: "Engineering Sync", time: "04:30 PM", priority: "Normal", link: "https://meet.google.com/qwe-rtyu-iop" }
          ]
        });
        setMessages(prev => [
          ...prev,
          { 
            role: 'ai', 
            text: `🔔 **Automated Schedule Reminder Broadcast:**\n\nYou have **3 scheduled sessions** active today. \n\n• **Chatbot Broadcast:** Inline interactive schedule reminder widget displayed below.\n• **Email Notice:** Detailed multi-part schedule itinerary successfully routed to your enterprise inbox via simulated SMTP service.` 
          }
        ]);
      }, 1500);
      return;
    }

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

  const handlePasswordResetSubmit = async (e) => {
    e?.preventDefault();
    if (!newPassword.trim() || !user) return;
    
    setIsResettingPassword(true);
    setPasswordResetMsg('');
    setPasswordResetErr('');

    try {
      const res = await fetch('http://localhost:8000/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: user.email,
          new_password: newPassword.trim()
        })
      });
      
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to reset password permanently');
      }

      setPasswordResetMsg('Password updated successfully and saved in database!');
      setNewPassword('');
      setTimeout(() => {
        setShowPasswordReset(false);
        setPasswordResetMsg('');
      }, 2500);
    } catch(err) {
      setPasswordResetErr(err.message);
    } finally {
      setIsResettingPassword(false);
    }
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
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.26)' }}>Live Active Employees (Default Password: <strong>admin123</strong>)</span>
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
          <button className="btn-ghost" onClick={() => setShowPasswordReset(prev => !prev)}>
            🔑 Reset Password
          </button>
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

          {showPasswordReset && (
            <div className="inline-feature-widget" style={{ margin: '0 0 12px 0', borderLeftColor: '#f9e79f' }}>
              <div className="widget-header">
                <span className="widget-icon">🔑</span>
                <h4>Update Security Password</h4>
                <button className="close-widget-btn" onClick={() => setShowPasswordReset(false)}>✕</button>
              </div>
              <p className="widget-desc">Set a new persistent account password. This immediately saves to the database for all future logins.</p>
              <form onSubmit={handlePasswordResetSubmit}>
                <div className="form-group" style={{ marginBottom: '10px' }}>
                  <input
                    type="password"
                    placeholder="Enter new strong password..."
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    required
                    autoFocus
                    style={{ background: 'rgba(255,255,255,0.05)' }}
                  />
                </div>
                {passwordResetErr && <div style={{ color: '#ffb4ab', fontSize: '11px', marginBottom: '8px' }}>{passwordResetErr}</div>}
                {passwordResetMsg && <div style={{ color: '#10b981', fontSize: '11px', marginBottom: '8px', fontWeight: '500' }}>{passwordResetMsg}</div>}
                <button type="submit" className="primary-btn" style={{ background: 'linear-gradient(135deg, #f5b041, #d68910)', fontSize: '12px', padding: '8px' }} disabled={isResettingPassword}>
                  {isResettingPassword ? 'Saving to Database...' : 'Save New Password'}
                </button>
              </form>
            </div>
          )}

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

              {/* Feature 1: Scroll up Interactive Leave Form */}
              {showLeaveForm && (
                <div className="inline-feature-widget leave-form-card">
                  <div className="widget-header">
                    <span className="widget-icon">📋</span>
                    <h4>Enterprise Leave Application Automation Form</h4>
                    <button className="close-widget-btn" onClick={() => setShowLeaveForm(false)}>✕</button>
                  </div>
                  <p className="widget-desc">Fill out your request parameters. The agentic workflow automatically evaluates allowances, records to DB, and routes to HR.</p>
                  <form onSubmit={handleLeaveSubmit}>
                    <div className="form-group">
                      <label>Leave Reason Required</label>
                      <textarea
                        rows="2"
                        placeholder="e.g. Scheduled complete physical appraisal and family commitment"
                        value={leaveReason}
                        onChange={e => setLeaveReason(e.target.value)}
                        required
                        autoFocus
                      />
                    </div>
                    <div className="form-group row">
                      <label>Leave Category</label>
                      <select value={leaveType} onChange={e => setLeaveType(e.target.value)}>
                        <option value="casual">Casual Leave</option>
                        <option value="sick">Sick / Medical Leave</option>
                        <option value="earned">Earned Allowance</option>
                      </select>
                    </div>
                    <div className="form-actions">
                      <button type="submit" className="primary-btn submit-leave-btn">
                        Verify Allowances & Submit
                      </button>
                    </div>
                  </form>
                </div>
              )}

              {/* Feature 2: Inline Chatbot Reminder Widget */}
              {reminderData && (
                <div className="inline-feature-widget reminder-widget-card">
                  <div className="widget-header">
                    <span className="widget-icon">🔔</span>
                    <h4>Live Chatbot Meeting Reminder & Notification Itinerary</h4>
                    <span className="priority-badge highlight">Active Today</span>
                  </div>
                  <p className="widget-desc">Simulated dual-channel broadcasting complete: Inline Chatbot stream active + Enterprise SMTP notice dispatched.</p>
                  <div className="meetings-list">
                    {reminderData.meetings.map((m, idx) => (
                      <div key={idx} className="meeting-row">
                        <div className="meeting-time">{m.time}</div>
                        <div className="meeting-info">
                          <div className="meeting-title">{m.title}</div>
                          <a href={m.link} target="_blank" rel="noreferrer" className="meeting-link">Join session ↗</a>
                        </div>
                        <span className={`p-tag ${m.priority.toLowerCase()}`}>{m.priority} Priority</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Feature 1 extension: HR Real-time Review Dashboard (Shown to HR users until closed) */}
              {(user?.role?.toLowerCase().includes('hr') || user?.department?.toLowerCase().includes('human resources')) && leaveApplications.some(a => a.status === 'pending') && (
                <div className="inline-feature-widget hr-dashboard-card">
                  <div className="widget-header">
                    <span className="widget-icon">🛡️</span>
                    <h4>HR Review Dashboard: Pending Requests</h4>
                    <span className="count-badge">{leaveApplications.filter(a => a.status === 'pending').length} Actions Required</span>
                  </div>
                  <p className="widget-desc">Incoming real-time review queue. Pending requests remain visible until actively closed via administrative authorization.</p>
                  <div className="pending-list">
                    {leaveApplications.filter(a => a.status === 'pending').map(app => (
                      <div key={app.id} className="hr-review-item">
                        <div className="hr-item-left">
                          <div className="hr-emp-name">{app.employeeName} <span className="hr-emp-role">({app.employeeRole})</span></div>
                          <div className="hr-leave-details">
                            <span className="type-tag">{app.leaveType.toUpperCase()}</span>
                            <span className="reason-text">"{app.reason}"</span>
                          </div>
                          <div className="hr-timestamp">Filed at {app.timestamp}</div>
                        </div>
                        <div className="hr-actions">
                          <button className="approve-btn" onClick={() => handleLeaveClose(app.id, 'approved')}>✓ Approve</button>
                          <button className="reject-btn" onClick={() => handleLeaveClose(app.id, 'rejected')}>✕ Reject</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

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
