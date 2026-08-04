"use client";

import { useState, useEffect } from "react";
import { ShieldCheck, Users, Activity, Banknote, TrendingUp, HeadphonesIcon, UploadCloud, Rocket, Bell, CheckCircle, Clock, Brain } from "lucide-react";
import { createClient } from "../../utils/supabase/client";

export default function FacultyNodePage() {
  const [activeTab, setActiveTab] = useState("analytics");
  const [stats, setStats] = useState<any>(null);
  const [tickets, setTickets] = useState<any[]>([]);
  const [notices, setNotices] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // API থেকে ডেটা ফেচ করার লজিক (আপাতত মক ডেটা সেট করছি ডেমোর জন্য)
    setTimeout(() => {
      setStats({
        total_users: 1250, pro_users: 340, free_users: 910, active_models: 10, est_revenue_bdt: 33660,
        trending_topics: [{ topic: "Neorealism vs Liberalism", count: 450 }, { topic: "South Asian Geopolitics", count: 320 }],
        dept_users: [{ dept: "IR", count: 850 }, { dept: "Economics", count: 250 }]
      });
      setTickets([
        { id: "t1", user_email: "fahim.ir@gstu.edu", query: "bKash payment failed, TrxID: 8X9Y...", status: "Open", time: "10 mins ago" },
        { id: "t2", user_email: "samia@gstu.edu", query: "Scholar Hub not generating gaps.", status: "Open", time: "1 hour ago" }
      ]);
      setNotices([
        { id: "n1", title: "Makeup Class for IR-202", content: "Tomorrow at 10 AM in Room 302.", submitted_by: "CR (IR 2.1)" }
      ]);
      setIsLoading(false);
    }, 1000);
  }, []);

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

          {/* 📚 TAB 2: DYNAMIC KNOWLEDGE BASE MANAGER (Your Screenshot) */}
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

              <button className="w-full bg-[#10b981] hover:bg-[#059669] text-white font-bold py-4 rounded-xl transition-all shadow-lg flex items-center justify-center gap-2">
                <Rocket className="w-5 h-5" /> Process & Memorize (Train AI)
              </button>
            </div>
          )}

          {/* 🎧 Tab 3: Support Tickets */}
          {activeTab === "tickets" && (
            <div className="animate-in fade-in slide-in-from-bottom-4 space-y-4">
              {tickets.length === 0 ? (
                <div className="text-center py-10 text-gray-500">No pending support tickets. Great job!</div>
              ) : (
                tickets.map((t) => (
                  <div key={t.id} className="bg-[#1e1e1e] border border-rose-500/20 p-6 rounded-2xl shadow-lg relative overflow-hidden group">
                    <div className="absolute top-0 left-0 w-1 h-full bg-rose-500"></div>
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <span className="text-xs font-bold text-gray-500 uppercase tracking-wider flex items-center gap-2 mb-1"><Clock className="w-3.5 h-3.5"/> {t.time}</span>
                        <h4 className="text-gray-200 font-medium text-[15px]">{t.user_email}</h4>
                      </div>
                      <span className="bg-rose-500/10 text-rose-400 text-[10px] font-bold uppercase px-2 py-1 rounded-full border border-rose-500/20">Open Ticket</span>
                    </div>
                    <div className="p-4 bg-[#0a0a0a] rounded-xl border border-white/5 text-gray-300 text-sm mb-4 leading-relaxed">
                      {t.query}
                    </div>
                    <button className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2.5 rounded-xl transition-all text-sm">
                      <CheckCircle className="w-4 h-4" /> Mark as Resolved & Close
                    </button>
                  </div>
                ))
              )}
            </div>
          )}

          {/* 🔔 Tab 4: Notice Approvals */}
          {activeTab === "notices" && (
            <div className="animate-in fade-in slide-in-from-bottom-4 space-y-4">
               {notices.length === 0 ? (
                <div className="text-center py-10 text-gray-500">No drafted notices pending approval.</div>
              ) : (
                notices.map((n) => (
                  <div key={n.id} className="bg-[#1e1e1e] border border-amber-500/20 p-6 rounded-2xl shadow-lg relative overflow-hidden group">
                    <div className="absolute top-0 left-0 w-1 h-full bg-amber-500"></div>
                    <h4 className="text-lg font-bold text-white mb-2">{n.title}</h4>
                    <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">Drafted By: <span className="text-amber-400">{n.submitted_by}</span></p>
                    <div className="p-4 bg-[#0a0a0a] rounded-xl border border-white/5 text-gray-300 text-sm mb-4 leading-relaxed">
                      {n.content}
                    </div>
                    <button className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4 py-2.5 rounded-xl transition-all text-sm">
                      <Bell className="w-4 h-4" /> Approve & Publish Globally
                    </button>
                  </div>
                ))
              )}
            </div>
          )}

        </div>
      )}
    </div>
  );
}