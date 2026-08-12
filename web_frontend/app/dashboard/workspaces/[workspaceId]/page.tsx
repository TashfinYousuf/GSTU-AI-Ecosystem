"use client";

import { useState, useEffect, useRef, use } from "react";
import rehypeRaw from "rehype-raw";
import { ArrowUp, Paperclip, Database, Globe, Activity, BrainCircuit, Loader2, Lock, Crown, X, FileText, Trash2, Sparkles, Brain, PenTool, CheckSquare, Clock, Network, Bell, Mic, MicOff, Zap, ChevronDown, AlertCircle, Volume2, Copy, Share2, ThumbsUp, ThumbsDown, RefreshCw, TrendingUp, BookOpen, Target } from "lucide-react";
import { createClient } from "../../../utils/supabase/client";
import dynamic from 'next/dynamic';
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

  const [isPremiumModalOpen, setIsPremiumModalOpen] = useState(false);

  const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

  // 🔴 1-argument Smart TTS Function
  const handleTTS = (text: string) => {
      if (window.speechSynthesis.speaking) { window.speechSynthesis.cancel(); return; }
      const cleanText = text.replace(/<[^>]+>/g, '').replace(/[*#_~`]+/g, '');
      
      // Auto-detect Bengali instantly!
      const isBn = /[\u0980-\u09FF]/.test(cleanText);
      
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = isBn ? 'bn-BD' : 'en-US';
      window.speechSynthesis.speak(utterance);
  };

  const handleCopy = (text: string) => {
      const cleanText = text.replace(/<[^>]+>/g, '').replace(/[*#_~`]+/g, '');
      navigator.clipboard.writeText(cleanText);
      alert("Copied to clipboard!");
  };

  const handleShare = () => {
      if (navigator.share) navigator.share({ url: window.location.href, title: "GSTU AI Chat" });
  };


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
        body: JSON.stringify({ workspace_id: workspaceId, message: userMessage.content, model: selectedModel.id }),
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
  const [feedbackModal, setFeedbackModal] = useState<{isOpen: boolean, msgId: string, query: string, response: string}>({isOpen: false, msgId: "", query: "", response: ""});
  const [feedbackReason, setFeedbackReason] = useState("");

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

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Reset textarea height after message send
  useEffect(() => {
    if (input === "" && textareaRef.current) {
      textareaRef.current.style.height = "44px";
    }
  }, [input]);

  const handleInputResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    const maxHeight = 200;
    e.target.style.height = `${Math.min(e.target.scrollHeight, maxHeight)}px`;
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
        endpoint = `${API_HOST}/study/routine`;
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

      {/* =========================================================
         CHAT MESSAGE AREA — PREMIUM CHATGPT / CLAUDE STYLE
      ========================================================= */}
      <div className="flex-1 min-h-0 overflow-y-auto scroll-smooth custom-scrollbar pb-32">
        <div className="mx-auto w-full max-w-4xl px-4 sm:px-6 lg:px-8 py-8 sm:py-10">

          {/* Empty State */}
          {messages.length === 0 && !isTyping && (
            <div className="flex min-h-[55vh] flex-col items-center justify-center text-center animate-in fade-in slide-in-from-bottom-4">
              <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] shadow-xl">
                <Brain className="h-8 w-8 text-indigo-500" />
              </div>
              <h2 className="text-[24px] font-medium tracking-[-0.02em] text-gray-200">
                How can I help you today?
              </h2>
              <p className="mt-3 max-w-md text-[15px] leading-6 text-gray-500">
                Ask anything about your courses, assignments, research, exams or academic tasks.
              </p>
            </div>
          )}

          {/* Messages */}
          <div className="space-y-8 sm:space-y-10">
            {messages.map((msg, i) => {
              const isUser = msg.role === "user";
              const previousUserMessage = [...messages].slice(0, i).reverse().find((m) => m.role === "user");

              return (
                <div key={i} className={`group w-full flex ${isUser ? "justify-end" : "justify-start"}`}>
                  
                  {/* =====================================================
                     USER MESSAGE (Bubble)
                  ====================================================== */}
                  {isUser ? (
                    <div className="flex max-w-[88%] flex-col items-end sm:max-w-[78%]">
                      <div className="rounded-[24px] rounded-br-[8px] bg-[#2f2f2f] px-5 py-3.5 text-[15.5px] leading-7 tracking-[-0.005em] text-gray-100 shadow-sm break-words whitespace-pre-wrap">
                        {msg.content}
                      </div>
                    </div>
                  ) : (

                  /* =====================================================
                     ASSISTANT MESSAGE (Open Canvas)
                  ====================================================== */
                    <div className="w-full max-w-3xl">
                      {/* Assistant Identity */}
                      <div className="mb-2.5 flex items-center gap-2">
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl border border-indigo-500/30 bg-indigo-500/10">
                          <Brain className="h-4 w-4 text-indigo-400" />
                        </div>
                        <span className="text-[13px] font-bold tracking-wide text-gray-400">GSTU Assistant</span>
                      </div>

                      {/* Assistant Response (Markdown) */}
                      <div className="prose prose-invert max-w-none text-[15.5px] leading-[1.78] tracking-[-0.003em] text-gray-200">
                        {msg.content ? (
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            rehypePlugins={[rehypeRaw]}
                            components={{
                              p: ({ node, ...props }) => <p className="mb-5 last:mb-0 text-[15.5px] leading-[1.8] text-gray-200" {...props} />,
                              strong: ({ node, ...props }) => <strong className="font-semibold text-gray-100" {...props} />,
                              em: ({ node, ...props }) => <em className="text-gray-300" {...props} />,
                              h1: ({ node, ...props }) => <h1 className="mb-5 mt-7 text-[24px] font-semibold tracking-[-0.025em] text-gray-100 first:mt-0" {...props} />,
                              h2: ({ node, ...props }) => <h2 className="mb-4 mt-7 text-[20px] font-semibold tracking-[-0.02em] text-gray-100 first:mt-0" {...props} />,
                              h3: ({ node, ...props }) => <h3 className="mb-3 mt-6 text-[17px] font-semibold text-gray-100 first:mt-0" {...props} />,
                              ul: ({ node, ...props }) => <ul className="mb-5 ml-1 list-disc space-y-2 pl-6 text-gray-200" {...props} />,
                              ol: ({ node, ...props }) => <ol className="mb-5 ml-1 list-decimal space-y-2 pl-6 text-gray-200" {...props} />,
                              li: ({ node, ...props }) => <li className="pl-1 leading-[1.75]" {...props} />,
                              blockquote: ({ node, ...props }) => <blockquote className="my-5 border-l-2 border-indigo-500/50 pl-4 italic text-gray-400 bg-indigo-500/5 py-2 pr-4 rounded-r-lg" {...props} />,
                              a: ({ node, ...props }) => <a className="text-indigo-400 underline decoration-indigo-400/30 underline-offset-4 transition-colors hover:text-indigo-300" target="_blank" rel="noopener noreferrer" {...props} />,
                              code: ({ node, inline, className, children, ...props }: any) => {
                                if (inline) return <code className="rounded-md border border-white/10 bg-white/[0.07] px-1.5 py-0.5 font-mono text-[13px] text-indigo-300" {...props}>{children}</code>;
                                return (
                                  <div className="my-5 overflow-hidden rounded-xl border border-white/10 bg-[#0a0a0a]">
                                    <div className="flex h-9 items-center border-b border-white/[0.06] bg-white/[0.025] px-3">
                                      <div className="flex gap-1.5">
                                        <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
                                        <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
                                        <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
                                      </div>
                                    </div>
                                    <pre className="overflow-x-auto p-4 text-[13.5px] leading-6 text-gray-300"><code className={className} {...props}>{children}</code></pre>
                                  </div>
                                );
                              },
                              table: ({ node, ...props }) => <div className="my-5 overflow-x-auto rounded-xl border border-white/10"><table className="w-full border-collapse text-[14px]" {...props} /></div>,
                              th: ({ node, ...props }) => <th className="border-b border-white/10 bg-white/[0.04] px-4 py-3 text-left font-semibold text-gray-200" {...props} />,
                              td: ({ node, ...props }) => <td className="border-b border-white/[0.06] px-4 py-3 text-gray-300" {...props} />,
                              hr: ({ node, ...props }) => <hr className="my-7 border-white/[0.08]" {...props} />,
                            }}
                          >
                            {msg.content}
                          </ReactMarkdown>
                        ) : (
                          /* Streaming placeholder */
                          <div className="flex items-center gap-1.5 py-2">
                            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-500" />
                            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-500 [animation-delay:150ms]" />
                            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-500 [animation-delay:300ms]" />
                          </div>
                        )}
                      </div>

                      {/* =================================================
                         ASSISTANT ACTION BAR (Hover to Reveal)
                      ================================================== */}
                      {msg.content && (
                        <div className="mt-3 flex items-center gap-1 opacity-0 transition-opacity duration-200 group-hover:opacity-100 focus-within:opacity-100">
                          <button onClick={() => handleCopy(msg.content)} className="rounded-lg p-1.5 text-gray-500 transition hover:bg-white/[0.06] hover:text-gray-200" title="Copy">
                            <Copy className="h-4 w-4" />
                          </button>
                          <button onClick={() => handleTTS(msg.content)} className="rounded-lg p-1.5 text-gray-500 transition hover:bg-white/[0.06] hover:text-gray-200" title="Listen">
                            <Volume2 className="h-4 w-4" />
                          </button>
                          <button className="rounded-lg p-1.5 text-gray-500 transition hover:bg-white/[0.06] hover:text-emerald-400" title="Good response">
                            <ThumbsUp className="h-4 w-4" />
                          </button>
                          <button 
                            onClick={() => setFeedbackModal({ 
                              isOpen: true, 
                              msgId: String(i), /* 🔴 FIX: Number কে String-এ কনভার্ট করা হয়েছে */
                              query: previousUserMessage?.content || "Unknown", 
                              response: msg.content 
                            })} 
                            className="rounded-lg p-1.5 text-gray-500 transition hover:bg-white/[0.06] hover:text-rose-400" 
                            title="Bad response"
                          >
                            <ThumbsDown className="h-4 w-4" />
                          </button>
                          
                          <button 
                            onClick={handleShare} /* 🔴 FIX: আর্গুমেন্ট (msg.content) রিমুভ করা হয়েছে */
                            className="rounded-lg p-1.5 text-gray-500 transition hover:bg-white/[0.06] hover:text-gray-200" 
                            title="Share"
                          >
                            <Share2 className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}

            {/* =========================================================
               TYPING INDICATOR (Subtle)
            ========================================================== */}
            {isTyping && messages[messages.length - 1]?.role === "user" && (
              <div className="flex w-full items-start">
                <div className="flex items-center gap-1.5 py-2">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-600 [animation-delay:-0.3s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-600 [animation-delay:-0.15s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-600" />
                </div>
              </div>
            )}
          </div>
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
              ref={textareaRef}
              disabled={isTyping}
              value={input}
              onChange={handleInputResize}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (input.trim()) handleSendMessage(e as any);
                }
              }}
              placeholder={isTyping ? "Generating response..." : "Message GSTU Assistant..."}
              rows={1}
              className="min-h-[44px] max-h-[200px] flex-1 resize-none overflow-y-auto bg-transparent px-2 py-2.5 text-[15.5px] leading-6 text-gray-100 placeholder:text-gray-500 focus:outline-none custom-scrollbar disabled:opacity-50"
              style={{ height: "44px" }}
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
                      { id: "openai/gpt-oss-120b", name: "Fast Engine (OpenAI GPT)", icon: <Zap className="w-4 h-4 text-amber-400" />, isPremium: false },
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

              {feedbackModal.isOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm px-4">
                  <div className="bg-[#171717] border border-white/10 p-6 rounded-2xl max-w-md w-full shadow-2xl">
                    <h3 className="text-lg font-bold text-white mb-2">🧠 Help GSTU AI Learn</h3>
                    <p className="text-xs text-gray-400 mb-4">Please explain the reason you dislike this response.</p>
                    
                    <textarea 
                      value={feedbackReason} 
                      onChange={e => setFeedbackReason(e.target.value)}
                      className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl p-3 text-sm text-gray-300 focus:border-indigo-500 outline-none min-h-[100px] mb-4"
                      placeholder="e.g., The geopolitical facts were outdated..."
                    />
                    
                    <div className="flex justify-end gap-3">
                      <button onClick={() => setFeedbackModal({isOpen: false, msgId: "", query: "", response: ""})} className="text-xs font-bold text-gray-400 hover:text-white px-4">Cancel</button>
                      <button 
                        onClick={async () => {
                          try {
                            await fetchAPI("/logger/feedback", {
                              method: "POST",
                              body: JSON.stringify({ query: feedbackModal.query, response: feedbackModal.response, reason: feedbackReason })
                            });
                            alert("✅ Feedback securely logged! The GSTU AI routing engine will adjust future responses.");
                            setFeedbackModal({isOpen: false, msgId: "", query: "", response: ""});
                          } catch (err: any) {
                            alert(err.message || "Failed to submit feedback.");
                          }
                        }}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-5 py-2.5 rounded-lg transition-colors"
                      >
                        Submit Feedback to Core
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </form>
        </div>
        <p className="mt-3 text-center text-[12px] text-gray-500 font-medium tracking-wide">
            GSTU Assistant can make mistakes. Verify important academic information.
          </p>
      </div>
    </div>
  );
}