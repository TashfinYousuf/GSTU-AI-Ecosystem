"use client";

import { useState, useRef, useEffect } from "react";
import { 
  Send, Bot, User, Sparkles, Search, Plus, 
  MessageSquare, MoreVertical, Pin, Edit3, Trash2, Share2, 
  ChevronDown, Calendar, CheckSquare, Building2, Rocket, 
  BarChart2, Settings, LogOut, ShieldCheck, Zap
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function Home() {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState("Llama 4 (17B Fast)");
  const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false);
  const [activeMenuChatId, setActiveMenuChatId] = useState<number | null>(null);
  
  // Mock Chat History list
  const [chats, setChats] = useState([
    { id: 1, title: "Political Geography Midterm Prep", pinned: true },
    { id: 2, title: "AI Startup Business Strategy", pinned: false },
    { id: 3, title: "Realism vs Liberalism Theories", pinned: false }
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: userMessage.content,
          model_name: "llama-3.1-70b-versatile",
          chat_history: messages,
        }),
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const dataStr = line.replace("data: ", "");
              if (dataStr === "[DONE]") {
                setIsLoading(false);
                break;
              }
              try {
                const data = JSON.parse(dataStr);
                if (data.text) {
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    const lastIndex = newMessages.length - 1;
                    newMessages[lastIndex].content += data.text;
                    return newMessages;
                  });
                }
              } catch (e) {
                // Ignore
              }
            }
          }
        }
      }
    } catch (error) {
      console.error("Connection Error:", error);
      setIsLoading(false);
    }
  };

  return (
    <main className="flex h-screen bg-[#06090F] text-slate-100 font-sans overflow-hidden">
      
      {/* 🔴 GEMINI / CHATGPT HYBRID SIDEBAR */}
      <aside className="w-75 bg-[#0A0E17] border-r border-slate-800/80 flex-col hidden md:flex z-20">
        
        {/* Sticky Top: Logo & New Chat */}
        <div className="p-4 border-b border-slate-800/60 space-y-3 bg-[#0A0E17]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-linear-to-tr from-teal-500 to-blue-600 flex items-center justify-center shadow-md shadow-teal-500/20">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <span className="font-bold tracking-wide text-white">GSTU Ecosystem</span>
            </div>
          </div>

          <button 
            onClick={() => setMessages([])}
            className="w-full flex items-center justify-between px-4 py-2.5 bg-linear-to-r from-teal-600 to-teal-700 hover:from-teal-500 hover:to-teal-600 text-white font-medium rounded-xl text-sm transition-all shadow-lg shadow-teal-900/30"
          >
            <span className="flex items-center gap-2"><Plus className="w-4 h-4" /> New Chat</span>
            <span className="text-[10px] bg-teal-800/60 px-1.5 py-0.5 rounded text-teal-200">⌘K</span>
          </button>

          {/* Search Chats */}
          <div className="relative">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search conversations..." 
              className="w-full bg-[#121826] border border-slate-800 rounded-lg py-2 pl-9 pr-3 text-xs focus:outline-none focus:border-teal-500/50 transition-all text-slate-300 placeholder:text-slate-500"
            />
          </div>
        </div>

        {/* Scrollable Chat History with Inline Actions */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          <div className="text-[11px] font-semibold text-slate-500 px-3 py-2 uppercase tracking-wider">Recent Chats</div>
          
          {chats.map((chat) => (
            <div 
              key={chat.id}
              className="group relative flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-[#121826] text-sm text-slate-300 hover:text-white cursor-pointer transition-all"
            >
              <div className="flex items-center gap-2.5 truncate">
                <MessageSquare className="w-4 h-4 text-slate-400 shrink-0" />
                <span className="truncate text-xs">{chat.title}</span>
              </div>

              {/* Inline Action Menu (ChatGPT Style on Hover) */}
              <div className="hidden group-hover:flex items-center gap-1 bg-[#121826] pl-2 absolute right-2">
                <button title="Pin" className="p-1 hover:text-teal-400"><Pin className="w-3.5 h-3.5" /></button>
                <button title="Rename" className="p-1 hover:text-blue-400"><Edit3 className="w-3.5 h-3.5" /></button>
                <button title="Delete" className="p-1 hover:text-rose-400"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
            </div>
          ))}
        </div>

        {/* Sticky Bottom: Gemini Style Profile & Account */}
        <div className="p-3 border-t border-slate-800/80 bg-[#0A0E17]">
          <div className="flex items-center justify-between p-2 rounded-xl bg-[#121826] border border-slate-800/60 hover:border-slate-700 transition-all cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-linear-to-tr from-blue-600 to-indigo-600 flex items-center justify-center font-bold text-sm text-white shadow-inner">
                TS
              </div>
              <div>
                <h4 className="text-xs font-semibold text-white">Tashfin Yousuf</h4>
                <p className="text-[10px] text-teal-400 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> Pro Student Workspace
                </p>
              </div>
            </div>
            <Settings className="w-4 h-4 text-slate-400 hover:text-white transition-colors" />
          </div>
        </div>
      </aside>

      {/* 🔴 MAIN HYBRID WORKSPACE */}
      <div className="flex-1 flex flex-col relative bg-[#06090F]">
        
        {/* Top Navbar */}
        <header className="px-6 py-3.5 flex items-center justify-between border-b border-slate-800/60 bg-[#06090F]/80 backdrop-blur-md z-10">
          <div className="flex items-center gap-2">
            <span className="text-xs px-2.5 py-1 bg-teal-500/10 border border-teal-500/20 text-teal-400 rounded-full font-medium flex items-center gap-1.5">
              <Zap className="w-3 h-3" /> FastAPI Headless Engine Active
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button className="px-3.5 py-1.5 bg-linear-to-r from-emerald-600 to-teal-600 hover:opacity-90 text-white text-xs font-semibold rounded-lg shadow-md transition-all">
              🚀 Upgrade Plan
            </button>
          </div>
        </header>

        {/* Chat Feed / Dashboard Hub */}
        <div className="flex-1 overflow-y-auto scroll-smooth">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center p-6 max-w-4xl mx-auto space-y-8 my-auto">
              
              {/* Quick Action Shortcuts */}
              <div className="w-full grid grid-cols-1 sm:grid-cols-3 gap-3">
                <button className="flex items-center gap-3 p-3.5 bg-[#0A0E17] hover:bg-[#121826] border border-slate-800 rounded-xl text-sm font-medium text-slate-300 hover:text-white transition-all text-left group">
                  <Calendar className="w-4 h-4 text-rose-400 group-hover:scale-110 transition-transform" /> Smart Routine
                </button>
                <button className="flex items-center gap-3 p-3.5 bg-[#0A0E17] hover:bg-[#121826] border border-slate-800 rounded-xl text-sm font-medium text-slate-300 hover:text-white transition-all text-left group">
                  <CheckSquare className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" /> Mock Exam
                </button>
                <button className="flex items-center gap-3 p-3.5 bg-[#0A0E17] hover:bg-[#121826] border border-slate-800 rounded-xl text-sm font-medium text-slate-300 hover:text-white transition-all text-left group">
                  <Building2 className="w-4 h-4 text-blue-400 group-hover:scale-110 transition-transform" /> Dept Hub
                </button>
              </div>

              {/* Centered Welcome */}
              <div className="text-center space-y-2">
                <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
                  Good day, Tashfin. What shall we master today? ✨
                </h1>
                <p className="text-slate-400 text-sm">
                  Your intelligent academic and startup command center is online.
                </p>
              </div>

              {/* Productivity & Statistics Dashboard Widget */}
              <div className="w-full grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 bg-[#0A0E17] border border-slate-800 rounded-2xl flex items-center gap-4 shadow-sm">
                  <div className="p-3 bg-teal-500/10 text-teal-400 rounded-xl"><BarChart2 className="w-5 h-5" /></div>
                  <div>
                    <div className="text-xs text-slate-400">Study Streak</div>
                    <div className="text-lg font-bold text-white">14 Days 🔥</div>
                  </div>
                </div>
                <div className="p-4 bg-[#0A0E17] border border-slate-800 rounded-2xl flex items-center gap-4 shadow-sm">
                  <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl"><Rocket className="w-5 h-5" /></div>
                  <div>
                    <div className="text-xs text-slate-400">Current CGPA</div>
                    <div className="text-lg font-bold text-white">2.88 (Target 3.5+)</div>
                  </div>
                </div>
                <div className="p-4 bg-[#0A0E17] border border-slate-800 rounded-2xl flex items-center gap-4 shadow-sm">
                  <div className="p-3 bg-amber-500/10 text-amber-400 rounded-xl"><Zap className="w-5 h-5" /></div>
                  <div>
                    <div className="text-xs text-slate-400">AI Tokens Used</div>
                    <div className="text-lg font-bold text-white">45.2K</div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-4 sm:p-6 space-y-6 max-w-4xl mx-auto mt-4">
              {messages.map((msg, idx) => (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  key={idx}
                  className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                >
                  <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${msg.role === "user" ? "bg-blue-600" : "bg-teal-600"}`}>
                    {msg.role === "user" ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-white" />}
                  </div>
                  <div className={`px-5 py-3.5 rounded-2xl text-[15px] leading-relaxed shadow-sm max-w-[85%] ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white rounded-tr-sm"
                      : "bg-[#0A0E17] border border-slate-800 text-slate-200 rounded-tl-sm"
                  }`}>
                    {msg.content}
                    {isLoading && idx === messages.length - 1 && msg.role === "assistant" && (
                      <span className="inline-block w-1.5 h-4 ml-1 bg-teal-400 animate-pulse align-middle" />
                    )}
                  </div>
                </motion.div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 🔴 MODERN CHAT INPUT BAR WITH EMBEDDED MODEL SELECTOR (ChatGPT/Claude Style) */}
        <div className="p-4 sm:p-6 bg-linear-to-t from-[#06090F] via-[#06090F] to-transparent">
          <div className="max-w-4xl mx-auto bg-[#0A0E17] border border-slate-800 rounded-2xl p-2.5 shadow-2xl focus-within:border-teal-500/50 transition-all">
            
            <textarea
              rows={2}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Ask anything about international relations, research, or startup strategy..."
              className="w-full bg-transparent border-none px-3 py-1.5 focus:outline-none text-slate-100 placeholder:text-slate-500 resize-none text-sm"
            />

            {/* Toolbar Inside Input Box (Model Selector + Send Button) */}
            <div className="flex items-center justify-between px-2 pt-2 border-t border-slate-800/60">
              
              {/* Embedded Model Selector Dropdown */}
              <div className="relative">
                <button 
                  onClick={() => setIsModelDropdownOpen(!isModelDropdownOpen)}
                  className="flex items-center gap-2 px-3 py-1.5 bg-[#121826] hover:bg-slate-800 border border-slate-800 rounded-lg text-xs font-medium text-slate-300 transition-all"
                >
                  <Sparkles className="w-3.5 h-3.5 text-teal-400" />
                  <span>{selectedModel}</span>
                  <ChevronDown className="w-3 h-3 text-slate-500" />
                </button>

                <AnimatePresence>
                  {isModelDropdownOpen && (
                    <motion.div 
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 5 }}
                      className="absolute bottom-full left-0 mb-2 w-56 bg-[#0A0E17] border border-slate-800 rounded-xl shadow-2xl p-1.5 z-30 space-y-1"
                    >
                      <div 
                        onClick={() => { setSelectedModel("Llama 4 (17B Fast)"); setIsModelDropdownOpen(false); }}
                        className="px-3 py-2 text-xs rounded-lg hover:bg-[#121826] cursor-pointer text-slate-300 hover:text-white font-medium"
                      >
                        ⚡ Llama 4 (17B Fast Engine)
                      </div>
                      <div 
                        onClick={() => { setSelectedModel("Groq 70B Advanced"); setIsModelDropdownOpen(false); }}
                        className="px-3 py-2 text-xs rounded-lg hover:bg-[#121826] cursor-pointer text-slate-300 hover:text-white font-medium"
                      >
                        🧠 Groq 70B (Deep Reasoning)
                      </div>
                      <div 
                        onClick={() => { setSelectedModel("Gemini 2.5 Web OS"); setIsModelDropdownOpen(false); }}
                        className="px-3 py-2 text-xs rounded-lg hover:bg-[#121826] cursor-pointer text-slate-300 hover:text-white font-medium"
                      >
                        🌐 Gemini 2.5 (Web Research)
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Send Button */}
              <button
                onClick={sendMessage}
                disabled={!input.trim() || isLoading}
                className={`p-2 rounded-xl transition-all ${
                  input.trim() && !isLoading 
                    ? "bg-teal-600 text-white hover:bg-teal-500 shadow-md shadow-teal-900/30" 
                    : "bg-slate-800 text-slate-500 cursor-not-allowed"
                }`}
              >
                <Send className="w-4 h-4" />
              </button>

            </div>
          </div>
          <div className="text-center mt-2.5 text-[11px] text-slate-500">
            GSTU IR AI Ecosystem v2.0 • Powered by FastAPI & Next.js Headless Architecture
          </div>
        </div>

      </div>
    </main>
  );
}