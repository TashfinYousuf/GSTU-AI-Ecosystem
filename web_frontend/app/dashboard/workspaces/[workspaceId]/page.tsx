"use client";

import { useState, useEffect, useRef, use } from "react";
import { ArrowUp, Paperclip, Database, FileText, X, Trash2, Sparkles, Brain, PenTool, CheckSquare, Clock, Network, Bell, Mic, MicOff, Zap, ChevronDown, TrendingUp, BookOpen, Target } from "lucide-react";
import { createClient } from "../../../utils/supabase/client";
import dynamic from 'next/dynamic';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// 🔴 Dynamic import for Graph library (to avoid Next.js SSR window errors)
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

export default function WorkspaceChatPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = use(params);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [workspaceName, setWorkspaceName] = useState("...");
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [messages, setMessages] = useState<{id: string, role: string, content: string}[]>([]);
  
  const [documents, setDocuments] = useState<{id: string, filename: string}[]>([]);
  const [isKbOpen, setIsKbOpen] = useState(false);
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);

  const [selectedModel, setSelectedModel] = useState("gemini");
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);

  // 🔴 State for Mentor Mode
  const [isMentorMode, setIsMentorMode] = useState(false);

  // 🔴 GraphRAG States
  const [graphData, setGraphData] = useState<{nodes: any[], links: any[]} | null>(null);
  const [isGraphOpen, setIsGraphOpen] = useState(false);
  const [graphTopic, setGraphTopic] = useState("");

  const fetchWorkspaceData = async () => {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    
    if (session?.access_token) {
      try {
        const wsRes = await fetch("http://localhost:8000/api/v1/workspaces", { headers: { "Authorization": `Bearer ${session.access_token}` } });
        if (wsRes.ok) {
          const data = await wsRes.json();
          const currentWs = data.find((ws: any) => ws.id === workspaceId);
          if (currentWs) setWorkspaceName(currentWs.name);
        }

        const histRes = await fetch(`http://localhost:8000/api/v1/chat/history/${workspaceId}`, { headers: { "Authorization": `Bearer ${session.access_token}` } });
        if (histRes.ok) {
          const historyData = await histRes.json();
          if (historyData.length > 0) setMessages(historyData);
          else setMessages([{ id: "1", role: "ai", content: "How can I help you with your academic tasks today?" }]);
        }

        const docRes = await fetch(`http://localhost:8000/api/v1/documents/list/${workspaceId}`, { headers: { "Authorization": `Bearer ${session.access_token}` } });
        if (docRes.ok) setDocuments(await docRes.json());
      } catch (error) {
        console.error("Failed to load workspace data", error);
      }
    }
  };

  useEffect(() => { fetchWorkspaceData(); }, [workspaceId]);

  // --- File Upload & Delete ---
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.type !== "application/pdf") { alert("Only PDF files supported."); return; }

    setIsTyping(true);
    const uploadingMsgId = Date.now().toString();
    setMessages(prev => [...prev, { id: uploadingMsgId, role: "ai", content: `Uploading **${file.name}**...` }]);

    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) return;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("workspace_id", workspaceId);

    try {
      const res = await fetch("http://localhost:8000/api/v1/documents/upload", {
        method: "POST",
        headers: { "Authorization": `Bearer ${session.access_token}` },
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(prev => prev.map(msg => msg.id === uploadingMsgId ? { ...msg, content: `✅ **Success!** ${data.message}.` } : msg));
        fetchWorkspaceData(); 
      } else throw new Error("Upload failed");
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
        const res = await fetch(`http://localhost:8000/api/v1/documents/delete/${workspaceId}/${docId}`, {
          method: "DELETE",
          headers: { "Authorization": `Bearer ${session.access_token}` }
        });
        if (res.ok) fetchWorkspaceData();
      } catch (error) { console.error("Failed to delete document", error); }
    }
  };

  // --- 🔴 AI Copilot & GraphRAG Trigger ---
  const handleCopilotAction = async (actionType: string) => {
    setIsCopilotOpen(false);
    
    const topic = prompt(`Enter the topic for your ${actionType}:`);
    if (!topic) return;

    setIsTyping(true);
    const actionMsgId = Date.now().toString();
    setMessages(prev => [...prev, { id: Date.now().toString() + 'u', role: "user", content: `✨ Generate a ${actionType} on: ${topic}` }]);
    setMessages(prev => [...prev, { id: actionMsgId, role: "ai", content: `Working on your ${actionType}...` }]);

    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) return;

    try {
      let endpoint = "http://localhost:8000/api/v1/academic/generate";
      let bodyData: any = { workspace_id: workspaceId, task_type: actionType.toLowerCase(), topic };

      // 🔴 AI Notice Engine & Other Copilot Actions
      if (actionType === "Concept Map") {
        endpoint = "http://localhost:8000/api/v1/knowledge/generate-graph";
        bodyData = { workspace_id: workspaceId, topic };
      } else if (actionType === "Mock Exam") {
        endpoint = "http://localhost:8000/api/v1/academic/mock-exam";
        bodyData = { workspace_id: workspaceId, topic, difficulty: "University Level" };
      } else if (actionType === "Smart Routine") {
        endpoint = "http://localhost:8000/api/v1/academic/routine";
        bodyData = { workspace_id: workspaceId, study_hours: 4, focus_areas: [topic] };
      } else if (actionType === "Formal Notice") {
        // 🔴 Notice Engine Logic
        endpoint = "http://localhost:8000/api/v1/academic/notice";
        bodyData = { raw_text: topic }; // এখানে topic মানে হলো ইউজারের দেওয়া Raw Instruction
      }

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${session.access_token}` },
        body: JSON.stringify(bodyData)
      });

      if (res.ok) {
        const data = await res.json();
        
        // 🔴 Handle GraphRAG Visualization
        if (actionType === "Concept Map") {
          // ১. নিশ্চিত করা যে nodes এবং links অবশ্যই একটি Array হবে (undefined নয়)
          const rawNodes = Array.isArray(data.graph?.nodes) ? data.graph.nodes : [];
          const rawLinks = Array.isArray(data.graph?.edges) ? data.graph.edges : (Array.isArray(data.graph?.links) ? data.graph.links : []);

          // ২. ভ্যালিডেশন: কোনো link যেন ভুয়া/অস্তিত্বহীন node-কে পয়েন্ট না করে (এতেই মূলত গ্রাফ ক্র্যাশ করে)
          // 🔴 Added (n: any) and (l: any) to satisfy TypeScript
          const validNodeIds = new Set(rawNodes.map((n: any) => n.id));
          const safeLinks = rawLinks.filter((l: any) => validNodeIds.has(l.source) && validNodeIds.has(l.target));
          setGraphData({
            nodes: rawNodes,
            links: safeLinks 
          });
          
          setGraphTopic(topic);
          setIsGraphOpen(true); 
          setMessages(prev => prev.map(msg => msg.id === actionMsgId ? { ...msg, content: `✅ **Concept Map Generated!** I have created an interactive Knowledge Graph for "${topic}". Check the visualizer.` } : msg));
        } else {
          setMessages(prev => prev.map(msg => msg.id === actionMsgId ? { ...msg, content: data.result } : msg));
        }
      } else throw new Error("Copilot task failed");
    } catch (error) {
      setMessages(prev => prev.map(msg => msg.id === actionMsgId ? { ...msg, content: `❌ Copilot failed to generate ${actionType}.` } : msg));
    } finally {
      setIsTyping(false);
    }
  };

  // --- Normal Chat Stream ---
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userText = input;
    const newUserMsg = { id: Date.now().toString(), role: "user", content: userText };
    setMessages(prev => [...prev, newUserMsg]);
    setInput("");
    setIsTyping(true);

    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) return;

    // 🔴 Dynamic Endpoint Routing (Mentor Mode vs Regular Chat)
    const endpoint = isMentorMode 
      ? "http://localhost:8000/api/v1/mentor/chat" 
      : "http://localhost:8000/api/v1/chat/stream";

    // 🔴 Smart Payload Injection
    const bodyPayload = isMentorMode
      ? { 
          message: userText, 
          workspace_id: workspaceId,
          student_context: { 
            major: "International Relations", 
            semester: "2.1", 
            current_cgpa: 2.88, 
            mood: "determined" 
          } 
        }
      : { message: userText, workspace_id: workspaceId };

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${session.access_token}` },
        body: JSON.stringify(bodyPayload)
      });
      
      if (!res.ok) throw new Error("Failed");
      
      const reader = res.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      let done = false;
      const aiMsgId = (Date.now() + 1).toString();
      setMessages(prev => [...prev, { id: aiMsgId, role: "ai", content: "" }]);
      setIsTyping(false);

      while (!done) {
        const { value, done: readerDone } = await reader!.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n").filter(line => line.trim() !== "");
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const text = line.replace("data: ", "");
              if (text === "[DONE]") { done = true; break; }
              setMessages(prev => prev.map(msg => msg.id === aiMsgId ? { ...msg, content: msg.content + text + " " } : msg));
            }
          }
        }
      }
    } catch (error) { setIsTyping(false); }
  };

  // 🔴 Voice Input States
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  // ব্রাউজারে স্পিচ রিকগনিশন ইনিশিয়ালাইজ করা
  useEffect(() => {
    if (typeof window !== "undefined" && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US'; // বাংলা চাইলে 'bn-BD' দিতে পারেন

      recognitionRef.current.onresult = (event: any) => {
        const transcript = Array.from(event.results)
          .map((result: any) => result[0].transcript)
          .join("");
        setInput(transcript); // ইউজারের কথা রিয়েল-টাইমে ইনপুট বক্সে লেখা হবে
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
    // 🔴 1. ROOT LOCK: h-screen overflow-hidden locks the entire page. 
    <div className="flex flex-col h-screen bg-[#212121] font-sans text-gray-200 overflow-hidden w-full">
      
      {/* 🔴 2. STICKY HEADER (Shrink-0 prevents it from squishing) */}
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

      {/* 🔴 3. INDEPENDENT SCROLLABLE CHAT AREA (flex-1 takes remaining space) */}
      <div className="flex-1 overflow-y-auto w-full px-4 pt-8 pb-6 custom-scrollbar">
        <div className="max-w-3xl mx-auto w-full flex flex-col space-y-8 min-h-full justify-end">
          
          {/* Empty State */}
          {messages.length === 0 && (
             <div className="flex flex-col items-center justify-center h-full text-gray-500 pb-20">
                <Brain className="w-12 h-12 mb-4 opacity-50" />
                <p className="text-[15px] font-medium">How can I help you with your academic tasks today?</p>
             </div>
          )}

          {/* Messages Map */}
          {messages.map((msg) => (
            <div key={msg.id} className="flex flex-col w-full group">
              <span className="text-[13px] font-semibold text-gray-400 mb-2 ml-1">{msg.role === "user" ? "You" : workspaceName}</span>
              <div className={`text-[16px] leading-[1.75] tracking-wide break-words ${msg.role === "user" ? "bg-[#2f2f2f] px-5 py-3.5 rounded-3xl w-fit max-w-[85%] text-gray-100 shadow-sm" : "text-gray-200 px-2 w-full"}`}>
                 {msg.role === "user" ? msg.content : (
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                      p: ({node, ...props}) => <p className="mb-4 last:mb-0" {...props} />,
                      strong: ({node, ...props}) => <strong className="font-semibold text-white" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc pl-6 mb-4 space-y-1.5 marker:text-gray-500" {...props} />,
                      ol: ({node, ...props}) => <ol className="list-decimal pl-6 mb-4 space-y-1.5 marker:text-gray-500" {...props} />,
                      code: ({node, inline, ...props}: any) => inline ? <code className="bg-white/10 text-indigo-300 px-1.5 py-0.5 rounded-md text-[14px] font-mono" {...props} /> : <div className="bg-[#1e1e1e] border border-white/10 rounded-xl my-5 overflow-hidden"><pre className="p-4 overflow-x-auto text-[14.5px] text-gray-300 font-mono"><code {...props} /></pre></div>
                    }}>
                      {msg.content}
                    </ReactMarkdown>
                 )}
              </div>
            </div>
          ))}
          {isTyping && (
             <div className="text-[15px] text-gray-400 px-2 animate-pulse flex items-center gap-2 mt-4">
                <Sparkles className="w-4 h-4 text-indigo-400 animate-spin" /> Processing...
             </div>
          )}
        </div>
      </div>

      {/* 🔴 4. LOCKED INPUT AREA (Shrink-0 keeps it at bottom perfectly) */}
      <div className="shrink-0 w-full bg-[#212121] pt-2 pb-6 px-4 z-20">
        <div className="max-w-3xl mx-auto w-full">
          
          {/* PERFECT FLEX ALIGNMENT */}
          <form onSubmit={handleSendMessage} className="flex items-end bg-[#2f2f2f] rounded-[24px] border border-white/10 shadow-lg focus-within:border-indigo-500/50 focus-within:ring-1 focus-within:ring-indigo-500/20 transition-all p-1.5">
            
            <input type="file" ref={fileInputRef} onChange={handleFileSelect} className="hidden" />
            
            {/* Left: Attach & Mic */}
            <div className="flex items-center gap-1 mb-1 ml-1 shrink-0">
              <button type="button" onClick={() => fileInputRef.current?.click()} className="p-2 text-gray-400 hover:text-white transition-colors rounded-full hover:bg-white/5">
                <Paperclip className="w-5 h-5" />
              </button>
              <button type="button" onClick={toggleListening} className={`p-2 transition-colors rounded-full hover:bg-white/5 ${isListening ? 'text-red-400 animate-pulse bg-red-500/10' : 'text-gray-400 hover:text-white'}`}>
                {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>
            </div>

            {/* Middle: Textarea (flex-1 pushes everything else to the edges) */}
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(e as any); } }}
              placeholder={isListening ? "Listening..." : "Message GSTU Assistant..."}
              className="flex-1 bg-transparent py-2.5 px-3 text-gray-100 placeholder-gray-500 focus:outline-none resize-none max-h-40 min-h-[44px] text-[15.5px] leading-relaxed self-center"
              rows={1}
            />

            {/* Right: Model Dropdown & Send */}
            <div className="flex items-center gap-2 mb-1 mr-1 shrink-0">
              <div className="relative">
                <button type="button" onClick={() => setIsModelMenuOpen(!isModelMenuOpen)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-black/20 hover:bg-black/40 border border-white/5 text-[12px] font-bold text-gray-300 transition-colors">
                  <Zap className={`w-3.5 h-3.5 ${selectedModel === 'gemini' ? 'text-indigo-400' : 'text-emerald-400'}`} />
                  {selectedModel === 'gemini' ? 'Gemini 2.5' : 'Llama 4 Fast'}
                  <ChevronDown className="w-3.5 h-3.5 opacity-70" />
                </button>
                {isModelMenuOpen && (
                  <div className="absolute right-0 bottom-full mb-3 w-48 bg-[#1e1e1e] border border-white/10 rounded-xl shadow-2xl z-50 py-1.5 overflow-hidden">
                    <button type="button" onClick={() => { setSelectedModel('gemini'); setIsModelMenuOpen(false); }} className="w-full flex items-center justify-between px-3 py-2.5 text-[13px] font-medium text-gray-300 hover:bg-white/5 hover:text-white">
                      <div className="flex items-center gap-2"><Zap className="w-4 h-4 text-indigo-400" /> Gemini 2.5 Flash</div>
                    </button>
                    <button type="button" onClick={() => { setSelectedModel('llama'); setIsModelMenuOpen(false); }} className="w-full flex items-center justify-between px-3 py-2.5 text-[13px] font-medium text-gray-300 hover:bg-white/5 hover:text-white">
                      <div className="flex items-center gap-2"><Sparkles className="w-4 h-4 text-emerald-400" /> Llama 4 Fast</div>
                    </button>
                  </div>
                )}
              </div>

              <button type="submit" disabled={!input.trim()} className="p-2 bg-white text-black hover:bg-gray-200 disabled:bg-[#404040] disabled:text-gray-600 rounded-full transition-all shadow-md">
                <ArrowUp className="w-4 h-4" />
              </button>
            </div>
          </form>

        </div>
      </div>
    </div>
  );
}