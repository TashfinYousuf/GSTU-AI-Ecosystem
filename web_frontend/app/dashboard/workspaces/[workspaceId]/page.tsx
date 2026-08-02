"use client";

import { useState, useEffect, useRef, use } from "react";
import { ArrowUp, Paperclip, Database, FileText, X, Trash2, Sparkles, Brain, PenTool, CheckSquare, Clock, Network, Bell, Mic, MicOff } from "lucide-react";
import { createClient } from "../../../utils/supabase/client";
import dynamic from 'next/dynamic';

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

    try {
      const res = await fetch("http://localhost:8000/api/v1/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${session.access_token}` },
        body: JSON.stringify({ message: userText, workspace_id: workspaceId })
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
    <div className="flex flex-col h-screen bg-[#212121] relative font-sans text-gray-200 overflow-hidden">
      
      {/* 🔴 Interactive GraphRAG Modal Overlay */}
      {isGraphOpen && graphData && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-sm transition-all">
          <div className="bg-[#1a1a1a] w-full max-w-5xl h-[80vh] rounded-2xl border border-white/10 shadow-2xl relative overflow-hidden flex flex-col">
            <div className="p-4 border-b border-white/10 flex justify-between items-center bg-[#212121]">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <Network className="w-5 h-5 text-indigo-400" /> Interactive Knowledge Graph: <span className="text-indigo-300">{graphTopic}</span>
              </h3>
              <button onClick={() => setIsGraphOpen(false)} className="text-gray-400 hover:text-white transition-colors bg-white/5 p-1.5 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            {/* The Graph Canvas */}
            <div className="flex-1 bg-[#0f0f0f] relative cursor-grab active:cursor-grabbing">
              <ForceGraph2D
                graphData={graphData}
                nodeLabel="id"
                nodeColor={() => '#6366f1'} // Indigo 500
                nodeRelSize={6}
                linkColor={() => 'rgba(255,255,255,0.15)'}
                linkDirectionalArrowLength={3.5}
                linkDirectionalArrowRelPos={1}
                backgroundColor="#0f0f0f"
                linkCurvature={0.25}
              />
              <div className="absolute bottom-4 left-4 text-xs text-gray-500 bg-black/50 px-3 py-1.5 rounded-full backdrop-blur-md">
                Hint: Scroll to zoom, Drag to move nodes
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="absolute top-0 w-full h-16 bg-[#212121]/80 backdrop-blur-md border-b border-white/5 flex items-center justify-between px-6 z-20">
        <div className="font-medium text-gray-200 flex items-center gap-2">
          {workspaceName} <span className="px-2 py-0.5 bg-indigo-500/10 text-indigo-400 text-[10px] uppercase rounded-full border border-indigo-500/20">Academic Mode</span>
        </div>
        <button onClick={() => setIsKbOpen(!isKbOpen)} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${isKbOpen ? 'bg-indigo-500/20 text-indigo-400' : 'bg-[#2f2f2f] text-gray-400 hover:text-gray-200'}`}>
          <Database className="w-4 h-4" /> Knowledge Base <span className="bg-white/10 px-1.5 py-0.5 rounded text-xs ml-1">{documents.length}</span>
        </button>
      </div>

      {/* Sliding Knowledge Base Panel */}
      <div className={`absolute top-16 right-0 bottom-0 w-80 bg-[#1a1a1a] border-l border-white/5 z-30 transform transition-transform duration-300 ease-in-out flex flex-col ${isKbOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="p-4 border-b border-white/5 flex items-center justify-between">
          <h3 className="font-semibold text-gray-200 flex items-center gap-2"><Database className="w-4 h-4 text-indigo-400" /> Workspace Data</h3>
          <button onClick={() => setIsKbOpen(false)} className="text-gray-500 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {documents.length === 0 ? (
            <p className="text-sm text-gray-500 text-center mt-10">No documents uploaded yet.</p>
          ) : (
            documents.map((doc) => (
              <div key={doc.id} className="flex items-start gap-3 p-3 rounded-xl bg-[#2f2f2f] border border-white/5 group relative overflow-hidden">
                <FileText className="w-8 h-8 text-indigo-400 shrink-0 p-1.5 bg-indigo-500/10 rounded-lg" />
                <div className="flex-1 min-w-0 pr-8">
                  <p className="text-sm font-medium text-gray-200 truncate" title={doc.filename}>{doc.filename}</p>
                </div>
                <button onClick={() => handleDeleteDoc(doc.id)} className="absolute right-2 top-2 p-2 bg-red-500/10 text-red-400 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-500/20 transition-all"><Trash2 className="w-4 h-4" /></button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto pb-48 pt-24 scroll-smooth">
        <div className="max-w-3xl mx-auto w-full px-4 flex flex-col space-y-8">
          {messages.map((msg) => (
            <div key={msg.id} className="flex flex-col w-full">
              <span className="text-[13px] font-semibold text-gray-400 mb-1.5 ml-1">{msg.role === "user" ? "You" : workspaceName}</span>
              <div className={`text-[15.5px] leading-relaxed break-words whitespace-pre-wrap ${msg.role === "user" ? "bg-[#2f2f2f] px-4 py-3 rounded-2xl w-fit max-w-full text-gray-100" : "text-gray-200 px-1"}`}>
                {msg.content}
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex flex-col w-full">
              <span className="text-[13px] font-semibold text-gray-400 mb-1.5 ml-1">{workspaceName}</span>
              <div className="text-[15px] text-gray-400 px-1 animate-pulse flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-400 animate-spin" /> Processing academic task...
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input Area & Copilot Overlay */}
      <div className="absolute bottom-0 w-full bg-gradient-to-t from-[#212121] via-[#212121] to-transparent pt-10 pb-6 px-4 z-10">
        <div className="max-w-3xl mx-auto w-full relative">
          
          {/* Copilot Menu */}
          {isCopilotOpen && (
            <div className="absolute bottom-20 left-0 w-64 bg-[#1f1f1f] border border-white/10 rounded-2xl shadow-2xl overflow-hidden p-2 flex flex-col gap-1 z-20 animate-in fade-in slide-in-from-bottom-4">
              <div className="px-3 py-2 text-[11px] uppercase tracking-wider font-semibold text-gray-500">Teacher & Student Tools</div>
              
              {/* 🔴 Concept Map Button */}
              <button onClick={() => handleCopilotAction("Concept Map")} className="flex items-center gap-3 px-3 py-2.5 hover:bg-white/5 rounded-xl text-sm text-left text-gray-200 transition-colors">
                <Network className="w-4 h-4 text-cyan-400" /> Generate Concept Map
              </button>

              <button onClick={() => handleCopilotAction("Mock Exam")} className="flex items-center gap-3 px-3 py-2.5 hover:bg-white/5 rounded-xl text-sm text-left text-gray-200 transition-colors">
                <Brain className="w-4 h-4 text-purple-400" /> Generate Mock Exam
              </button>
              <button onClick={() => handleCopilotAction("rubric")} className="flex items-center gap-3 px-3 py-2.5 hover:bg-white/5 rounded-xl text-sm text-left text-gray-200 transition-colors">
                <CheckSquare className="w-4 h-4 text-emerald-400" /> Create Grading Rubric
              </button>
              <button onClick={() => handleCopilotAction("Smart Routine")} className="flex items-center gap-3 px-3 py-2.5 hover:bg-white/5 rounded-xl text-sm text-left text-gray-200 transition-colors">
                <Clock className="w-4 h-4 text-orange-400" /> Smart Study Routine
              </button>
              <button onClick={() => handleCopilotAction("Formal Notice")} className="flex items-center gap-3 px-3 py-2.5 hover:bg-white/5 rounded-xl text-sm text-left text-gray-200 transition-colors">
                <Bell className="w-4 h-4 text-yellow-400" /> Draft Formal Notice
              </button>
            </div>
          )}

          {/* Copilot Trigger Button */}
          <button 
            onClick={() => setIsCopilotOpen(!isCopilotOpen)}
            className={`absolute -top-10 left-2 flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold shadow-lg transition-all ${isCopilotOpen ? 'bg-indigo-500 text-white shadow-indigo-500/25' : 'bg-[#2f2f2f] text-indigo-400 hover:bg-indigo-500/10 border border-indigo-500/20'}`}
          >
            <Sparkles className="w-3.5 h-3.5" /> {isCopilotOpen ? "Close Copilot" : "Academic Copilot"}
          </button>

          <form onSubmit={handleSendMessage} className="relative flex items-end bg-[#2f2f2f] rounded-3xl overflow-hidden focus-within:ring-1 focus-within:ring-white/20 transition-all border border-white/5">
            <input type="file" ref={fileInputRef} onChange={handleFileSelect} className="hidden" />
            <button type="button" onClick={(e) => { e.preventDefault(); fileInputRef.current?.click(); }} className="p-3 ml-1 mb-1 text-gray-400 hover:text-white transition-colors z-10" title="Attach PDF for RAG">
              <Paperclip className="w-5 h-5" />
            </button>
            
            {/* 🔴 Voice Input Button */}
            <button 
              type="button" 
              onClick={toggleListening} 
              className={`p-3 mb-1 transition-colors z-10 ${isListening ? 'text-red-400 animate-pulse' : 'text-gray-400 hover:text-white'}`} 
              title={isListening ? "Listening... Click to stop" : "Use Voice Input"}
            >
              {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>

            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(e as any); } }}
              placeholder={isListening ? "Listening..." : "Ask anything or use the Copilot..."}
              className="w-full bg-transparent py-4 pr-12 text-gray-100 placeholder-gray-500 focus:outline-none resize-none max-h-48 min-h-[56px] text-[15px]"
              rows={1}
            />
            <button type="submit" disabled={!input.trim()} className="absolute right-2 bottom-2 p-2 bg-white text-black hover:bg-gray-200 disabled:bg-[#404040] disabled:text-gray-500 rounded-full transition-all z-10">
              <ArrowUp className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}