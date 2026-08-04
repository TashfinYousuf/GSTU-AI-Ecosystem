"use client";

import { useState, useEffect } from "react";
import { Building2, Bell, BookOpen, Calendar, GraduationCap, Image as ImageIcon, FileText, Download, Search, Loader2 } from "lucide-react";
import { fetchAPI } from "../../utils/api";

export default function DepartmentHubPage() {
  const [activeTab, setActiveTab] = useState("notices"); 
  const [searchQuery, setSearchQuery] = useState("");
  
  // 🔴 Dynamic States
  const [notices, setNotices] = useState<any[]>([]);
  const [syllabus, setSyllabus] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // 🔴 Data Fetching Hook
  useEffect(() => {
    async function fetchDepartmentData() {
      setIsLoading(true);
      try {
        if (activeTab === "notices" && notices.length === 0) {
          const res = await fetchAPI("/department/notices");
          setNotices(res.data || []);
        } else if (activeTab === "syllabus" && syllabus.length === 0) {
          const res = await fetchAPI("/department/syllabus");
          setSyllabus(res.data || []);
        }
      } catch (error) {
        console.error("Error fetching department data:", error);
      } finally {
        setIsLoading(false);
      }
    }
    
    fetchDepartmentData();
  }, [activeTab]);

  return (
    <div className="flex flex-col h-screen bg-[#121212] overflow-y-auto custom-scrollbar p-8 md:p-12">
      <div className="max-w-6xl mx-auto w-full animate-in fade-in slide-in-from-bottom-4 pt-4">
        
        {/* Header */}
        <div className="mb-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
              <Building2 className="w-8 h-8 text-blue-500" /> Department Hub
            </h1>
            <p className="text-gray-400 mt-2 text-[15px]">The central digital ecosystem for International Relations, GSTU.</p>
          </div>
          
          <div className="relative w-full md:w-72 shrink-0">
            <Search className="w-4 h-4 text-gray-500 absolute left-3 top-3.5" />
            <input 
              type="text" 
              placeholder="Search notices, syllabus..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#1e1e1e] border border-white/10 rounded-xl py-3 pl-10 pr-4 text-white focus:outline-none focus:border-blue-500 text-sm transition-colors"
            />
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex flex-wrap gap-2 border-b border-white/10 mb-8 pb-4">
          <button onClick={() => setActiveTab("notices")} className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all flex items-center gap-2 ${activeTab === "notices" ? "bg-blue-500/20 text-blue-400 border border-blue-500/30" : "bg-[#1e1e1e] text-gray-400 hover:text-white"}`}><Bell className="w-4 h-4"/> Notices</button>
          <button onClick={() => setActiveTab("syllabus")} className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all flex items-center gap-2 ${activeTab === "syllabus" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-[#1e1e1e] text-gray-400 hover:text-white"}`}><BookOpen className="w-4 h-4"/> Syllabus</button>
          <button onClick={() => setActiveTab("routines")} className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all flex items-center gap-2 ${activeTab === "routines" ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30" : "bg-[#1e1e1e] text-gray-400 hover:text-white"}`}><Calendar className="w-4 h-4"/> Routines</button>
          <button onClick={() => setActiveTab("results")} className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all flex items-center gap-2 ${activeTab === "results" ? "bg-amber-500/20 text-amber-400 border border-amber-500/30" : "bg-[#1e1e1e] text-gray-400 hover:text-white"}`}><GraduationCap className="w-4 h-4"/> Results</button>
          <button onClick={() => setActiveTab("gallery")} className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all flex items-center gap-2 ${activeTab === "gallery" ? "bg-rose-500/20 text-rose-400 border border-rose-500/30" : "bg-[#1e1e1e] text-gray-400 hover:text-white"}`}><ImageIcon className="w-4 h-4"/> Gallery</button>
        </div>

        {/* 🔔 TAB 1: NOTICES */}
        {activeTab === "notices" && (
          <div className="space-y-4 animate-in fade-in">
            {isLoading ? (
              <div className="flex justify-center py-10"><Loader2 className="w-8 h-8 text-blue-500 animate-spin" /></div>
            ) : notices.filter(n => n.title.toLowerCase().includes(searchQuery.toLowerCase())).map((notice) => (
              <div key={notice.id} className="bg-[#1e1e1e] border border-white/5 hover:border-blue-500/30 p-5 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all group cursor-pointer">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <h3 className="text-white font-semibold text-lg group-hover:text-blue-400 transition-colors">{notice.title}</h3>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-gray-500 bg-black/50 px-2 py-1 rounded-md">{notice.date}</span>
                      <span className={`text-[10px] uppercase font-bold px-2 py-1 rounded-md ${notice.type === 'Academic' ? 'bg-emerald-500/10 text-emerald-400' : notice.type === 'Event' ? 'bg-amber-500/10 text-amber-400' : 'bg-rose-500/10 text-rose-400'}`}>{notice.type}</span>
                    </div>
                  </div>
                </div>
                <button className="text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 p-2.5 rounded-xl transition-colors shrink-0 flex items-center gap-2 text-sm font-medium">
                  <Download className="w-4 h-4" /> Download PDF
                </button>
              </div>
            ))}
          </div>
        )}

        {/* 📚 TAB 2: SYLLABUS */}
        {activeTab === "syllabus" && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-in fade-in">
            {syllabus.map((course, idx) => (
              <div key={idx} className="bg-[#1e1e1e] border border-white/5 hover:border-emerald-500/30 p-6 rounded-2xl transition-all group">
                <div className="flex justify-between items-start mb-4">
                  <span className="bg-emerald-500/10 text-emerald-400 text-xs font-bold px-3 py-1.5 rounded-lg">{course.code}</span>
                  <span className="text-gray-500 text-xs font-medium">{course.credits} Credits</span>
                </div>
                <h3 className="text-white font-bold text-lg mb-6 leading-snug">{course.title}</h3>
                <div className="flex gap-2">
                  <button className="flex-1 bg-white/5 hover:bg-white/10 text-white text-sm font-medium py-2.5 rounded-xl transition-colors flex items-center justify-center gap-2">
                    <BookOpen className="w-4 h-4"/> View
                  </button>
                  <button className="bg-white/5 hover:bg-emerald-500/20 hover:text-emerald-400 text-gray-400 p-2.5 rounded-xl transition-colors">
                    <Download className="w-4 h-4"/>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Other Tabs Placeholder */}
        {(activeTab === "routines" || activeTab === "results" || activeTab === "gallery") && (
          <div className="flex flex-col items-center justify-center py-32 text-gray-500 border-2 border-dashed border-white/5 rounded-3xl animate-in fade-in">
            <Building2 className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-lg font-medium text-gray-400">Database Integration Pending</p>
            <p className="text-sm mt-1">This module will be connected to the GSTU backend securely.</p>
          </div>
        )}

      </div>
    </div>
  );
}