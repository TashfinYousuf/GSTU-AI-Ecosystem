"use client";

import { useState, useEffect } from "react";
import { ShieldCheck, Users, Ticket, Database, FileSignature, Loader2, CheckCircle } from "lucide-react";
import { fetchAPI } from "../../utils/api";

export default function FacultyNodePage() {
  const [activeTab, setActiveTab] = useState("overview"); // overview, assessment, support
  
  // 🔴 Dynamic States
  const [stats, setStats] = useState({ active_students: 0, open_tickets: 0, knowledge_base_size: 0 });
  const [tickets, setTickets] = useState<any[]>([]);
  const [isLoadingStats, setIsLoadingStats] = useState(true);

  // Assessment States
  const [topic, setTopic] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [assessment, setAssessment] = useState<any>(null);

  // Fetch Stats & Tickets
  useEffect(() => {
    async function loadFacultyData() {
      if (activeTab === "overview") {
        setIsLoadingStats(true);
        try {
          const res = await fetchAPI("/faculty/overview");
          if (res.data) setStats(res.data);
        } catch (e) {} finally { setIsLoadingStats(false); }
      } else if (activeTab === "support") {
        try {
          const res = await fetchAPI("/faculty/tickets");
          if (res.data) setTickets(res.data);
        } catch (e) {}
      }
    }
    loadFacultyData();
  }, [activeTab]);

  const handleGenerateExam = async () => {
    setIsGenerating(true); setAssessment(null);
    try {
      const res = await fetchAPI("/faculty/assessment", { method: "POST", body: JSON.stringify({ topic }) });
      if (res.data) setAssessment(res.data);
    } catch (error) {
      alert("Failed to generate assessment. Ensure you have Faculty clearance.");
    } finally { setIsGenerating(false); }
  };

  return (
    <div className="flex flex-col h-screen bg-[#121212] overflow-y-auto custom-scrollbar p-8 md:p-12">
      <div className="max-w-6xl mx-auto w-full animate-in fade-in slide-in-from-bottom-4 pt-4">
        
        {/* Header */}
        <div className="mb-10">
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <ShieldCheck className="w-8 h-8 text-blue-500" /> Faculty Node
          </h1>
          <p className="text-gray-400 mt-2 text-[15px]">Advanced Control Center for Assessment and Department Management.</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 border-b border-white/10 mb-8 pb-px">
          <button onClick={() => setActiveTab("overview")} className={`px-6 py-3 text-sm font-bold transition-all ${activeTab === "overview" ? "text-blue-400 border-b-2 border-blue-400" : "text-gray-500 hover:text-gray-300"}`}>📊 Live Overview</button>
          <button onClick={() => setActiveTab("assessment")} className={`px-6 py-3 text-sm font-bold transition-all ${activeTab === "assessment" ? "text-indigo-400 border-b-2 border-indigo-400" : "text-gray-500 hover:text-gray-300"}`}>📝 Assessment Generator</button>
          <button onClick={() => setActiveTab("support")} className={`px-6 py-3 text-sm font-bold transition-all ${activeTab === "support" ? "text-rose-400 border-b-2 border-rose-400" : "text-gray-500 hover:text-gray-300"}`}>🎧 Support Desk</button>
        </div>

        {/* 📊 TAB 1: OVERVIEW */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-in fade-in">
            <div className="bg-[#1e1e1e] border border-white/5 p-8 rounded-3xl shadow-xl flex items-center gap-6">
              <div className="w-16 h-16 rounded-full bg-blue-500/10 flex items-center justify-center shrink-0">
                <Users className="w-8 h-8 text-blue-500" />
              </div>
              <div>
                <p className="text-sm font-bold text-gray-500 uppercase tracking-wider">Active Students</p>
                <h3 className="text-3xl font-black text-white mt-1">{isLoadingStats ? "..." : stats.active_students}</h3>
              </div>
            </div>
            <div className="bg-[#1e1e1e] border border-white/5 p-8 rounded-3xl shadow-xl flex items-center gap-6">
              <div className="w-16 h-16 rounded-full bg-rose-500/10 flex items-center justify-center shrink-0">
                <Ticket className="w-8 h-8 text-rose-500" />
              </div>
              <div>
                <p className="text-sm font-bold text-gray-500 uppercase tracking-wider">Open Tickets</p>
                <h3 className="text-3xl font-black text-white mt-1">{isLoadingStats ? "..." : stats.open_tickets}</h3>
              </div>
            </div>
            <div className="bg-[#1e1e1e] border border-white/5 p-8 rounded-3xl shadow-xl flex items-center gap-6">
              <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center shrink-0">
                <Database className="w-8 h-8 text-emerald-500" />
              </div>
              <div>
                <p className="text-sm font-bold text-gray-500 uppercase tracking-wider">Knowledge Base</p>
                <h3 className="text-3xl font-black text-white mt-1">{isLoadingStats ? "..." : stats.knowledge_base_size} <span className="text-sm text-gray-500 font-medium">Docs</span></h3>
              </div>
            </div>
          </div>
        )}

        {/* 📝 TAB 2: ASSESSMENT GENERATOR */}
        {activeTab === "assessment" && (
          <div className="bg-white text-black rounded-xl p-10 shadow-2xl animate-in zoom-in-95 font-serif border border-gray-200">
             <div className="text-center border-b-2 border-black pb-6 mb-6">
               <h2 className="text-2xl font-black uppercase tracking-widest">Department of International Relations</h2>
               <h3 className="text-lg font-bold mt-2 text-gray-700">{assessment.assessment_type || "Mock Exam"}</h3>
               <p className="text-sm text-gray-500 mt-2 font-sans">{assessment.exam_rules || "Time: 3 Hours | Full Marks: 60"}</p>
             </div>

             <div className="space-y-8">
                {assessment.questions?.map((q: any, i: number) => (
                  <div key={i} className="flex gap-4">
                    <span className="font-bold text-lg">{i + 1}.</span>
                    <div className="flex-1">
                      <p className="text-[16px] font-medium leading-relaxed">{q.q}</p>
                      <div className="mt-3 flex gap-2 font-sans">
                        <span className={`text-[10px] font-bold px-2 py-1 rounded uppercase tracking-wider ${q.difficulty === 'Critical' ? 'bg-red-100 text-red-700' : q.difficulty === 'Medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'}`}>
                          {q.difficulty}
                        </span>
                      </div>
                      {/* Only visible to Faculty */}
                      <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-100 font-sans">
                        <span className="text-xs font-bold text-blue-600 uppercase">Model Answer / Key Points:</span>
                        <p className="text-sm text-gray-600 mt-1">{q.model_answer}</p>
                      </div>
                    </div>
                  </div>
                ))}
             </div>
          </div>
        )}

        {/* 🎧 TAB 3: SUPPORT DESK */}
        {activeTab === "support" && (
          <div className="bg-[#1e1e1e] border border-white/5 rounded-3xl shadow-xl p-8 animate-in fade-in min-h-[400px]">
             <h3 className="text-xl font-bold text-white mb-6">Pending Support Tickets</h3>
             {tickets.length > 0 ? (
               <div className="space-y-4">
                 {tickets.map((t, i) => (
                   <div key={i} className="flex items-center justify-between p-5 bg-[#0a0a0a] border border-white/5 rounded-2xl">
                     <div>
                       <span className="text-xs font-bold text-rose-500 uppercase tracking-wider bg-rose-500/10 px-2 py-1 rounded-md mb-2 inline-block">{t.category || "Issue"}</span>
                       <p className="text-gray-300 font-medium">{t.query}</p>
                     </div>
                     <button className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm font-bold transition-colors">Resolve</button>
                   </div>
                 ))}
               </div>
             ) : (
               <div className="text-center text-gray-500 py-10">
                 <CheckCircle className="w-12 h-12 mx-auto mb-4 opacity-20" />
                 <p>All clear! No pending support tickets.</p>
               </div>
             )}
          </div>
        )}

      </div>
    </div>
  );
}