"use client";

import { useState, useEffect } from "react";
import { ShieldCheck, Users, Activity, Banknote, TrendingUp, HeadphonesIcon, UploadCloud, Rocket, Bell, Headset, Loader2, Brain, MessageSquare, Clock, CheckCircle } from "lucide-react";
import { createClient } from "../../utils/supabase/client";
import { fetchAPI } from "../../utils/api";

export default function FacultyNodePage() {
  const [activeTab, setActiveTab] = useState("analytics");
  const [tickets, setTickets] = useState<any[]>([]);
  const [notices, setNotices] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // 🔴 Initialize with ZERO
  const [stats, setStats] = useState({
    total_users: 0,
    pro_users: 0,
    free_users: 0,
    active_models: 10,
    est_revenue_bdt: 0,
    trending_topics: [],
    dept_users: []
  });


  useEffect(() => {
    async function loadAdminData() {
      setIsLoading(true);
      try {
        if (activeTab === "analytics") {
          const res = await fetchAPI("/admin/analytics");
          if (res.data) setStats(res.data);
        } else if (activeTab === "support") {
          const res = await fetchAPI("/admin/tickets");
          if (res.data) setTickets(res.data);
        }
      } catch (error) {
        console.error("Failed to load admin data");
      } finally {
        setIsLoading(false);
      }
    }
    loadAdminData();
  }, [activeTab]);

  return (
    <div className="min-h-screen bg-[#121212] text-gray-200 p-8 md:p-12 font-sans overflow-y-auto custom-scrollbar">
      
      {/* Premium Header */}
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <ShieldCheck className="w-8 h-8 text-emerald-500" /> Faculty & Admin Node
        </h1>
        <p className="text-gray-400 mt-2 text-[15px]">Enterprise-grade departmental control center, analytics, and operational hub.</p>
      </div>

      {/* Modern Tabs */}
      <div className="flex gap-2 border-b border-white/10 mb-8 pb-px">
        <button onClick={() => setActiveTab("analytics")} className={`px-6 py-3 text-sm font-semibold rounded-t-xl transition-all ${activeTab === "analytics" ? "text-white bg-[#1e1e1e] border-t border-l border-r border-white/10 shadow-[0_-4px_10px_rgba(0,0,0,0.2)]" : "text-gray-500 hover:text-gray-300"}`}>
          <div className="flex items-center gap-2"><Activity className="w-4 h-4"/> Live Overview</div>
        </button>
        <button onClick={() => setActiveTab("knowledge-base")} className={`px-6 py-3 text-sm font-bold transition-all ${activeTab === "knowledge-base" ? "text-emerald-400 border-b-2 border-emerald-400" : "text-gray-500 hover:text-gray-300"}`}>📚 Knowledge Base</button>
        <button onClick={() => setActiveTab("tickets")} className={`px-6 py-3 text-sm font-semibold rounded-t-xl transition-all ${activeTab === "tickets" ? "text-white bg-[#1e1e1e] border-t border-l border-r border-white/10 shadow-[0_-4px_10px_rgba(0,0,0,0.2)]" : "text-gray-500 hover:text-gray-300"}`}>
          <div className="flex items-center gap-2"><HeadphonesIcon className="w-4 h-4"/> Support Desk {tickets.length > 0 && <span className="bg-rose-500 text-white text-[10px] px-1.5 py-0.5 rounded-full">{tickets.length}</span>}</div>
        </button>
        <button onClick={() => setActiveTab("notices")} className={`px-6 py-3 text-sm font-semibold rounded-t-xl transition-all ${activeTab === "notices" ? "text-white bg-[#1e1e1e] border-t border-l border-r border-white/10 shadow-[0_-4px_10px_rgba(0,0,0,0.2)]" : "text-gray-500 hover:text-gray-300"}`}>
          <div className="flex items-center gap-2"><Bell className="w-4 h-4"/> Notice Approvals</div>
        </button>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 text-emerald-500/50 animate-pulse">
          <ShieldCheck className="w-12 h-12 mb-4 animate-bounce" />
          <p>Decrypting Admin Vault...</p>
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
                <div className="bg-gradient-to-br from-amber-500/10 to-transparent border border-amber-500/20 p-6 rounded-2xl shadow-lg">
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

          {/* 📚 TAB 2: DYNAMIC KNOWLEDGE BASE MANAGER */}
          {activeTab === "knowledge-base" && (
            <div className="animate-in fade-in slide-in-from-bottom-4 space-y-8">
              <h3 className="text-white font-bold flex items-center gap-2 text-lg mb-6">
                📤 Upload Departmental Resources
              </h3>
              
              <div className="bg-[#1e3a8a]/20 border border-blue-500/20 p-4 rounded-xl mb-6">
                <p className="text-sm text-blue-200/80 leading-relaxed">
                  Upload syllabus, lecture notes, or past questions. The AI will automatically chunk, embed, and memorize them securely.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-2">Course Code & Version (Crucial for Version Control):</label>
                  <input type="text" placeholder="e.g., IR-210-v1" className="w-full bg-[#0b0c10] border border-emerald-500/30 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-emerald-500 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-2">Document Type:</label>
                  <select className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-emerald-500 text-sm">
                    <option>Lecture Notes</option>
                    <option>Syllabus</option>
                    <option>Past Questions</option>
                    <option>Research Paper</option>
                  </select>
                </div>
              </div>

              {/* Drag & Drop Area */}
              <div className="mb-6">
                <label className="block text-xs font-medium text-gray-400 mb-2">Drag & Drop PDFs or TXT files here</label>
                <div className="border-2 border-dashed border-white/10 rounded-xl p-10 flex flex-col items-center justify-center bg-[#0f172a] hover:bg-[#1e293b] transition-colors cursor-pointer group">
                  <button className="bg-white/5 group-hover:bg-white/10 border border-white/10 text-white px-6 py-3 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 shadow-sm">
                    <UploadCloud className="w-5 h-5" /> Upload File
                  </button>
                  <span className="text-[11px] text-gray-500 mt-4">200MB per file • PDF, TXT</span>
                </div>
              </div>

              <button className="w-full bg-[#059669] hover:bg-[#10b981] text-white font-bold py-4 rounded-xl transition-all shadow-lg flex items-center justify-center gap-2">
                <Rocket className="w-5 h-5" /> Process & Memorize (Train AI)
              </button>
            </div>
          )}

          {/* 🎧 TAB: SUPPORT DESK */}
          {activeTab === "support" && (
            <div className="bg-[#1e1e1e] border border-white/5 rounded-3xl shadow-xl p-8 animate-in fade-in min-h-[400px]">
              <h3 className="text-xl font-bold text-white mb-6">Pending Support Tickets</h3>
              
              {isLoading ? (
                <div className="flex justify-center py-10"><Loader2 className="w-8 h-8 text-rose-500 animate-spin" /></div>
              ) : Array.isArray(tickets) && tickets.length > 0 ? (
                <div className="space-y-4">
                  {tickets.map((t, i) => (
                    <div key={i} className="flex items-center justify-between p-5 bg-[#0a0a0a] border border-white/5 rounded-2xl">
                      <div>
                        <span className="text-xs font-bold text-rose-500 uppercase tracking-wider bg-rose-500/10 px-2 py-1 rounded-md mb-2 inline-block">{t.category || "Issue"}</span>
                        <p className="text-gray-300 font-medium">{t.query}</p>
                      </div>
                      <button className="px-4 py-2 bg-white/10 hover:bg-emerald-600 hover:text-white text-gray-300 rounded-lg text-sm font-bold transition-colors">Resolve</button>
                    </div>
                  ))}
                </div>
              ) : (
                // 🔴 Safe Empty State
                <div className="flex flex-col items-center justify-center py-16 text-gray-500 border border-dashed border-white/10 rounded-2xl bg-[#121212]/50 mt-4">
                  <MessageSquare className="w-16 h-16 mb-4 opacity-30 text-gray-400" />
                  <h3 className="text-xl font-bold text-gray-300 mb-2">No Active Tickets</h3>
                  <p className="text-sm text-gray-500 text-center max-w-sm">The support desk is currently clear. Any queries or issues raised by students will appear here.</p>
                </div>
              )}
            </div>
          )}

          {/* 🔔 TAB 4: PUBLISH NOTICES, ROUTINES & RESULTS */}
          {activeTab === "notices" && (
            <div className="bg-[#171923] w-full rounded-2xl shadow-2xl border border-amber-500/30 p-8 animate-in fade-in">
              <h3 className="text-white font-bold flex items-center gap-2 text-lg mb-6">
                📢 Publish Department Update
              </h3>
              
              <div className="bg-amber-500/10 border border-amber-500/20 p-4 rounded-xl mb-6">
                <p className="text-sm text-amber-200/80 leading-relaxed">
                  Upload official notices, class routines, or semester results here. This will instantly reflect on the student's Department Hub.
                </p>
              </div>

              <div className="space-y-5 mb-6">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-2">Title / Subject:</label>
                  <input type="text" placeholder="e.g., Final Exam Routine - Semester 2.1" className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-amber-500 text-sm" />
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-2">Category:</label>
                    <select className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-amber-500 text-sm">
                      <option>Official Notice</option>
                      <option>Class Routine</option>
                      <option>Semester Result</option>
                      <option>Event/Seminar</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-2">Publish Date:</label>
                    <input type="date" className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-amber-500 text-sm" />
                  </div>
                </div>
              </div>

              {/* Drag & Drop Area for PDF */}
              <div className="mb-6">
                <label className="block text-xs font-medium text-gray-400 mb-2">Attach Document (Optional but recommended)</label>
                <div className="border-2 border-dashed border-white/10 rounded-xl p-8 flex flex-col items-center justify-center bg-[#0f172a] hover:bg-[#1e293b] transition-colors cursor-pointer group">
                  <button className="bg-white/5 group-hover:bg-white/10 border border-white/10 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 shadow-sm">
                    <UploadCloud className="w-5 h-5" /> Attach PDF/Image
                  </button>
                </div>
              </div>

              <button className="w-full bg-amber-700 hover:bg-amber-600 text-white font-bold py-4 rounded-xl transition-all shadow-lg flex items-center justify-center gap-2">
                <Bell className="w-5 h-5" /> Publish to Department Hub
              </button>
            </div>
          )}

        </div>
      )}
    </div>
  );
}