"use client";

import { useState, useEffect, useRef, use } from "react";
import { ArrowUp, Paperclip, Database, FileText, X, Trash2} from "lucide-react";
import { createClient } from "../../../utils/supabase/client";

export default function WorkspaceChatPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = use(params);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [workspaceName, setWorkspaceName] = useState("...");
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [messages, setMessages] = useState<{id: string, role: string, content: string}[]>([]);
  
  // 🔴 New States for Knowledge Base
  const [documents, setDocuments] = useState<{id: string, filename: string}[]>([]);
  const [isKbOpen, setIsKbOpen] = useState(false);

  // 🔴 Fetch Workspace Data, Chat History, AND Documents
  const fetchWorkspaceData = async () => {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    
    if (session?.access_token) {
      try {
        // 1. Fetch Workspace Name
        const wsRes = await fetch("http://localhost:8000/api/v1/workspaces", {
          headers: { "Authorization": `Bearer ${session.access_token}` }
        });
        if (wsRes.ok) {
          const data = await wsRes.json();
          const currentWs = data.find((ws: any) => ws.id === workspaceId);
          if (currentWs) setWorkspaceName(currentWs.name);
        }

        // 2. Fetch Chat History
        const histRes = await fetch(`http://localhost:8000/api/v1/chat/history/${workspaceId}`, {
          headers: { "Authorization": `Bearer ${session.access_token}` }
        });
        if (histRes.ok) {
          const historyData = await histRes.json();
          if (historyData.length > 0) setMessages(historyData);
          else setMessages([{ id: "1", role: "ai", content: "How can I help you with your research today?" }]);
        } else {
          setMessages([{ id: "1", role: "ai", content: "How can I help you with your research today?" }]);
        }

        // 🔴 3. Fetch Uploaded Documents
        const docRes = await fetch(`http://localhost:8000/api/v1/documents/list/${workspaceId}`, {
          headers: { "Authorization": `Bearer ${session.access_token}` }
        });
        if (docRes.ok) {
          const docData = await docRes.json();
          setDocuments(docData);
        }
      } catch (error) {
        console.error("Failed to load workspace data", error);
      }
    }
  };

  useEffect(() => {
    fetchWorkspaceData();
  }, [workspaceId]);

  // 🔴 Updated File Upload Logic (Auto-refreshes Knowledge Base)
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.type !== "application/pdf") {
      alert("Only PDF files are currently supported for AI processing.");
      return;
    }

    setIsTyping(true);
    const uploadingMsgId = Date.now().toString();
    setMessages((prev) => [...prev, { id: uploadingMsgId, role: "ai", content: `Uploading and processing document: **${file.name}**... Please wait.` }]);

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
        setMessages((prev) => prev.map(msg => msg.id === uploadingMsgId ? { ...msg, content: `✅ **Success!** ${data.message}. I have read the document.` } : msg));
        
        // 🔴 ফাইল আপলোড সাকসেস হলে ডকুমেন্টের লিস্ট রিফ্রেশ করা
        fetchWorkspaceData(); 
      } else {
        throw new Error("Upload failed");
      }
    } catch (error) {
      setMessages((prev) => prev.map(msg => msg.id === uploadingMsgId ? { ...msg, content: `❌ **Error:** Failed to process the document.` } : msg));
    } finally {
      setIsTyping(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // 🔴 Delete Document Logic
  const handleDeleteDoc = async (docId: string) => {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    
    if (session?.access_token) {
      try {
        const res = await fetch(`http://localhost:8000/api/v1/documents/delete/${workspaceId}/${docId}`, {
          method: "DELETE",
          headers: { "Authorization": `Bearer ${session.access_token}` }
        });
        if (res.ok) {
          fetchWorkspaceData(); // ডিলিট হওয়ার পর লিস্ট রিফ্রেশ হবে
        }
      } catch (error) {
        console.error("Failed to delete document", error);
      }
    }
  };

  // Chat Streaming Logic
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userText = input;
    const newUserMsg = { id: Date.now().toString(), role: "user", content: userText };
    setMessages((prev) => [...prev, newUserMsg]);
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
      setMessages((prev) => [...prev, { id: aiMsgId, role: "ai", content: "" }]);
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
              setMessages((prev) => prev.map(msg => msg.id === aiMsgId ? { ...msg, content: msg.content + text + " " } : msg));
            }
          }
        }
      }
    } catch (error) {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#212121] relative font-sans text-gray-200 overflow-hidden">
      
      {/* 🔴 Top Header with Knowledge Base Toggle */}
      <div className="absolute top-0 w-full h-16 bg-[#212121]/80 backdrop-blur-md border-b border-white/5 flex items-center justify-between px-6 z-20">
        <div className="font-medium text-gray-200">{workspaceName} Chat</div>
        <button 
          onClick={() => setIsKbOpen(!isKbOpen)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${isKbOpen ? 'bg-indigo-500/20 text-indigo-400' : 'bg-[#2f2f2f] text-gray-400 hover:text-gray-200'}`}
        >
          <Database className="w-4 h-4" />
          Knowledge Base <span className="bg-white/10 px-1.5 py-0.5 rounded text-xs ml-1">{documents.length}</span>
        </button>
      </div>

      {/* 🔴 Sliding Knowledge Base Panel */}
      <div className={`absolute top-16 right-0 bottom-0 w-80 bg-[#1a1a1a] border-l border-white/5 z-30 transform transition-transform duration-300 ease-in-out flex flex-col ${isKbOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="p-4 border-b border-white/5 flex items-center justify-between">
          <h3 className="font-semibold text-gray-200 flex items-center gap-2">
            <Database className="w-4 h-4 text-indigo-400" /> Workspace Data
          </h3>
          <button onClick={() => setIsKbOpen(false)} className="text-gray-500 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {documents.length === 0 ? (
            <p className="text-sm text-gray-500 text-center mt-10">No documents uploaded yet. Use the paperclip icon in the chat to add PDFs.</p>
          ) : (
            documents.map((doc) => (
              <div key={doc.id} className="flex items-start gap-3 p-3 rounded-xl bg-[#2f2f2f] border border-white/5 group relative overflow-hidden">
                <FileText className="w-8 h-8 text-indigo-400 shrink-0 p-1.5 bg-indigo-500/10 rounded-lg" />
                <div className="flex-1 min-w-0 pr-8">
                  <p className="text-sm font-medium text-gray-200 truncate" title={doc.filename}>{doc.filename}</p>
                  <p className="text-xs text-gray-500 mt-0.5">Vectorized & Ready</p>
                </div>
                
                {/* 🔴 Delete Button (Hover করলে ভেসে উঠবে) */}
                <button 
                  onClick={() => handleDeleteDoc(doc.id)} 
                  className="absolute right-2 top-2 p-2 bg-red-500/10 text-red-400 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-500/20 transition-all"
                  title="Delete Document"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto pb-40 pt-24 scroll-smooth">
        <div className="max-w-3xl mx-auto w-full px-4 flex flex-col space-y-8">
          {messages.map((msg) => (
            <div key={msg.id} className="flex flex-col w-full">
              <span className="text-[13px] font-semibold text-gray-400 mb-1.5 ml-1">
                {msg.role === "user" ? "You" : workspaceName}
              </span>
              <div className={`text-[15.5px] leading-relaxed break-words ${msg.role === "user" ? "bg-[#2f2f2f] px-4 py-3 rounded-2xl w-fit max-w-full text-gray-100" : "text-gray-200 px-1"}`}>
                {msg.content}
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex flex-col w-full">
              <span className="text-[13px] font-semibold text-gray-400 mb-1.5 ml-1">{workspaceName}</span>
              <div className="text-[15px] text-gray-400 px-1 animate-pulse">Thinking...</div>
            </div>
          )}
        </div>
      </div>

      {/* Input Box */}
      <div className="absolute bottom-0 w-full bg-gradient-to-t from-[#212121] via-[#212121] to-transparent pt-6 pb-6 px-4 z-10">
        <div className="max-w-3xl mx-auto w-full">
          <form onSubmit={handleSendMessage} className="relative flex items-end bg-[#2f2f2f] rounded-3xl overflow-hidden focus-within:ring-1 focus-within:ring-white/20 transition-all">
            <input type="file" ref={fileInputRef} onChange={handleFileSelect} className="hidden" />
            <button type="button" onClick={(e) => { e.preventDefault(); fileInputRef.current?.click(); }} className="p-3 ml-1 mb-1 text-gray-400 hover:text-white transition-colors z-10">
              <Paperclip className="w-5 h-5" />
            </button>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(e as any); } }}
              placeholder={`Message ${workspaceName}...`}
              className="w-full bg-transparent py-4 pr-12 text-gray-100 placeholder-gray-500 focus:outline-none resize-none max-h-48 min-h-[56px] text-[15px]"
              rows={1}
            />
            <button type="submit" disabled={!input.trim()} className="absolute right-2 bottom-2 p-2 bg-white text-black hover:bg-gray-200 disabled:bg-[#404040] disabled:text-gray-500 rounded-full transition-all z-10">
              <ArrowUp className="w-4 h-4" />
            </button>
          </form>
          <p className="text-center text-xs text-gray-500 mt-2">AI can make mistakes. Check important info.</p>
        </div>
      </div>
    </div>
  );
}