"use client";
 
import { useState, useEffect, useRef } from "react";
import { ShieldCheck, Users, Activity, Banknote, TrendingUp, HeadphonesIcon, UploadCloud, Rocket, Bell, Headset, Loader2, Brain, MessageSquare, Clock, CheckCircle, FileCheck2, ShieldAlert, Sparkles } from "lucide-react";
import { createClient } from "../../utils/supabase/client";
import { fetchAPI } from "../../utils/api";
 
export default function FacultyNodePage() {
  const [activeTab, setActiveTab] = useState("analytics");
  
  // 🔴 NUCLEAR FIX 2: Guaranteed Array States (No more null breaks)
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

  // 🔴 NUCLEAR FIX 1: React useRef for file inputs (Solves the unclickable bug)
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
 
  // Publishing Logic
  const handlePublishNotice = async () => {
    if (!noticeTitle.trim() || !noticeDate) return alert("Title and date required.");
    setIsPublishingNotice(true);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error("No session");
 
      const formData = new FormData();
      formData.append("title", noticeTitle.trim());
      formData.append("category", noticeCategory);
      formData.append("publish_date", noticeDate);
      if (noticeFile) formData.append("file", noticeFile);
 
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/admin/notices/publish`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${session.access_token}` },
        body: formData,
      });
      if (res.ok) {
        setNoticeTitle(""); setNoticeDate(""); setNoticeFile(null);
        alert("Notice published successfully!");
      } else throw new Error("Upload failed");
    } catch (error) {
      console.error(error); alert("Network error during publish.");
    } finally { setIsPublishingNotice(false); }
  };
 
  // KB Upload Logic
  const handleKbUpload = async () => {
    if (!kbFile || !kbCourseCode.trim()) return alert("Course code and file required.");
    setIsUploading(true);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error("No session");
 
      const formData = new FormData();
      formData.append("file", kbFile);
      formData.append("course_code", kbCourseCode.trim());
      formData.append("doc_type", kbDocType);
 
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/admin/knowledge-base/upload`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${session.access_token}` },
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        setKbDocs(prev => [data.document || data, ...prev]);
        setKbFile(null); setKbCourseCode("");
        alert("Document processed and memorized by AI.");
      } else throw new Error("Upload failed");
    } catch (error) {
      console.error(error); alert("Network error during upload.");
    } finally { setIsUploading(false); }
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

        // 🔴 Fetch Knowledge Base Logs (Just like app.py)
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


  return (
    <div className="min-h-screen bg-[#121212] text-gray-200 p-6 md:p-12 font-sans overflow-y-auto custom-scrollbar pt-16 md:pt-0">
 
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

 
          {/* KNOWLEDGE BASE TAB */}
          {activeTab === "knowledge-base" && (
            <div className="animate-in fade-in slide-in-from-bottom-4 space-y-8">
              <div className="bg-[#1e3a8a]/20 border border-blue-500/20 p-4 rounded-xl mb-6">
                <p className="text-sm text-blue-200/80 leading-relaxed">
                  Upload syllabus, lecture notes, or past questions. The AI will automatically chunk, embed, and memorize them securely.
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-2">Course Code & Version:</label>
                  <input type="text" value={kbCourseCode} onChange={(e) => setKbCourseCode(e.target.value)} placeholder="e.g., IR-210-v1" className="w-full bg-[#0b0c10] border border-emerald-500/30 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-emerald-500 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-2">Document Type:</label>
                  <select value={kbDocType} onChange={(e) => setKbDocType(e.target.value)} className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-emerald-500 text-sm">
                    <option>Lecture Notes</option><option>Syllabus</option><option>Past Questions</option>
                  </select>
                </div>
              </div>
              
              <div className="mb-6">
                {/* 🔴 NUCLEAR FIX 1: Direct useRef click trigger (Solves unclickable bug) */}
                <div onClick={() => kbFileInputRef.current?.click()} className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center transition-colors cursor-pointer group border-white/10 bg-[#0f172a] hover:bg-[#1e293b]`}>
                  <input 
                    ref={kbFileInputRef} 
                    type="file" 
                    accept=".pdf,.txt" 
                    className="hidden" 
                    onChange={(e) => setKbFile(e.target.files?.[0] || null)} 
                  />
                  {kbFile ? (
                    <div className="flex items-center gap-2 text-emerald-400"><FileCheck2 className="w-6 h-6" /><span className="text-sm font-medium">{kbFile.name}</span></div>
                  ) : (
                    <button type="button" className="bg-white/5 group-hover:bg-white/10 border border-white/10 text-white px-6 py-3 rounded-lg text-sm font-medium flex items-center gap-2 pointer-events-none"><UploadCloud className="w-5 h-5" /> Upload File</button>
                  )}
                </div>
              </div>

              <button onClick={handleKbUpload} disabled={isUploading || !kbFile || !kbCourseCode.trim()} className="w-full bg-[#059669] hover:bg-[#10b981] text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg">
                {isUploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Rocket className="w-5 h-5" />} Process & Memorize (Train AI)
              </button>

              {/* 🔴 ACTIVE VECTORS LIST */}
              <div className="mt-12 border-t border-white/10 pt-8">
                <h4 className="text-lg font-bold text-gray-300 flex items-center gap-2 mb-4">🗄️ Currently Active Knowledge Vectors</h4>
                {kbDocs.length > 0 ? (
                  <div className="space-y-3">
                    {kbDocs.map((doc, i) => (
                      <div key={i} className="flex items-center gap-3 text-sm text-gray-400 bg-[#0a0a0a] p-3 rounded-lg border border-white/5">
                        <span className="text-emerald-500">🏷️</span>
                        <strong className="text-gray-200">{doc.course_tag || doc.course_code}</strong> 
                        <span className="px-2 py-0.5 bg-white/5 rounded text-xs">({doc.doc_type})</span>
                        <span className="ml-auto text-emerald-400/80 text-xs font-bold uppercase tracking-wider">Active</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 italic">No custom knowledge vectors active yet. Connect database to view.</p>
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