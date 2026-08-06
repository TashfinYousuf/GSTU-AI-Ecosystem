"use client";

import { useState, useEffect } from "react";
import { Brain, Target, Search, BookOpen, Presentation, CheckCircle, XCircle, TrendingUp } from "lucide-react";
import { createClient } from "../../utils/supabase/client";
import { fetchAPI } from "../../utils/api";

export default function ScholarHubPage() {
  const [activeTab, setActiveTab] = useState("research");
  const [input1, setInput1] = useState(""); 
  const [input2, setInput2] = useState(""); 
  const [result, setResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleAction = async (endpoint: string, payload: any) => {
    setIsLoading(true);
    setResult(null);
    
    try {
      // 🔴 Using our global fetchAPI utility
      const res = await fetchAPI(`/powerups/${endpoint}`, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      
      if (res && res.data) {
        setResult(res.data);
      } else {
        setResult({ error: "Failed to process request." });
      }
    } catch (error) {
      setResult({ error: "Network error. Please try again." });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-gray-200 p-8 md:p-12 font-sans transition-all duration-300">
      
      {/* Premium Header */}
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <Brain className="w-8 h-8 text-indigo-500" /> Advanced Scholar Hub
        </h1>
        <p className="text-gray-400 mt-2 text-[15px]">Enterprise-grade academic tools for research synthesis and critical review.</p>
      </div>

      {/* Modern Tabs */}
      <div className="flex gap-2 border-b border-white/10 mb-8 pb-px">
        <button onClick={() => { setActiveTab("research"); setResult(null); }} className={`px-6 py-3 text-sm font-semibold rounded-t-xl transition-all ${activeTab === "research" ? "text-white bg-[#1e1e1e] border-t border-l border-r border-white/10 shadow-[0_-4px_10px_rgba(0,0,0,0.2)]" : "text-gray-300 hover:text-gray-300"}`}>
          <div className="flex items-center gap-2"><BookOpen className="w-4 h-4"/> Literature & Gap Analyzer</div>
        </button>
        <button onClick={() => { setActiveTab("review"); setResult(null); }} className={`px-6 py-3 text-sm font-semibold rounded-t-xl transition-all ${activeTab === "review" ? "text-white bg-[#1e1e1e] border-t border-l border-r border-white/10 shadow-[0_-4px_10px_rgba(0,0,0,0.2)]" : "text-gray-300 hover:text-gray-300"}`}>
          <div className="flex items-center gap-2"><Presentation className="w-4 h-4"/> Critical Peer Review</div>
        </button>
      </div>

      {/* Main Content Area */}
      <div className="max-w-4xl">
        
        {/* Research Tab */}
        {activeTab === "research" && (
          <div className="bg-[#1e1e1e] border border-white/5 p-6 md:p-8 rounded-2xl shadow-xl">
            <label className="block text-sm font-medium text-gray-400 mb-3">Research Topic or Thesis Domain</label>
            <input type="text" value={input1} onChange={(e) => setInput1(e.target.value)} placeholder="e.g., Geopolitics of South Asia, Neorealism..." className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl px-5 py-4 text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all mb-6 text-[15px]" />
            <div className="flex gap-4">
              <button onClick={() => handleAction("research", { topic: input1, task_mode: "gap_hunter" })} disabled={!input1 || isLoading} className="flex-1 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3.5 rounded-xl transition-all">
                <Target className="w-4 h-4" /> Find Research Gap
              </button>
              <button onClick={() => handleAction("research", { topic: input1, task_mode: "literature_review" })} disabled={!input1 || isLoading} className="flex-1 flex items-center justify-center gap-2 bg-[#0a0a0a] hover:bg-[#333] border border-white/10 text-white font-medium py-3.5 rounded-xl transition-all">
                <Search className="w-4 h-4" /> Synthesize Literature
              </button>
            </div>
          </div>
        )}

        {/* Review Tab */}
        {activeTab === "review" && (
          <div className="bg-[#1e1e1e] border border-white/5 p-6 md:p-8 rounded-2xl shadow-xl space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-3">Concept / Question</label>
              <input type="text" value={input1} onChange={(e) => setInput1(e.target.value)} placeholder="e.g., Explain the concept of Hegemony." className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl px-5 py-4 text-white focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-all text-[15px]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-3">Your Argument / Answer</label>
              <textarea value={input2} onChange={(e) => setInput2(e.target.value)} placeholder="Write your perspective here..." rows={4} className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl px-5 py-4 text-white focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-all resize-none text-[15px]" />
            </div>
            <button onClick={() => handleAction("roast", { question: input1, answer: input2 })} disabled={!input1 || !input2 || isLoading} className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-3.5 rounded-xl transition-all">
              <CheckCircle className="w-5 h-5" /> Submit for Critical Review
            </button>
          </div>
        )}

        {/* Results Rendering Area */}
        <div className="mt-8">
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400 animate-pulse">
              <Brain className="w-12 h-12 mb-4 text-indigo-500/50 animate-bounce" />
              <p className="text-[15px] font-medium tracking-wide">Processing Academic Data...</p>
            </div>
          )}

          {result && !isLoading && !result.error && (
            <div className="animate-in fade-in slide-in-from-bottom-6">
              
              {/* Gap Hunter Result */}
              {result.the_gap && (
                <div className="space-y-6">
                  <div className="p-6 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl">
                    <h4 className="text-lg font-bold text-indigo-400 mb-3 flex items-center gap-2"><Target className="w-5 h-5"/> The Missing Gap</h4>
                    <p className="text-indigo-100 leading-relaxed text-[15.5px]">{result.the_gap}</p>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-[#1e1e1e] p-6 rounded-2xl border border-white/5">
                      <h4 className="text-[13px] font-bold text-gray-300 uppercase tracking-wider mb-4">Existing Focus</h4>
                      <ul className="space-y-3">
                        {result.existing_research_focus?.map((pt: string, i: number) => <li key={i} className="text-gray-300 text-[14.5px] flex items-start gap-3"><div className="w-1.5 h-1.5 rounded-full bg-gray-500 mt-2 shrink-0"></div> {pt}</li>)}
                      </ul>
                    </div>
                    <div className="bg-[#1e1e1e] p-6 rounded-2xl border border-white/5">
                      <h4 className="text-[13px] font-bold text-gray-300 uppercase tracking-wider mb-4">Proposed Thesis Titles</h4>
                      <ul className="space-y-3">
                        {result.proposed_thesis_titles?.map((pt: string, i: number) => <li key={i} className="p-3 bg-[#2a2a2a] border border-white/5 rounded-xl text-gray-200 text-[14.5px] font-medium leading-snug">{pt}</li>)}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Peer Review Result */}
              {result.roast_text && (
                <div className="space-y-6">
                  <div className={`p-6 border rounded-2xl ${result.is_correct ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-100' : 'bg-rose-500/10 border-rose-500/20 text-rose-100'}`}>
                    <h4 className={`text-lg font-bold mb-3 flex items-center gap-2 ${result.is_correct ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {result.is_correct ? <CheckCircle className="w-6 h-6"/> : <XCircle className="w-6 h-6"/>}
                      {result.is_correct ? 'Outstanding Analysis' : 'Critical Flaw Detected'}
                    </h4>
                    <p className="leading-relaxed text-[15.5px]">{result.roast_text}</p>
                  </div>
                  {!result.is_correct && (
                    <div className="p-6 bg-[#1e1e1e] border border-white/5 rounded-2xl">
                      <h4 className="text-[13px] font-bold text-emerald-500 uppercase tracking-wider mb-3">Correct Academic Concept</h4>
                      <p className="text-gray-300 leading-relaxed text-[15px]">{result.correct_concept}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}