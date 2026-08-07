"use client";

import { useState, useEffect, useRef, use } from "react";
import { ArrowUp, Paperclip, Database, Globe, Activity, BrainCircuit, Loader2, FileText, X, Trash2, Lock, Sparkles, Brain, PenTool, CheckSquare, Clock, Network, Bell, Mic, MicOff, Zap, ChevronDown, TrendingUp, BookOpen, Target } from "lucide-react";
import { createClient } from "../../../utils/supabase/client";
import dynamic from 'next/dynamic';
import { use as usePromise } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { fetchAPI } from "../../../utils/api";

const API_HOST = "http://127.0.0.1:8000/api/v1"; // 🔴 standardized — file previously
// mixed "http://localhost:8000" and "http://127.0.0.1:8000" across different
// functions in the same component. Browsers treat these as different origins
// for CORS purposes, which was a likely contributor to intermittent "Failed to
// fetch" errors. Everything below now uses one constant.

export default function WorkspaceChatPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = use(params);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [workspaceName, setWorkspaceName] = useState("...");
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [messages, setMessages] = useState<{ id: string, role: string, content: string }[]>([]);

  const [documents, setDocuments] = useState<{ id: string, filename: string }[]>([]);
  const [isKbOpen, setIsKbOpen] = useState(false);
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);

  const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 🔴 FIX: was duplicated as two separate, identical useEffects. One is enough.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // 🔴 THE BIG FIX: this component previously had THREE separate, competing
  // data-loading mechanisms all firing on mount/workspaceId change:
  //   1. loadWorkspaceData() via fetchAPI("/chat/workspaces") + fetchAPI("/chat/history/:id")
  //   2. loadHistory() via fetchAPI("/chat/history/:id") — pure duplicate of #1's second call
  //   3. fetchWorkspaceData() via raw fetch to "http://localhost:8000/api/v1/workspaces"
  //      (WRONG path — chat.py only exposes /api/v1/chat/workspaces, not /api/v1/workspaces)
  //      which also read `currentWs.name` instead of `currentWs.title`, and seeded
  //      the empty state with role "ai" instead of "assistant".
  // All three raced each other and could each overwrite `messages` with a
  // different shape. Consolidated into one effect below.
  useEffect(() => {
    if (!workspaceId) return;
    let isMounted = true;

    async function loadWorkspaceData() {
      try {
        const wsRes = await fetchAPI("/chat/workspaces");
        if (wsRes?.data && isMounted) {
          const currentWs = wsRes.data.find((ws: any) => ws.id === workspaceId);
          if (currentWs) setWorkspaceName(currentWs.title || "Academic Workspace");
        }

        const histRes = await fetchAPI(`/chat/history/${workspaceId}`);
        if (histRes?.data && isMounted) {
          if (histRes.data.length > 0) {
            setMessages(histRes.data.map((m: any) => ({ id: m.id, role: m.role, content: m.content })));
          } else {
            setMessages([]); // let the JSX empty-state placeholder handle this, not a fake message
          }
        }

        const supabase = createClient();
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token && isMounted) {
          const docRes = await fetch(`${API_HOST}/documents/list/${workspaceId}`, {
            headers: { "Authorization": `Bearer ${session.access_token}` }
          });
          if (docRes.ok) setDocuments(await docRes.json());
        }
      } catch (err) {
        console.error("Failed to load workspace data:", err);
      }
    }

    loadWorkspaceData();
    return () => { isMounted = false; };
  }, [workspaceId]);

  const fetchWorkspaceData = async () => {
    // Kept as a manually-callable refresh (used after upload/delete) but now
    // reuses the same logic path/host as the effect above instead of its own
    // divergent, wrong-endpoint implementation.
    if (!workspaceId) return;
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const docRes = await fetch(`${API_HOST}/documents/list/${workspaceId}`, {
        headers: { "Authorization": `Bearer ${session.access_token}` }
      });
      if (docRes.ok) setDocuments(await docRes.json());
    } catch (error) {
      console.error("Failed to refresh workspace data", error);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) {
      alert("No active session! Please log in.");
      return;
    }

    const userMessage = { id: crypto.randomUUID(), role: "user", content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);

    const assistantId = crypto.randomUUID();
    setMessages(prev => [...prev, { id: assistantId, role: "assistant", content: "" }]);

    try {
      const res = await fetch(`${API_HOST}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`
        },
        body: JSON.stringify({ workspace_id: workspaceId, message: userMessage.content }),
      });

      if (!res.ok || !res.body) throw new Error("Stream blocked (404/401) or failed to start");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        accumulated += decoder.decode(value, { stream: true });
        setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: accumulated } : m));
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: "⚠️ Failed to stream response. Please try again." } : m));
    } finally {
      setIsTyping(false);
    }
  };

  const [selectedModel, setSelectedModel] = useState<{ id: string; name: string; icon: React.ReactNode; isPremium: boolean }>({
    id: "gemini-2.5-flash",
    name: "Web Search (Gemini 2.5)",
    icon: <Globe className="w-4 h-4 text-emerald-400" />,
    isPremium: false
  });
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const [isMentorMode, setIsMentorMode] = useState(false);

  const [graphData, setGraphData] = useState<{ nodes: any[], links: any[] } | null>(null);
  const [isGraphOpen, setIsGraphOpen] = useState(false);
  const [graphTopic, setGraphTopic] = useState("");

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.type !== "application/pdf") { alert("Only PDF files supported."); return; }

    setIsTyping(true);
    const uploadingMsgId = crypto.randomUUID();
    // 🔴 FIX: role was "ai" — standardized to "assistant" to match backend + rest of UI
    setMessages(prev => [...prev, { id: uploadingMsgId, role: "assistant", content: `Uploading **${file.name}**...` }]);

    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) { setIsTyping(false); return; }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("workspace_id", workspaceId);

    try {
      const res = await fetch(`${API_HOST}/documents/upload`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${session.access_token}` },
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(prev => prev.map(msg => msg.id === uploadingMsgId ? { ...msg, content: `✅ **Success!** ${data.message}.` } : msg));
        fetchWorkspaceData();
      } else {
        throw new Error("Upload failed");
      }
    } catch (error) {
      setMessages(prev => prev.map(msg => msg.id === uploadingMsgId ? { ...msg, content: `❌ **Error:** Failed to process document.` } : msg));
    } finally {
      setIsTyping(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDeleteDoc = async (docId: string) => {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      try {
        const res = await fetch(`${API_HOST}/documents/delete/${workspaceId}/${docId}`, {
          method: "DELETE",
          headers: { "Authorization": `Bearer ${session.access_token}` }
        });
        if (res.ok) fetchWorkspaceData();
      } catch (error) { console.error("Failed to delete document", error); }
    }
  };

  const handleCopilotAction = async (actionType: string) => {
    setIsCopilotOpen(false);

    const topic = prompt(`Enter the topic for your ${actionType}:`);
    if (!topic) return;

    setIsTyping(true);
    const actionMsgId = crypto.randomUUID();
    setMessages(prev => [...prev, { id: crypto.randomUUID(), role: "user", content: `✨ Generate a ${actionType} on: ${topic}` }]);
    // 🔴 FIX: role was "ai" — standardized to "assistant"
    setMessages(prev => [...prev, { id: actionMsgId, role: "assistant", content: `Working on your ${actionType}...` }]);

    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) { setIsTyping(false); return; }

    try {
      let endpoint = `${API_HOST}/academic/generate`;
      let bodyData: any = { workspace_id: workspaceId, task_type: actionType.toLowerCase(), topic };

      if (actionType === "Concept Map") {
        endpoint = `${API_HOST}/knowledge/generate-graph`;
        bodyData = { workspace_id: workspaceId, topic };
      } else if (actionType === "Mock Exam") {
        endpoint = `${API_HOST}/academic/mock-exam`;
        bodyData = { workspace_id: workspaceId, topic, difficulty: "University Level" };
      } else if (actionType === "Smart Routine") {
        endpoint = `${API_HOST}/academic/routine`;
        bodyData = { workspace_id: workspaceId, study_hours: 4, focus_areas: [topic] };
      } else if (actionType === "Formal Notice") {
        endpoint = `${API_HOST}/academic/notice`;
        bodyData = { raw_text: topic };
      }

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${session.access_token}` },
        body: JSON.stringify(bodyData)
      });

      if (res.ok) {
        const data = await res.json();

        if (actionType === "Concept Map") {
          const rawNodes = Array.isArray(data.graph?.nodes) ? data.graph.nodes : [];
          const rawLinks = Array.isArray(data.graph?.edges) ? data.graph.edges : (Array.isArray(data.graph?.links) ? data.graph.links : []);
          const validNodeIds = new Set(rawNodes.map((n: any) => n.id));
          const safeLinks = rawLinks.filter((l: any) => validNodeIds.has(l.source) && validNodeIds.has(l.target));
          setGraphData({ nodes: rawNodes, links: safeLinks });

          setGraphTopic(topic);
          setIsGraphOpen(true);
          setMessages(prev => prev.map(msg => msg.id === actionMsgId ? { ...msg, content: `✅ **Concept Map Generated!** I have created an interactive Knowledge Graph for "${topic}". Check the visualizer.` } : msg));
        } else {
          setMessages(prev => prev.map(msg => msg.id === actionMsgId ? { ...msg, content: data.result } : msg));
        }
      } else {
        throw new Error("Copilot task failed");
      }
    } catch (error) {
      setMessages(prev => prev.map(msg => msg.id === actionMsgId ? { ...msg, content: `❌ Copilot failed to generate ${actionType}.` } : msg));
    } finally {
      setIsTyping(false);
    }
  };

  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event: any) => {
        const transcript = Array.from(event.results)
          .map((result: any) => result[0].transcript)
          .join("");
        setInput(transcript);
      };

      recognitionRef.current.onerror = (event: any) => {
        console.error("Speech recognition error", event.error);
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
  }, []);

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      recognitionRef.current?.start();
      setIsListening(true);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#212121] font-sans text-gray-200 overflow-hidden w-full">

      {/* 🔴 FIX: header was duplicated — an outer h-16 flex container wrapped
          an IDENTICAL inner h-16 w-full container that held only the workspace
          name, while the Mentor/Knowledge Base buttons sat as a sibling of that
          inner div. Because the inner div was `w-full`, it consumed the entire
          flex row and pushed/wrapped the buttons out of place. Now it's a
          single header with the name on the left and actions on the right. */}
      <div className="shrink-0 w-full h-16 bg-[#212121] border-b border-white/5 flex items-center justify-between px-6 z-20">
        <div className="font-medium text-gray-200 flex items-center gap-2">
          {workspaceName} <span className="px-2 py-0.5 bg-indigo-500/10 text-indigo-400 text-[10px] uppercase rounded-full border border-indigo-500/20">Academic Mode</span>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => setIsMentorMode(!isMentorMode)} className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-bold transition-all ${isMentorMode ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/30' : 'bg-[#2f2f2f] text-orange-400 border border-orange-500/20'}`}>
            <Brain className="w-4 h-4" /> {isMentorMode ? "Mentor Active" : "Ask Mentor"}
          </button>
          <button onClick={() => setIsKbOpen(!isKbOpen)} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${isKbOpen ? 'bg-indigo-500/20 text-indigo-400' : 'bg-[#2f2f2f] text-gray-400 hover:text-gray-200'}`}>
            <Database className="w-4 h-4" /> Knowledge Base <span className="bg-white/10 px-1.5 py-0.5 rounded text-xs ml-1">{documents.length}</span>
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto w-full px-4 pt-8 pb-6 custom-scrollbar">
        <div className="max-w-3xl mx-auto w-full flex flex-col space-y-8 min-h-full justify-end">

          {messages.length === 0 && !isTyping && (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 pb-20">
              <Brain className="w-12 h-12 mb-4 opacity-50 text-gray-400" />
              <p className="text-[15px] font-medium text-gray-400">How can I help you with your academic tasks today?</p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className="flex flex-col w-full group">
              <span className="text-[13px] font-semibold text-gray-400 mb-2 ml-1">{msg.role === "user" ? "You" : "GSTU Assistant"}</span>
              <div className={`text-[16px] leading-[1.75] tracking-wide wrap-break-word ${msg.role === "user" ? "bg-[#2f2f2f] px-5 py-3.5 rounded-3xl w-fit max-w-[85%] text-gray-100 shadow-sm" : "text-gray-200 px-2 w-full"}`}>
                {msg.role === "user" ? msg.content : (
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                    p: ({ node, ...props }) => <p className="mb-4 last:mb-0" {...props} />,
                    strong: ({ node, ...props }) => <strong className="font-semibold text-white" {...props} />,
                    ul: ({ node, ...props }) => <ul className="list-disc pl-6 mb-4 space-y-1.5 marker:text-gray-400" {...props} />,
                    ol: ({ node, ...props }) => <ol className="list-decimal pl-6 mb-4 space-y-1.5 marker:text-gray-400" {...props} />,
                    code: ({ node, inline, ...props }: any) => inline ? <code className="bg-white/10 text-indigo-300 px-1.5 py-0.5 rounded-md text-[14px] font-mono" {...props} /> : <div className="bg-[#1e1e1e] border border-white/10 rounded-xl my-5 overflow-hidden"><pre className="p-4 overflow-x-auto text-[14.5px] text-gray-300 font-mono"><code {...props} /></pre></div>
                  }}>
                    {msg.content}
                  </ReactMarkdown>
                )}
              </div>
            </div>
          ))}

          {isTyping && messages[messages.length - 1]?.content === "" && (
            <div className="flex flex-col w-full">
              <span className="text-[13px] font-semibold text-gray-400 mb-2 ml-1">GSTU Assistant</span>
              <div className="flex items-center gap-1.5 px-4 py-2 mt-1">
                <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
                <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="shrink-0 w-full bg-[#212121] pt-2 pb-6 px-4 z-20">
        <div className="max-w-3xl mx-auto w-full">
          <form onSubmit={handleSendMessage} className="flex items-end bg-[#2f2f2f] rounded-3xl border border-white/10 shadow-lg focus-within:border-indigo-500/50 focus-within:ring-1 focus-within:ring-indigo-500/20 transition-all p-1.5">

            <input type="file" ref={fileInputRef} onChange={handleFileSelect} className="hidden" />

            <div className="flex items-center gap-1 mb-1 ml-1 shrink-0">
              <button type="button" onClick={() => fileInputRef.current?.click()} className="p-2 text-gray-400 hover:text-white transition-colors rounded-full hover:bg-white/5">
                <Paperclip className="w-5 h-5" />
              </button>
              <button type="button" onClick={toggleListening} className={`p-2 transition-colors rounded-full hover:bg-white/5 ${isListening ? 'text-red-400 animate-pulse bg-red-500/10' : 'text-gray-400 hover:text-white'}`}>
                {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>
            </div>

            <textarea
              disabled={isTyping}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(e as any); } }}
              placeholder={isTyping ? "Generating response..." : "Message GSTU Assistant..."}
              className={`flex-1 bg-transparent py-2.5 px-3 text-gray-100 placeholder-gray-500 focus:outline-none resize-none max-h-40 min-h-11 text-[15.5px] leading-relaxed self-center ${isTyping ? "cursor-not-allowed" : ""}`}
              rows={1}
            />

            <div className="flex items-center gap-2 mb-1 mr-1 shrink-0 relative">
              <button
                type="button"
                onClick={() => setIsModelMenuOpen(!isModelMenuOpen)}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-black/40 hover:bg-black/60 border border-white/10 text-[12px] font-bold text-gray-200 transition-colors shadow-inner"
              >
                {selectedModel.icon}
                <span className="max-w-30 truncate">{selectedModel.name}</span>
                <ChevronDown className="w-3.5 h-3.5 opacity-70" />
              </button>

              {isModelMenuOpen && (
                <div className="absolute right-12 bottom-full mb-3 w-72 bg-[#171717] border border-white/10 rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col max-h-87.5">
                  <div className="px-4 py-3 border-b border-white/5 bg-[#121212]">
                    <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Select AI Engine</span>
                  </div>

                  <div className="overflow-y-auto custom-scrollbar flex-1 py-2">
                    {[
                      { id: "llama-4-scout-17b-16e-instruct", name: "Fast Engine (Llama 4)", icon: <Zap className="w-4 h-4 text-amber-400" />, isPremium: false },
                      { id: "local-gpt4all", name: "Offline Mode (GPT4All)", icon: <Database className="w-4 h-4 text-gray-400" />, isPremium: false },
                      { id: "gemini-2.5-flash", name: "Web Search (Gemini 2.5)", icon: <Globe className="w-4 h-4 text-emerald-400" />, isPremium: false },
                      { id: "deepseek-r1:free", name: "DeepSeek R1 (Free)", icon: <Activity className="w-4 h-4 text-cyan-400" />, isPremium: false },
                      { id: "openai/gpt-4o-mini", name: "GPT-4o Mini (Fast)", icon: <Sparkles className="w-4 h-4 text-rose-400" />, isPremium: false },
                      { id: "llama-3.3-70b-versatile", name: "Deep Logic (Llama 3 70B)", icon: <BrainCircuit className="w-4 h-4 text-blue-400" />, isPremium: true },
                      { id: "qwen/qwen-2.5-72b-instruct", name: "Qwen Core (Qwen 72B)", icon: <BrainCircuit className="w-4 h-4 text-indigo-400" />, isPremium: true },
                      { id: "gemini-2.5-pro", name: "Adv. Analysis (Gemini Pro)", icon: <Globe className="w-4 h-4 text-purple-400" />, isPremium: true },
                      { id: "openai/gpt-4o-2024-08-06", name: "GPT-4o (OpenAI Premium)", icon: <Sparkles className="w-4 h-4 text-rose-500" />, isPremium: true },
                      { id: "anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet", icon: <Brain className="w-4 h-4 text-orange-400" />, isPremium: true },
                    ].map((model) => (
                      <button
                        key={model.id}
                        type="button"
                        onClick={async () => {
                          if (model.isPremium) {
                            const supabase = createClient();
                            const { data: { session } } = await supabase.auth.getSession();
                            const role = session?.user?.user_metadata?.role?.toLowerCase() || "guest";
                            const tier = session?.user?.user_metadata?.tier || "free";
                            const createdAt = session?.user?.created_at;

                            if (role === "guest" || (role !== "admin" && tier !== "pro_scholar")) {
                              alert("🔒 Security Alert: Premium AI Model Locked. Guest and Free accounts cannot access this engine.");
                              return;
                            }

                            const trialEnd = new Date(new Date(createdAt || Date.now()).getTime() + 30 * 24 * 60 * 60 * 1000);
                            const isTrialActive = trialEnd > new Date();

                            if (tier !== "pro_scholar" && session?.user?.user_metadata?.role !== "admin" && !isTrialActive) {
                              alert("🔒 Premium Model Locked. Your 1-Month trial has expired. Upgrade to Pro Scholar in Settings.");
                              return;
                            }
                          }
                          setSelectedModel(model);
                          setIsModelMenuOpen(false);
                        }}
                        className={`w-full flex items-center justify-between px-4 py-3 text-[13px] font-medium transition-colors ${model.isPremium ? "hover:bg-indigo-500/10" : "hover:bg-white/5"} ${selectedModel.id === model.id ? "bg-white/10 text-white" : "text-gray-300"}`}
                      >
                        <div className="flex items-center gap-3">
                          {model.icon}
                          {model.name}
                        </div>
                        {model.isPremium && <Lock className="w-3.5 h-3.5 text-indigo-500 opacity-60" />}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={!input.trim() || isTyping}
                className="p-3 bg-white text-black hover:bg-gray-200 disabled:bg-[#404040] disabled:text-gray-600 rounded-xl transition-all shadow-md"
              >
                {isTyping ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowUp className="w-4 h-4" />}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}