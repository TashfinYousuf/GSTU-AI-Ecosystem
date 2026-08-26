"use client";
 
import { useState, useEffect, useRef } from "react";
import { ShieldCheck, Users, Activity, Banknote, TrendingUp, HeadphonesIcon, UploadCloud, Rocket, Bell, Headset, Loader2, Brain, MessageSquare, Clock, CheckCircle, FileCheck2, ShieldAlert, Sparkles, Eye, Pencil, Archive, AlertCircle, CheckCircle2, Database, RefreshCw, FileText, Trash2} from "lucide-react";
import { createClient } from "../../utils/supabase/client";
import { fetchAPI } from "../../utils/api";
 
export default function FacultyNodePage() {
  const [activeTab, setActiveTab] = useState("analytics");
  
  // 🔴 Guaranteed Array States (No more null breaks)
  const [tickets, setTickets] = useState<any[]>([]);
  const [notices, setNotices] = useState<any[]>([]);
  const [kbDocs, setKbDocs] = useState<any[]>([]);
  const [pendingFaculty, setPendingFaculty] = useState<any[]>([]);
  
  const [isLoading, setIsLoading] = useState(true);
  const [facultyLoading, setFacultyLoading] = useState(false);
 
  const [stats, setStats] = useState({
    total_users: 0, pro_users: 0, free_users: 0, active_models: 10,
    est_revenue_bdt: 0, trending_topics: [] as any[], dept_users: [] as any[]
  });

  // 🔴 React useRef for file inputs (Solves the unclickable bug)
  const kbFileInputRef = useRef<HTMLInputElement>(null);
  const noticeFileInputRef = useRef<HTMLInputElement>(null);

  // KB Upload States
  const [kbFile, setKbFile] = useState<File | null>(null);
  const [kbCourseCode, setKbCourseCode] = useState("");
  const [kbDocType, setKbDocType] = useState("Lecture Notes");
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
 
  // Notice Publishing States
  const [noticeTitle, setNoticeTitle] = useState("");
  const [noticeCategory, setNoticeCategory] = useState("Official Notice");
  const [noticeDate, setNoticeDate] = useState("");
  const [noticeType, setNoticeType] = useState("");
  const [noticeFile, setNoticeFile] = useState<File | null>(null);
  const [isPublishingNotice, setIsPublishingNotice] = useState(false);
 
  // AI Auto-Reply States
  const [aiDrafts, setAiDrafts] = useState<Record<string, string>>({});
  const [isDrafting, setIsDrafting] = useState<string | null>(null);

  // 🔴 1. Add Super Admin State at the top with other states
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);

  // 🔴 2. Replace the Initial Data Loader useEffect
  useEffect(() => {
    let isMounted = true;
    const loadInitialData = async () => {
      try {
        const supabase = createClient();
        const { data: { session } } = await supabase.auth.getSession();
        
        // Check if Super Admin
        const role = session?.user?.user_metadata?.role || "";
        const email = session?.user?.email || "";
        const adminAccess = role === "admin" || email === "yousufaltashfin@gmail.com";
        
        if (isMounted) {
           setIsSuperAdmin(adminAccess);
           // Default tab for normal faculty
           if (!adminAccess) setActiveTab("knowledge-base");
        }

        // Fetch tickets
        const ticketsRes = await fetchAPI("/admin/tickets").catch(() => null);
        if (ticketsRes?.data && isMounted) setTickets(ticketsRes.data || []);
        
        // 🔴 FIX: Changed from /stats to /analytics to match backend!
        if (adminAccess) {
          const statsRes = await fetchAPI("/admin/analytics").catch(() => null);
          if (statsRes?.data && isMounted) setStats(prev => ({...prev, ...statsRes.data}));
        }
      } catch (error) {
        console.error("Failed to load initial data", error);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };
    loadInitialData();
    return () => { isMounted = false; };
  }, []);

  // Pending Faculty Loader
  const loadPendingFaculty = async () => {
    setFacultyLoading(true);
    try {
      const response = await fetchAPI("/admin/pending-faculty");
      const data = Array.isArray(response) ? response : response?.data || [];
      setPendingFaculty(data);
    } catch (error) {
      console.error("Failed to load pending faculty:", error);
    } finally {
      setFacultyLoading(false);
    }
  };
  
  useEffect(() => {
    if (activeTab === "pending-faculty") loadPendingFaculty();
  }, [activeTab]);

  // AI Auto Reply Handler
  const handleGenerateDraft = async (ticketId: string, query: string, dept: string) => {
    setIsDrafting(ticketId);
    try {
      const res = await fetchAPI("/admin/support/auto-reply", {
        method: "POST",
        body: JSON.stringify({ ticket_query: query, student_department: dept || "General" })
      });
      if (res.status === "success" || res.reply) {
        setAiDrafts(prev => ({ ...prev, [ticketId]: res.reply || res.data }));
      }
    } catch (e) {
      console.error("AI Draft failed", e);
      alert("Failed to connect to AI Support Engine.");
    } finally {
      setIsDrafting(null);
    }
  };
 
  // 🔴 100% Bulletproof Notice Publish
  const handlePublishNotice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!noticeTitle.trim() || !noticeDate) {
      alert("Please provide a title and date.");
      return;
    }
    
    setIsPublishingNotice(true);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      
      let apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      if (apiUrl.endsWith('/')) apiUrl = apiUrl.slice(0, -1);

      const formData = new FormData();
      formData.append("title", noticeTitle);
      formData.append("date", noticeDate);
      formData.append("type", noticeType || "Academic"); // Ensure fallback value
      if (noticeFile) {
        formData.append("file", noticeFile);
      }

      const res = await fetch(`${apiUrl}/api/v1/admin/notices/publish`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${session?.access_token}` },
        body: formData,
      });

      if (res.ok) {
        setNoticeTitle(""); setNoticeDate(""); setNoticeFile(null);
        alert("Notice published successfully!");
        // if (fetchNotices) fetchNotices(); 
      } else {
        // 🔴 Parse FastAPI 422 Array Error gracefully instead of [object Object]
        const err = await res.json().catch(() => ({}));
        let errMsg = "Server rejected the notice.";
        if (Array.isArray(err.detail)) {
          errMsg = err.detail.map((e: any) => `${e.loc.join("->")}: ${e.msg}`).join(", ");
        } else if (err.detail) {
          errMsg = err.detail;
        }
        alert(`Failed: ${errMsg}`);
      }
    } catch (error) {
      console.error(error); 
      alert("Network error during publish.");
    } finally { 
      setIsPublishingNotice(false); 
    }
  };
 
  // ==========================================
  // 📚 3. KNOWLEDGE BASE FETCHER
  // ==========================================
  useEffect(() => {
    let isMounted = true;
    
    const loadInitialData = async () => {
      try {
        const supabase = createClient();
        const { data: { session } } = await supabase.auth.getSession();
        
        // Check if Super Admin
        const role = session?.user?.user_metadata?.role || "";
        const email = session?.user?.email || "";
        const adminAccess = role === "admin" || email === "yousufaltashfin@gmail.com";
        
        if (isMounted) {
           setIsSuperAdmin(adminAccess);
           if (!adminAccess) setActiveTab("knowledge-base");
        }

        // 🔴 Fetch Knowledge Base Logs
        const { data: kbData, error: kbError } = await supabase
          .from("knowledge_base_logs")
          .select("course_tag, doc_type, created_at")
          .order("created_at", { ascending: false })
          .limit(5);

        if (kbData && isMounted) {
          setKbDocs(kbData);
        }

        // Fetch Support Tickets
        const ticketsRes = await fetchAPI("/admin/tickets").catch(() => null);
        if (ticketsRes?.data && isMounted) setTickets(ticketsRes.data || []);
        
        // Fetch Live Analytics
        if (adminAccess) {
          const statsRes = await fetchAPI("/admin/analytics").catch(() => null);
          if (statsRes?.data && isMounted) setStats(prev => ({...prev, ...statsRes.data}));
        }
      } catch (error) {
        console.error("Failed to load initial data", error);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };
    
    loadInitialData();
    
    return () => { isMounted = false; };
  }, []);


  // 🔴 1. State for Upload Message
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  // 🔴 2. Native Fetch to avoid Method Not Allowed errors
  // Add a loading state for the refresh button
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchKbDocs = async () => {
    setIsRefreshing(true); // Start spinning
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/admin/knowledge-base`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${session?.access_token}`,
          "Content-Type": "application/json"
        },
        cache: 'no-store' 
      });
      
      if (res.ok) {
        const result = await res.json();
        setKbDocs(result.data || []);
      }
    } catch (error) {
      console.error("Fetch error:", error);
    } finally {
      setIsRefreshing(false); // Stop spinning
    }
  };

  // 🔴 Activate Delete/Archive Logic
  // 1. Delete Document (Hard Delete)
  const handleDeleteDoc = async (docId: string) => {
    if (!confirm("Are you sure you want to permanently delete this document from Database and AI Vector Store?")) return;
    
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      
      // Fixed the undefined URL issue!
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      
      const res = await fetch(`${apiUrl}/api/v1/admin/knowledge-base/${docId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${session?.access_token}` }
      });
      
      if (res.ok) {
        setUploadMessage("Success: Document permanently deleted.");
        fetchKbDocs(); // UI Refresh
      } else {
        setUploadMessage("Error: Failed to delete document.");
      }
    } catch (error) {
      console.error(error);
      setUploadMessage("Error: Network issue while deleting.");
    }
  };

  // 🔴 2. Archive Document (Soft Delete)
  const handleArchiveDoc = async (docId: string) => {
    if (!confirm("Archive this document? It will be hidden from the AI knowledge base.")) return;
    
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      
      const res = await fetch(`${apiUrl}/api/v1/admin/knowledge-base/${docId}/archive`, {
        method: "PUT",
        headers: { "Authorization": `Bearer ${session?.access_token}` }
      });
      
      if (res.ok) {
        setUploadMessage("Success: Document archived successfully.");
        fetchKbDocs(); // UI Refresh
      }
    } catch (error) {
      console.error(error);
    }
  };

  // 🔴 3. Auto-fetch when the Knowledge Base tab is opened
  useEffect(() => {
    if (activeTab === "knowledge-base") {
      fetchKbDocs();
      setUploadMessage(null); // Reset message on tab switch
    }
  }, [activeTab]);

  // 🔴 4. The Updated Upload Function (No boring alerts!)
  // KB Upload Logic (Updated for RAG 2.0 UI)
  const handleKbUpload = async () => {
    if (!kbFile || !kbCourseCode.trim()) {
      setUploadMessage("Error: Course code and file are required.");
      return;
    }
    
    setIsUploading(true);
    setUploadMessage(null); // Clear previous message

    try {
      // 1. Get Authentication Session
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error("Authentication failed. Please log in again.");
 
      // 2. Prepare Form Data
      const formData = new FormData();
      formData.append("file", kbFile);
      formData.append("course_code", kbCourseCode.trim());
      formData.append("doc_type", kbDocType || "Syllabus");
 
      // 3. Send API Request
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/admin/knowledge-base/upload`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${session.access_token}` },
        body: formData,
      });

      // 4. Handle Response
      if (res.ok) {
        const data = await res.json();
        
        // Success Message in UI (No alert)
        setUploadMessage("Success: " + (data.message || "Document queued for background AI processing."));
        
        // Clear Inputs
        setKbFile(null); 
        setKbCourseCode("");
        
        // Auto-refresh the list from DB to show the new 'Queued' document
        if (typeof fetchKbDocs === 'function') {
          fetchKbDocs(); 
        } else {
          // Fallback if fetchKbDocs is missing
          setKbDocs(prev => [data.document || data, ...prev]);
        }
      } else {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Upload failed from server.");
      }
    } catch (error: any) {
      console.error("Upload Error:", error); 
      setUploadMessage(`Error: ${error.message || "Network error during upload."}`);
    } finally { 
      setIsUploading(false); 
    }
  };


  return (
    <div className="min-h-dvh bg-[#121212] text-gray-200 p-6 md:p-12 font-sans overflow-y-auto custom-scrollbar">
 
      <div className="mb-10">
        <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-3">
          <ShieldCheck className="w-7 h-7 md:w-8 md:h-8 text-emerald-500" /> Faculty & Admin Node
        </h1>
        <p className="text-gray-400 mt-2 text-[13px] md:text-[15px]">Enterprise-grade departmental control center, analytics, and operational hub.</p>
      </div>
 
      {/* Scrollable Tabs */}
      <div className="flex gap-2 border-b border-white/10 mb-8 pb-px overflow-x-auto custom-scrollbar">
        
        {/* Only Super Admins can see the Live Overview Tab */}
        {isSuperAdmin && (
          <button onClick={() => setActiveTab("analytics")} className={`shrink-0 px-4 md:px-6 py-3 text-xs md:text-sm font-semibold rounded-t-xl transition-all ${activeTab === "analytics" ? "text-white bg-[#1e1e1e] border-t border-l border-r border-white/10 shadow-[0_-4px_10px_rgba(0,0,0,0.2)]" : "text-gray-500 hover:text-gray-300"}`}>
            <div className="flex items-center gap-2"><Activity className="w-4 h-4" /> Live Overview</div>
          </button>
        )}

        <button onClick={() => setActiveTab("knowledge-base")} className={`shrink-0 px-4 md:px-6 py-3 text-xs md:text-sm font-bold transition-all ${activeTab === "knowledge-base" ? "text-emerald-400 border-b-2 border-emerald-400" : "text-gray-500 hover:text-gray-300"}`}>
           📚 Knowledge Base
        </button>

        {/* 🔴 Only Super Admins can see Support Desk */}
        {isSuperAdmin && (
        <button onClick={() => setActiveTab("support")} className={`shrink-0 px-4 md:px-6 py-3 text-xs md:text-sm font-semibold rounded-t-xl transition-all ${activeTab === "support" ? "text-white bg-[#1e1e1e] border-t border-l border-r border-white/10 shadow-[0_-4px_10px_rgba(0,0,0,0.2)]" : "text-gray-500 hover:text-gray-300"}`}>
          <div className="flex items-center gap-2">
            <HeadphonesIcon className="w-4 h-4" /> Support Desk 
            {(tickets || []).length > 0 && <span className="bg-rose-500 text-white text-[10px] px-1.5 py-0.5 rounded-full">{(tickets || []).length}</span>}
          </div>
        </button>
        )}

        <button onClick={() => setActiveTab("notices")} className={`shrink-0 px-4 md:px-6 py-3 text-xs md:text-sm font-semibold rounded-t-xl transition-all ${activeTab === "notices" ? "text-white bg-[#1e1e1e] border-t border-l border-r border-white/10 shadow-[0_-4px_10px_rgba(0,0,0,0.2)]" : "text-gray-500 hover:text-gray-300"}`}>
          <div className="flex items-center gap-2"><Bell className="w-4 h-4" /> Notice Approvals</div>
        </button>

        {/* 🔴 Only Super Admins can see Pending Approvals */}
        {isSuperAdmin && (
        <button onClick={() => setActiveTab("pending-faculty")} className={`shrink-0 px-4 md:px-6 py-3 text-xs md:text-sm font-semibold rounded-t-xl transition-all ${activeTab === "pending-faculty" ? "text-white bg-[#1e1e1e] border-t border-l border-r border-white/10 shadow-[0_-4px_10px_rgba(0,0,0,0.2)]" : "text-gray-500 hover:text-gray-300"}`}>
          <div className="flex items-center gap-2"><ShieldAlert className="w-4 h-4"/> Pending Approvals</div>
        </button>
        )}

      </div>
 
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-32 text-emerald-500/50">
          <ShieldCheck className="w-12 h-12 mb-4 animate-pulse" />
          <p className="animate-pulse font-medium">Decrypting Admin Vault...</p>
        </div>
      ) : (
        <div className="max-w-5xl">
 
          {/* 📊 Tab 1: Analytics */}
          {activeTab === "analytics" && stats && (
            <div className="animate-in fade-in slide-in-from-bottom-4 space-y-8">
              {/* Metrics Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl shadow-lg">
                  <div className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-2 flex items-center gap-2"><Users className="w-4 h-4 text-blue-400"/> Total Users</div>
                  <div className="text-3xl font-bold text-white">{stats.total_users}</div>
                </div>
                <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl shadow-lg">
                  <div className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-2 flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-emerald-400"/> Pro / Free</div>
                  <div className="text-2xl font-bold text-white mt-1">{stats.pro_users} <span className="text-gray-500 text-lg">/ {stats.free_users}</span></div>
                </div>
                <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl shadow-lg">
                  <div className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-2 flex items-center gap-2"><Brain className="w-4 h-4 text-purple-400"/> Active Engines</div>
                  <div className="text-3xl font-bold text-white">{stats.active_models}</div>
                </div>
                <div className="bg-linear-to-br from-amber-500/10 to-transparent border border-amber-500/20 p-6 rounded-2xl shadow-lg">
                  <div className="text-amber-500/70 text-xs font-bold uppercase tracking-wider mb-2 flex items-center gap-2"><Banknote className="w-4 h-4 text-amber-400"/> Est. Revenue</div>
                  <div className="text-3xl font-bold text-amber-400">৳ {stats.est_revenue_bdt}</div>
                </div>
              </div>

              {/* Two Column Layout for Lists */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl shadow-lg">
                  <h3 className="text-sm font-bold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2"><TrendingUp className="w-4 h-4 text-rose-400"/> Top Trending Topics</h3>
                  <div className="space-y-3">
                    {stats.trending_topics.map((t: any, i: number) => (
                      <div key={i} className="flex justify-between items-center bg-[#2a2a2a] px-4 py-3 rounded-xl border border-white/5">
                        <span className="text-gray-200 text-sm font-medium">{t.topic}</span>
                        <span className="bg-black/30 text-rose-400 text-xs font-bold px-2 py-1 rounded-md">{t.count} queries</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl shadow-lg">
                  <h3 className="text-sm font-bold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2"><Users className="w-4 h-4 text-indigo-400"/> Department Demographics</h3>
                  <div className="space-y-3">
                    {stats.dept_users.map((d: any, i: number) => (
                      <div key={i} className="flex justify-between items-center bg-[#2a2a2a] px-4 py-3 rounded-xl border border-white/5">
                        <span className="text-gray-200 text-sm font-medium">{d.dept} Department</span>
                        <span className="bg-black/30 text-indigo-400 text-xs font-bold px-2 py-1 rounded-md">{d.count} users</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

 
          {/* =========================================
            KNOWLEDGE BASE TAB (RAG 2.0 ENTERPRISE UI)
            ========================================= */}
          {activeTab === "knowledge-base" && (
            <div className="animate-in fade-in slide-in-from-bottom-4 space-y-8">
              
              {/* Header / Info Box */}
              <div className="bg-gradient-to-r from-blue-900/20 to-indigo-900/10 border border-blue-500/20 p-5 rounded-xl mb-6 shadow-lg">
                <div className="flex gap-3">
                  <Brain className="w-6 h-6 text-blue-400 shrink-0" />
                  <div>
                    <h3 className="text-sm font-bold text-blue-300 mb-1">Knowledge Ingestion Engine</h3>
                    <p className="text-xs text-blue-200/70 leading-relaxed">
                      Upload massive PDFs (Syllabus, Books, Questions). The system will queue, deduplicate, chunk, and embed them safely in the background. Close the browser anytime; processing continues on the server.
                    </p>
                  </div>
                </div>
              </div>

              {/* Upload Section */}
              <div className="bg-[#0f172a]/50 border border-white/5 p-6 rounded-2xl">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                  <div>
                    <label className="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-wider">Course Tag</label>
                    <input type="text" value={kbCourseCode} onChange={(e) => setKbCourseCode(e.target.value)} placeholder="e.g., IR-210-v1" className="w-full bg-[#0b0c10] border border-white/10 focus:border-indigo-500 rounded-lg py-3 px-4 text-white focus:outline-none transition-colors text-sm shadow-inner" />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-wider">Document Type</label>
                    <select value={kbDocType} onChange={(e) => setKbDocType(e.target.value)} className="w-full bg-[#0b0c10] border border-white/10 focus:border-indigo-500 rounded-lg py-3 px-4 text-white focus:outline-none transition-colors text-sm shadow-inner">
                      <option>Syllabus</option>
                      <option>Textbook / PDF</option>
                      <option>Lecture Notes</option>
                      <option>Past Questions</option>
                      <option>Research Paper</option>
                    </select>
                  </div>
                </div>
                
                <div className="mb-6">
                  <div onClick={() => kbFileInputRef.current?.click()} className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center transition-all cursor-pointer group ${kbFile ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-white/10 bg-[#0f172a] hover:border-indigo-500/30 hover:bg-[#1e293b]'}`}>
                    <input ref={kbFileInputRef} type="file" accept=".pdf,.txt" className="hidden" onChange={(e) => setKbFile(e.target.files?.[0] || null)} />
                    {kbFile ? (
                      <div className="flex flex-col items-center gap-2">
                        <div className="p-3 bg-emerald-500/20 rounded-full mb-2"><FileCheck2 className="w-8 h-8 text-emerald-400" /></div>
                        <span className="text-sm font-bold text-emerald-400">{kbFile.name}</span>
                        <span className="text-xs text-gray-500">{(kbFile.size / (1024 * 1024)).toFixed(2)} MB</span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-3 text-gray-500 group-hover:text-indigo-400 transition-colors">
                        <UploadCloud className="w-10 h-10" />
                        <div className="text-center">
                          <p className="text-sm font-bold">Click to browse or drag and drop</p>
                          <p className="text-xs mt-1">PDF or TXT (Max 50MB)</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Status Message (Replaces Browser Alert) */}
                {uploadMessage && (
                  <div className={`p-4 rounded-lg mb-6 text-sm flex items-start gap-3 border ${uploadMessage.includes("Error") || uploadMessage.includes("failed") ? 'bg-rose-500/10 border-rose-500/20 text-rose-400' : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'}`}>
                    {uploadMessage.includes("Error") ? <AlertCircle className="w-5 h-5 shrink-0" /> : <CheckCircle2 className="w-5 h-5 shrink-0" />}
                    <span className="leading-relaxed">{uploadMessage}</span>
                  </div>
                )}

                <button onClick={handleKbUpload} disabled={isUploading || !kbFile || !kbCourseCode.trim()} className="w-full bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-3 disabled:opacity-50 transition-all shadow-lg active:scale-[0.99]">
                  {isUploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Rocket className="w-5 h-5" />} 
                  {isUploading ? "Uploading & Queuing..." : "Process & Memorize"}
                </button>
              </div>

              {/* =========================================
                  DOCUMENT REGISTRY & PROGRESS TRACKER
                  ========================================= */}
              <div className="mt-12">
                <div className="flex items-center justify-between mb-6 border-b border-white/10 pb-4">
                  <h4 className="text-lg font-bold text-white flex items-center gap-2">
                    📚 Knowledge Registry
                    <span className="px-2 py-0.5 bg-white/10 rounded-full text-xs text-gray-400 font-medium ml-2">{kbDocs.length} Docs</span>
                  </h4>
                  <button 
                    type="button" 
                    onClick={fetchKbDocs} 
                    disabled={isRefreshing}
                    className="text-xs flex items-center gap-1.5 text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} /> 
                    {isRefreshing ? 'Refreshing...' : 'Refresh Status'}
                  </button>
                </div>

                {kbDocs.length > 0 ? (
                  <div className="grid grid-cols-1 gap-4">
                    {kbDocs.map((doc, i) => (
                      <div key={i} className="bg-[#0b0c10] border border-white/5 hover:border-white/10 p-5 rounded-xl transition-all group">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                          
                          {/* File Info */}
                          <div className="flex items-start gap-4 overflow-hidden">
                            <div className="p-3 bg-[#1e293b] rounded-lg text-gray-400">
                              <FileText className="w-6 h-6" />
                            </div>
                            <div className="truncate">
                              <h5 className="text-sm font-bold text-gray-200 truncate" title={doc.filename}>{doc.filename}</h5>
                              <div className="flex items-center gap-3 mt-1.5">
                                <span className="text-xs font-medium text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded">{doc.course_code}</span>
                                <span className="text-xs text-gray-500">{doc.doc_type}</span>
                              </div>
                            </div>
                          </div>

                          {/* Status & Progress */}
                          <div className="flex flex-col items-end min-w-[200px]">
                            {doc.status === "queued" && (
                              <span className="flex items-center gap-1.5 text-xs font-bold text-amber-400 bg-amber-400/10 px-3 py-1 rounded-full uppercase tracking-wider">
                                <Clock className="w-3.5 h-3.5" /> Queued
                              </span>
                            )}
                            
                            {doc.status === "processing" && (
                              <div className="w-full text-right">
                                <span className="flex justify-end items-center gap-1.5 text-xs font-bold text-blue-400 mb-1.5 uppercase tracking-wider">
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Ingesting AI Vectors
                                </span>
                                {doc.total_chunks > 0 && (
                                  <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
                                    <div className="bg-blue-500 h-full transition-all duration-500 ease-out" style={{ width: `${(doc.processed_chunks / doc.total_chunks) * 100}%` }}></div>
                                  </div>
                                )}
                                <p className="text-[10px] text-gray-500 mt-1">{doc.processed_chunks} / {doc.total_chunks} Chunks</p>
                              </div>
                            )}
                            
                            {doc.status === "active" && (
                              <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-400 bg-emerald-400/10 px-3 py-1 rounded-full uppercase tracking-wider">
                                <CheckCircle2 className="w-3.5 h-3.5" /> Active
                              </span>
                            )}

                            {doc.status === "failed" && (
                              <span className="flex items-center gap-1.5 text-xs font-bold text-rose-400 bg-rose-400/10 px-3 py-1 rounded-full uppercase tracking-wider" title={doc.error_msg}>
                                <AlertCircle className="w-3.5 h-3.5" /> Failed
                              </span>
                            )}
                          </div>

                          {/* 🔴 Actions Buttons (View, Edit, Archive, Delete) */}
                          <div className="flex items-center gap-2 border-l border-white/10 pl-4">
                            {/* VIEW */}
                            <a href={doc.public_url} target="_blank" rel="noreferrer" className="p-2 text-gray-500 hover:text-white hover:bg-white/5 rounded-lg transition-colors tooltip" title="View PDF">
                              <Eye className="w-4 h-4" />
                            </a>
                            
                            {/* EDIT (Just an alert for now, you can add a modal later) */}
                            <button onClick={() => alert("Edit modal coming soon!")} className="p-2 text-gray-500 hover:text-indigo-400 hover:bg-indigo-500/10 rounded-lg transition-colors" title="Edit Metadata">
                              <Pencil className="w-4 h-4" />
                            </button>
                            
                            {/* ARCHIVE */}
                            <button onClick={() => handleArchiveDoc(doc.id)} className="p-2 text-gray-500 hover:text-amber-400 hover:bg-amber-500/10 rounded-lg transition-colors" title="Archive Document">
                              <Archive className="w-4 h-4" />
                            </button>

                            {/* DELETE */}
                            <button onClick={() => handleDeleteDoc(doc.id)} className="p-2 text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors" title="Delete Document">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>

                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 border border-dashed border-white/5 rounded-2xl bg-white/[0.02]">
                    <Database className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                    <h5 className="text-gray-300 font-medium">Knowledge Base is Empty</h5>
                    <p className="text-sm text-gray-500 mt-1">Upload course materials to start training the AI.</p>
                  </div>
                )}
              </div>
            </div>
          )}
 
          {activeTab === "support" && (
          <div className="bg-[#1e1e1e] border border-white/5 rounded-3xl shadow-xl p-6 md:p-8 animate-in fade-in min-h-[400px]">
            <h3 className="text-xl font-bold text-white mb-6">Pending Support Tickets</h3>

            {tickets.length > 0 ? (
              <div className="space-y-4">
                {tickets.map((t) => (
                  <div key={t.id} className="flex flex-col p-5 bg-[#0a0a0a] border border-white/5 rounded-2xl">
                    <div className="flex flex-col md:flex-row md:items-center justify-between mb-4 gap-4">
                      <div>
                        <span className="text-[10px] font-bold text-rose-500 uppercase tracking-wider bg-rose-500/10 px-2 py-1 rounded-md mb-2 inline-block">
                          {t.department || "General"} Issue
                        </span>
                        <p className="text-gray-200 font-medium text-sm md:text-base leading-relaxed">{t.query}</p>
                      </div>
                      <div className="flex gap-2 shrink-0">
                        <button 
                          onClick={() => handleGenerateDraft(t.id, t.query, t.department)}
                          disabled={isDrafting === t.id}
                          className="px-4 py-2 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 rounded-lg text-xs font-bold transition-colors flex items-center gap-2"
                        >
                          {isDrafting === t.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                          AI Draft
                        </button>
                        <button
                          onClick={async () => {
                            try {
                              await fetchAPI(`/admin/tickets/${t.id}/resolve`, { method: "POST" });
                              setTickets(prev => prev.filter(x => x.id !== t.id));
                            } catch (err) { console.error("Resolve failed", err); }
                          }}
                          className="px-4 py-2 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 rounded-lg text-xs font-bold transition-colors"
                        >
                          Resolve
                        </button>
                      </div>
                    </div>

                    {/* AI Draft Box */}
                    {aiDrafts[t.id] && (
                      <div className="mt-2 bg-[#171717] p-4 rounded-xl border border-indigo-500/20 animate-in fade-in">
                        <label className="text-[11px] font-bold text-indigo-400 uppercase mb-2 block">AI Draft (Edit before sending)</label>
                        <textarea 
                          value={aiDrafts[t.id]} 
                          onChange={(e) => setAiDrafts(prev => ({...prev, [t.id]: e.target.value}))}
                          className="w-full bg-[#0a0a0a] border border-white/10 rounded-lg p-3 text-sm text-gray-300 focus:border-indigo-500 outline-none min-h-[100px]"
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-gray-500 border border-dashed border-white/10 rounded-2xl bg-[#121212]/50">
                <MessageSquare className="w-16 h-16 mb-4 opacity-30 text-gray-400" />
                <p className="text-sm">No active support tickets found.</p>
              </div>
            )}
          </div>
        )}

        {/* 🔔 TAB 4: PUBLISH NOTICES */}
          {activeTab === "notices" && (
            <div className="bg-[#171923] w-full rounded-2xl shadow-2xl border border-amber-500/30 p-8 animate-in fade-in">
              <h3 className="text-white font-bold flex items-center gap-2 text-lg mb-6">📢 Publish Department Update</h3>
              
              <div className="bg-amber-500/10 border border-amber-500/20 p-4 rounded-xl mb-6">
                <p className="text-sm text-amber-200/80 leading-relaxed">Upload official notices, class routines, or semester results here.</p>
              </div>

              <div className="space-y-5 mb-6">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-2">Title / Subject:</label>
                  <input type="text" value={noticeTitle} onChange={(e) => setNoticeTitle(e.target.value)} placeholder="e.g., Final Exam Routine" className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-amber-500 text-sm" />
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-2">Category:</label>
                    <select value={noticeCategory} onChange={(e) => setNoticeCategory(e.target.value)} className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-amber-500 text-sm">
                      <option>Official Notice</option><option>Class Routine</option><option>Semester Result</option><option>Event/Seminar</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-2">Publish Date:</label>
                    <input type="date" value={noticeDate} onChange={(e) => setNoticeDate(e.target.value)} className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-amber-500 text-sm" />
                  </div>
                </div>
              </div>

              {/* 🔴 FIX: Restored File Upload Click & Ref Logic */}
              <div className="mb-6">
                <label className="block text-xs font-medium text-gray-400 mb-2">Attach Document (Optional)</label>
                <div onClick={() => noticeFileInputRef.current?.click()} className="border-2 border-dashed border-white/10 rounded-xl p-8 flex flex-col items-center justify-center bg-[#0f172a] hover:bg-[#1e293b] transition-colors cursor-pointer group">
                  <input ref={noticeFileInputRef} type="file" accept=".pdf,.png,.jpg,.jpeg" className="hidden" onChange={(e) => setNoticeFile(e.target.files?.[0] || null)} />
                  {noticeFile ? (
                    <span className="text-sm text-emerald-400 font-medium">{noticeFile.name}</span>
                  ) : (
                    <button type="button" className="bg-white/5 group-hover:bg-white/10 border border-white/10 text-white px-6 py-2.5 rounded-lg text-sm font-medium flex items-center gap-2 pointer-events-none">
                      <UploadCloud className="w-5 h-5" /> Attach PDF/Image
                    </button>
                  )}
                </div>
              </div>

              {/* 🔴 FIX: Bound onClick event to handlePublishNotice */}
              <button onClick={handlePublishNotice} disabled={isPublishingNotice || !noticeTitle} className="w-full bg-amber-700 hover:bg-amber-600 text-white font-bold py-4 rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50">
                {isPublishingNotice ? <Loader2 className="w-5 h-5 animate-spin" /> : <Bell className="w-5 h-5" />} Publish to Department Hub
              </button>
            </div>
          )}


          {/* PENDING FACULTY TAB */}
          {activeTab === "pending-faculty" && (
            <div className="bg-[#1e1e1e] border border-white/5 rounded-3xl shadow-xl p-6 md:p-8 animate-in fade-in min-h-[400px]">
              <h3 className="text-xl font-bold text-white mb-6">Pending Faculty Approvals</h3>
              {facultyLoading ? (
                 <div className="flex justify-center py-10"><Loader2 className="w-6 h-6 animate-spin text-emerald-500" /></div>
              ) : pendingFaculty && pendingFaculty.length > 0 ? (
                <div className="space-y-4">
                  {pendingFaculty.map(faculty => (
                    <div key={faculty.id} className="p-5 bg-[#0a0a0a] border border-white/10 rounded-2xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                      <div>
                        <p className="text-white font-medium">{faculty.full_name || "Unknown Faculty"}</p>
                        <p className="text-sm text-gray-400">{faculty.email}</p>
                        <span className="text-[10px] bg-yellow-500/10 text-yellow-500 px-2 py-1 rounded mt-2 inline-block">PENDING REVIEW</span>
                      </div>
                      <div className="flex gap-2">
                        {/* 🔴 FIX: Restored Backend Calls for Approve and Reject */}
                        <button 
                          onClick={async () => {
                            try {
                              await fetchAPI(`/admin/pending-faculty/${faculty.id}/approve`, { method: "POST" });
                              setPendingFaculty(prev => prev.filter(f => f.id !== faculty.id));
                              alert("Faculty Approved!");
                            } catch (e) { console.error(e); }
                          }} 
                          className="px-4 py-2 bg-emerald-600/20 text-emerald-400 text-xs font-bold rounded-lg hover:bg-emerald-600/30 transition">Approve</button>
                          
                        <button 
                          onClick={async () => {
                            try {
                              await fetchAPI(`/admin/pending-faculty/${faculty.id}/reject`, { method: "POST" });
                              setPendingFaculty(prev => prev.filter(f => f.id !== faculty.id));
                              alert("Faculty Rejected!");
                            } catch (e) { console.error(e); }
                          }} 
                          className="px-4 py-2 bg-rose-600/20 text-rose-400 text-xs font-bold rounded-lg hover:bg-rose-600/30 transition">Reject</button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-gray-500 border border-dashed border-white/10 rounded-2xl bg-[#121212]/50">
                  <ShieldCheck className="w-16 h-16 mb-4 opacity-30 text-gray-400" />
                  <p className="text-sm font-medium">No pending approvals.</p>
                </div>
              )}
            </div>
         )}
         
        </div>
      )}
    </div>
  );
}