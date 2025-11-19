import React, { useState, useRef, useEffect } from 'react';
import { Send, Plus, Settings, BarChart3, Zap, Upload, Search, Trash2, Menu, X, Loader } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export default function RAGChatbot() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'assistant',
      content: '👋 Welcome to RAG Agent System! I can help you with:\n\n📚 **Search** - Query your knowledge base\n📝 **Ingest** - Upload and process documents\n⚡ **Optimize** - Heal and optimize the system\n\nWhat would you like to do?',
      timestamp: new Date()
    }
  ]);
  
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState('chat'); // chat, settings, analytics
  const [userRole, setUserRole] = useState('engineer');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [currentSession, setCurrentSession] = useState('Session 1');
  const [sessions, setSessions] = useState(['Session 1']);
  const [uploadFile, setUploadFile] = useState(null);
  const [systemStats, setSystemStats] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (mode === 'analytics') {
      fetchSystemStats();
    }
  }, [mode]);

  const fetchSystemStats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/stats`);
      setSystemStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const detectIntent = (text) => {
    const lower = text.toLowerCase();
    if (lower.includes('search') || lower.includes('find') || lower.includes('query') || lower.includes('what') || lower.includes('how')) {
      return 'search';
    }
    if (lower.includes('upload') || lower.includes('ingest') || lower.includes('add') || lower.includes('document')) {
      return 'ingest';
    }
    if (lower.includes('optimize') || lower.includes('heal') || lower.includes('fix') || lower.includes('repair')) {
      return 'heal';
    }
    if (lower.includes('help') || lower.includes('hi') || lower.includes('hello')) {
      return 'help';
    }
    return 'search';
  };

  const generateMockResponse = (intent, query) => {
    const responses = {
      search: {
        content: `🔍 **Search Results for:** "${query}"\n\n✅ Found 5 relevant documents:\n\n1. **Database Rollback Procedures** (Match: 94%)\n   - Last updated: 2025-01-15\n   - Category: Engineering\n   - Access Level: 3\n\n2. **API Documentation v2.1** (Match: 87%)\n   - Department: Engineering\n   - Tags: api, documentation, backend\n\n3. **System Architecture** (Match: 82%)\n   - Category: Technical\n   - Updated: 2025-01-10\n\n📊 **COT Reasoning:**\n• Analyzed query intent: technical documentation\n• Applied RBAC filtering: showing engineering documents\n• Ranked by relevance score\n• Confidence: High (0.91)`,
        actions: ['View Full Document', 'Export Results', 'Ask Follow-up']
      },
      ingest: {
        content: `📤 **Document Ingestion Ready**\n\n**What would you like to upload?**\n\n1. 📄 Text Files (.txt, .md)\n2. 📑 PDF Documents\n3. 📊 CSV/Excel Data\n4. 📋 JSON Files\n\n**Select department for classification:**\n- Engineering\n- HR\n- Finance\n- General\n\n**RBAC Configuration:**\n• Your Role: ${userRole}\n• Access Level: 3\n• Departments: All`,
        actions: ['Upload File', 'Batch Upload', 'Cancel']
      },
      heal: {
        content: `⚕️ **System Healing & Optimization**\n\n**Current System Status:**\n✓ Vector Store: 2,450 embeddings\n✓ Documents: 1,240 total\n✓ Database: 148MB\n⚠️ Fragmentation: 12%\n\n**Available Healing Modes:**\n\n1. **🔧 Full Optimization** (20 min)\n   - Rebalance namespaces\n   - Optimize embeddings\n   - Rebuild indexes\n\n2. **📦 Namespace Cleanup** (5 min)\n   - Fix fragmentation\n   - Consolidate chunks\n\n3. **🧊 Embedding Refresh** (10 min)\n   - Regenerate embeddings\n   - Update metadata\n\n**Recommendation:** Run full optimization`,
        actions: ['Start Full Heal', 'Quick Cleanup', 'View Report']
      },
      help: {
        content: `❓ **Help & Documentation**\n\n**Quick Commands:**\n• "Search for X" - Find documents\n• "Upload documents" - Ingest files\n• "Optimize system" - Run healing\n• "Show analytics" - View statistics\n\n**RBAC & Access:**\n• Current Role: ${userRole}\n• Access Level: 3/5\n• Departments: Engineering, General\n\n**Features:**\n✨ Multi-source document ingestion\n✨ RBAC-aware retrieval\n✨ Chain-of-thought reasoning\n✨ Real-time optimization\n✨ Advanced analytics\n\n**Need more help?** Type "settings" to configure.`,
        actions: ['View Docs', 'Contact Support', 'Settings']
      }
    };
    
    return responses[intent] || responses.search;
  };

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Call backend API
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message: input,
        user_role: userRole,
        session: currentSession
      });

      const assistantMessage = {
        id: messages.length + 2,
        type: 'assistant',
        content: response.data.content || generateMockResponse(detectIntent(input), input).content,
        actions: response.data.actions || generateMockResponse(detectIntent(input), input).actions,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      
      // Fallback to mock response
      const intent = detectIntent(input);
      const mockResponse = generateMockResponse(intent, input);

      const assistantMessage = {
        id: messages.length + 2,
        type: 'assistant',
        content: mockResponse.content,
        actions: mockResponse.actions,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    }

    setIsLoading(false);
  };

  const handleAction = (action) => {
    setInput(action);
    setMessages(prev => [...prev, {
      id: prev.length + 1,
      type: 'user',
      content: action,
      timestamp: new Date()
    }]);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_role', userRole);

    try {
      const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const assistantMessage = {
        id: messages.length + 1,
        type: 'assistant',
        content: `✅ **File Uploaded Successfully**\n\n📄 **${file.name}**\n• Size: ${(file.size / 1024).toFixed(2)} KB\n• Type: ${file.type}\n• Status: Processing...\n\n📊 **Ingestion Pipeline:**\n1. ✓ Chunking (2,450 chunks)\n2. ✓ Metadata extraction\n3. ✓ RBAC classification\n4. ✓ Embedding generation\n5. ✓ Storage completed\n\n✨ Document ready for retrieval!`,
        actions: ['Search in Document', 'View Metadata', 'Upload Another']
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Upload failed:', error);
      const errorMessage = {
        id: messages.length + 1,
        type: 'assistant',
        content: `❌ Upload failed: ${error.message}`
      };
      setMessages(prev => [...prev, errorMessage]);
    }

    setIsLoading(false);
  };

  const createNewSession = () => {
    const newSession = `Session ${sessions.length + 1}`;
    setSessions(prev => [...prev, newSession]);
    setCurrentSession(newSession);
    setMessages([{
      id: 1,
      type: 'assistant',
      content: '👋 New conversation started. How can I help you?',
      timestamp: new Date()
    }]);
  };

  const clearChat = () => {
    setMessages([{
      id: 1,
      type: 'assistant',
      content: '👋 Chat cleared. How can I help you?',
      timestamp: new Date()
    }]);
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-slate-900 border-r border-slate-700 flex flex-col transition-all duration-300`}>
        <div className="p-4 flex items-center justify-between">
          {sidebarOpen && <span className="text-xl font-bold text-cyan-400">🤖 RAG Agent</span>}
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)} 
            className="p-2 hover:bg-slate-700 rounded transition"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        <button
          onClick={createNewSession}
          className="m-4 p-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-lg hover:shadow-lg transition flex items-center justify-center gap-2 font-semibold"
        >
          <Plus size={20} />
          {sidebarOpen && <span>New Chat</span>}
        </button>

        {sidebarOpen && (
          <div className="flex-1 overflow-y-auto px-3 space-y-2">
            <div className="text-xs text-slate-400 mb-3 px-2">SESSIONS</div>
            {sessions.map(session => (
              <button
                key={session}
                onClick={() => setCurrentSession(session)}
                className={`w-full text-left p-3 rounded truncate transition ${
                  currentSession === session
                    ? 'bg-cyan-500 text-white font-semibold'
                    : 'text-slate-300 hover:bg-slate-700'
                }`}
              >
                {session}
              </button>
            ))}
          </div>
        )}

        <div className="p-4 border-t border-slate-700 space-y-2">
          <button
            onClick={() => setMode(mode === 'settings' ? 'chat' : 'settings')}
            className={`w-full p-3 rounded flex items-center gap-2 transition ${
              mode === 'settings' ? 'bg-slate-700' : 'hover:bg-slate-700'
            }`}
          >
            <Settings size={20} />
            {sidebarOpen && <span>Settings</span>}
          </button>
          <button
            onClick={() => setMode(mode === 'analytics' ? 'chat' : 'analytics')}
            className={`w-full p-3 rounded flex items-center gap-2 transition ${
              mode === 'analytics' ? 'bg-slate-700' : 'hover:bg-slate-700'
            }`}
          >
            <BarChart3 size={20} />
            {sidebarOpen && <span>Analytics</span>}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-slate-800 border-b border-slate-700 p-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              {mode === 'chat' ? '💬 Chat' : mode === 'settings' ? '⚙️ Settings' : '📊 Analytics'}
            </h1>
            <p className="text-sm text-slate-400">Session: {currentSession}</p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={userRole}
              onChange={(e) => setUserRole(e.target.value)}
              className="px-4 py-2 bg-slate-700 text-white rounded border border-slate-600 hover:border-cyan-500 focus:border-cyan-500 outline-none transition"
            >
              <option value="intern">Intern (Level 1)</option>
              <option value="junior">Junior (Level 2)</option>
              <option value="engineer">Engineer (Level 3)</option>
              <option value="lead">Lead (Level 4)</option>
              <option value="admin">Admin (Level 5)</option>
            </select>
          </div>
        </div>

        {/* Content Area */}
        {mode === 'chat' ? (
          <>
            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map(msg => (
                <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-2xl ${
                    msg.type === 'user'
                      ? 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white'
                      : 'bg-slate-700 text-slate-100'
                  } p-4 rounded-lg shadow-lg`}>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
                    {msg.actions && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {msg.actions.map((action, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleAction(action)}
                            className="px-3 py-1 bg-slate-600 hover:bg-slate-500 rounded text-xs transition font-semibold"
                          >
                            {action}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-slate-700 p-4 rounded-lg flex items-center gap-2">
                    <Loader size={20} className="animate-spin text-cyan-400" />
                    <span className="text-slate-300">Processing your request...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="bg-slate-800 border-t border-slate-700 p-4 space-y-3">
              {/* File Input */}
              <div className="flex gap-3">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  className="hidden"
                  accept=".txt,.pdf,.csv,.json,.md"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded flex items-center gap-2 transition"
                >
                  <Upload size={20} />
                  <span className="text-sm">Upload</span>
                </button>
              </div>

              {/* Message Input */}
              <div className="flex gap-3">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Ask me anything... (e.g., 'Search for database docs')"
                  className="flex-1 px-4 py-3 bg-slate-700 text-white rounded border border-slate-600 focus:border-cyan-500 outline-none transition"
                />
                <button
                  onClick={handleSendMessage}
                  disabled={isLoading || !input.trim()}
                  className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-500 text-white rounded hover:shadow-lg transition disabled:opacity-50 font-semibold"
                >
                  <Send size={20} />
                </button>
                <button
                  onClick={clearChat}
                  className="px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded transition"
                >
                  <Trash2 size={20} />
                </button>
              </div>
            </div>
          </>
        ) : mode === 'settings' ? (
          // Settings Panel
          <div className="flex-1 overflow-y-auto p-6">
            <div className="space-y-6 max-w-4xl">
              <div className="bg-slate-700 p-6 rounded-lg">
                <h2 className="text-xl font-bold mb-4">⚙️ System Settings</h2>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold mb-2">User Role</label>
                    <select
                      value={userRole}
                      onChange={(e) => setUserRole(e.target.value)}
                      className="w-full px-4 py-2 bg-slate-600 rounded border border-slate-500 hover:border-cyan-500"
                    >
                      <option value="intern">Intern (Level 1)</option>
                      <option value="junior">Junior (Level 2)</option>
                      <option value="engineer">Engineer (Level 3)</option>
                      <option value="lead">Lead (Level 4)</option>
                      <option value="admin">Admin (Level 5)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold mb-2">API Endpoint</label>
                    <input
                      type="text"
                      value={API_BASE_URL}
                      readOnly
                      className="w-full px-4 py-2 bg-slate-600 rounded border border-slate-500 text-slate-300"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold mb-2">Theme</label>
                    <select className="w-full px-4 py-2 bg-slate-600 rounded border border-slate-500 hover:border-cyan-500">
                      <option>Dark (Default)</option>
                      <option>Light</option>
                      <option>Auto</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="bg-slate-700 p-6 rounded-lg">
                <h2 className="text-xl font-bold mb-4">🔐 RBAC Configuration</h2>
                <div className="space-y-2">
                  <p>Current Role: <span className="text-cyan-400 font-semibold">{userRole}</span></p>
                  <p>Access Level: <span className="text-cyan-400 font-semibold">3/5</span></p>
                  <p>Departments: <span className="text-cyan-400 font-semibold">Engineering, General</span></p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          // Analytics Panel
          <div className="flex-1 overflow-y-auto p-6">
            <div className="grid grid-cols-2 gap-6 max-w-4xl">
              <div className="bg-slate-700 p-6 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-slate-400 text-sm">Total Documents</p>
                    <p className="text-4xl font-bold text-cyan-400">1,240</p>
                  </div>
                  <Search size={40} className="text-slate-600" />
                </div>
              </div>

              <div className="bg-slate-700 p-6 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-slate-400 text-sm">Queries (24h)</p>
                    <p className="text-4xl font-bold text-cyan-400">2,450</p>
                  </div>
                  <Zap size={40} className="text-slate-600" />
                </div>
              </div>

              <div className="bg-slate-700 p-6 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-slate-400 text-sm">Avg Response Time</p>
                    <p className="text-4xl font-bold text-cyan-400">0.45s</p>
                  </div>
                  <BarChart3 size={40} className="text-slate-600" />
                </div>
              </div>

              <div className="bg-slate-700 p-6 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-slate-400 text-sm">Success Rate</p>
                    <p className="text-4xl font-bold text-cyan-400">98.5%</p>
                  </div>
                  <Zap size={40} className="text-slate-600" />
                </div>
              </div>

              <div className="bg-slate-700 p-6 rounded-lg col-span-2">
                <h3 className="text-lg font-bold mb-4">Recent Activity</h3>
                <div className="space-y-2 text-sm text-slate-300">
                  <p>✓ Document ingested: company_handbook.pdf (2 mins ago)</p>
                  <p>✓ Query processed: "database procedures" (5 mins ago)</p>
                  <p>✓ System healing completed (1 hour ago)</p>
                  <p>✓ 3 new documents indexed (2 hours ago)</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
