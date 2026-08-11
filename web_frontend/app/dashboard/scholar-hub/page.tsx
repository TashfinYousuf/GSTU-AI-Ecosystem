"use client";

import { useState } from "react";
import { Brain, Target, Search, BookOpen, Presentation, CheckCircle, XCircle, AlertTriangle, Lightbulb } from "lucide-react";
import { fetchAPI } from "../../utils/api";

export default function ScholarHubPage() {
  const [activeTab, setActiveTab] = useState<"research" | "review">("research");
  const [taskMode, setTaskMode] = useState<"gap_hunter" | "literature_review">("gap_hunter");
  
  // Inputs
  const [topic, setTopic] = useState(""); 
  const [question, setQuestion] = useState(""); 
  const [answer, setAnswer] = useState(""); 

  const [result, setResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleAction = async (endpoint: string, payload: any) => {
    setIsLoading(true);
    setResult(null);
    
    try {
      // Using global fetchAPI which automatically handles the Bearer token
      const res = await fetchAPI(`/powerups/${endpoint}`, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      
      if (res && res.status === "success" && res.data) {
        setResult(res.data);
      } else {
        setResult({ error: res.detail || res.message || "Failed to process request. AI might be overloaded." });
      }
    } catch (error) {
      setResult({ error: "Network error. Please check your connection and try again." });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#121212] text-gray-200 p-8 md:p-12 font-sans overflow-y-auto custom-scrollbar transition-all duration-300">
      
      {/* Premium Header */}
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <Brain className="w-8 h-8 text-indigo-500" /> Advanced Scholar Hub
        </h1>
        <p className="text-gray-400 mt-2 text-[15px]">Enterprise-grade academic tools for research synthesis and critical review.</p>
      </div>

      {/* Modern Tabs */}
      <div className="flex gap-2 border-b border-white/10 mb-8 pb-px">
        <button 
          onClick={() => { setActiveTab("research"); setResult(null); }} 
          className={`px-6 py-3 text-sm font-semibold rounded-t-xl transition-all ${activeTab === "research" ? "text-white bg-[#1e1e1e] border-t border-l border-r border-white/10 shadow-[0_-4px_10px_rgba(0,0,0,0.2)]" : "text-gray-400 hover:text-gray-200"}`}
        >
          <div className="flex items-center gap-2"><BookOpen className="w-4 h-4"/> Literature & Gap Analyzer</div>
        </button>
        <button 
          onClick={() => { setActiveTab("review"); setResult(null); }} 
          className={`px-6 py-3 text-sm font-semibold rounded-t-xl transition-all ${activeTab === "review" ? "text-white bg-[#1e1e1e] border-t border-l border-r border-white/10 shadow-[0_-4px_10px_rgba(0,0,0,0.2)]" : "text-gray-400 hover:text-gray-200"}`}
        >
          <div className="flex items-center gap-2"><Presentation className="w-4 h-4"/> Critical Peer Review</div>
        </button>
      </div>

      {/* Main Content Area */}
      <div className="max-w-5xl">
        
        {/* 🔬 RESEARCH TAB */}
        {activeTab === "research" && (
          <div className="bg-[#1e1e1e] border border-white/5 p-6 md:p-8 rounded-3xl shadow-xl animate-in fade-in">
            
            {/* Task Selectors */}
            <div className="flex flex-col md:flex-row gap-4 mb-6">
              <button 
                onClick={() => setTaskMode("gap_hunter")}
                className={`flex-1 py-4 rounded-xl font-bold transition-all border ${taskMode === "gap_hunter" ? "bg-indigo-600/20 border-indigo-500 text-indigo-400" : "bg-[#0a0a0a] border-white/10 text-gray-400 hover:bg-white/5"}`}
              >
                <Target className="inline w-5 h-5 mr-2" /> Research Gap Hunter
              </button>
              <button 
                onClick={() => setTaskMode("literature_review")}
                className={`flex-1 py-4 rounded-xl font-bold transition-all border ${taskMode === "literature_review" ? "bg-blue-600/20 border-blue-500 text-blue-400" : "bg-[#0a0a0a] border-white/10 text-gray-400 hover:bg-white/5"}`}
              >
                <Search className="inline w-5 h-5 mr-2" /> Literature Review
              </button>
            </div>

            <label className="block text-sm font-medium text-gray-400 mb-3 uppercase tracking-wider">Research Topic or Thesis Domain</label>
            <div className="flex flex-col md:flex-row gap-4">
              <input 
                type="text" 
                value={topic} 
                onChange={(e) => setTopic(e.target.value)} 
                placeholder="e.g., Neorealism in South Asia, The Blue Economy..." 
                className="flex-1 bg-[#0a0a0a] border border-white/10 rounded-2xl px-5 py-4 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all text-[15px]" 
              />
              <button 
                onClick={() => handleAction("research", { topic: topic, task_mode: taskMode })} 
                disabled={!topic || isLoading} 
                className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold px-10 py-4 rounded-2xl transition-all shadow-lg shrink-0"
              >
                {isLoading ? "Analyzing..." : "Execute OS 🚀"}
              </button>
            </div>
          </div>
        )}

        {/* 👁️ REVIEW TAB (Savage Roast) */}
        {activeTab === "review" && (
          <div className="bg-[#1e1e1e] border border-white/5 p-6 md:p-8 rounded-3xl shadow-xl space-y-6 animate-in fade-in">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2 uppercase tracking-wider">Concept / Question</label>
              <input 
                type="text" 
                value={question} 
                onChange={(e) => setQuestion(e.target.value)} 
                placeholder="e.g., Explain the concept of Hegemonic Stability Theory." 
                className="w-full bg-[#0a0a0a] border border-white/10 rounded-2xl px-5 py-4 text-white focus:outline-none focus:ring-2 focus:ring-rose-500 transition-all text-[15px]" 
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2 uppercase tracking-wider">Your Argument / Answer</label>
              <textarea 
                value={answer} 
                onChange={(e) => setAnswer(e.target.value)} 
                placeholder="Write your perspective here..." 
                rows={4} 
                className="w-full bg-[#0a0a0a] border border-white/10 rounded-2xl px-5 py-4 text-white focus:outline-none focus:ring-2 focus:ring-rose-500 transition-all resize-none text-[15px]" 
              />
            </div>
            <button 
              onClick={() => handleAction("roast", { question: question, answer: answer })} 
              disabled={!question || !answer || isLoading} 
              className="w-full flex items-center justify-center gap-2 bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white font-bold py-4 rounded-2xl transition-all shadow-lg"
            >
              {isLoading ? "Summoning Professor..." : <><CheckCircle className="w-5 h-5" /> Submit for Critical Review</>}
            </button>
          </div>
        )}

        {/* =========================================
            RESULTS RENDERING AREA (Dynamic Logic) 
            ========================================= */}
        <div className="mt-8">
          
          {/* Loading State */}
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400 animate-pulse bg-[#1e1e1e] border border-white/5 rounded-3xl">
              <Brain className="w-14 h-14 mb-4 text-indigo-500/50 animate-bounce" />
              <p className="text-[16px] font-bold tracking-wider uppercase text-indigo-400/80">Processing High-Level Academic Data...</p>
            </div>
          )}

          {/* Error State */}
          {result?.error && (
            <div className="bg-rose-500/10 border border-rose-500/30 text-rose-400 p-6 rounded-2xl flex items-center gap-3 font-medium animate-in fade-in">
              <AlertTriangle className="w-6 h-6 shrink-0" />
              <p>{result.error}</p>
            </div>
          )}

          {/* Success States */}
          {result && !isLoading && !result.error && (
            <div className="animate-in fade-in slide-in-from-bottom-6">
              
              {/* 🎯 GAP HUNTER OUTPUT */}
              {result.the_gap && (
                <div className="space-y-6">
                  <div className="p-8 bg-gradient-to-br from-indigo-500/10 to-[#1e1e1e] border border-indigo-500/30 rounded-3xl shadow-xl">
                    <h4 className="text-xl font-bold text-indigo-400 mb-4 flex items-center gap-3"><Target className="w-6 h-6"/> The Missing Gap</h4>
                    <p className="text-gray-200 leading-relaxed text-[16px]">{result.the_gap}</p>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-[#1e1e1e] p-8 rounded-3xl border border-white/5 shadow-lg">
                      <h4 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">Existing Focus</h4>
                      <ul className="space-y-4">
                        {result.existing_research_focus?.map((pt: string, i: number) => (
                          <li key={i} className="text-gray-300 text-[14.5px] flex items-start gap-3">
                            <div className="w-2 h-2 rounded-full bg-indigo-500 mt-2 shrink-0 shadow-[0_0_8px_#6366f1]"></div> {pt}
                          </li>
                        ))}
                      </ul>
                    </div>
                    
                    <div className="bg-[#1e1e1e] p-8 rounded-3xl border border-white/5 shadow-lg">
                      <h4 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2"><Lightbulb className="w-4 h-4 text-amber-400"/> Proposed Thesis Titles</h4>
                      <ul className="space-y-4">
                        {result.proposed_thesis_titles?.map((pt: string, i: number) => (
                          <li key={i} className="p-4 bg-[#0a0a0a] border border-white/10 hover:border-amber-500/30 rounded-xl text-emerald-400 text-[15px] font-bold leading-snug transition-colors">
                            {pt}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* 📚 LITERATURE REVIEW OUTPUT */}
              {result.main_arguments && (
                <div className="space-y-6">
                  <div className="bg-[#1e1e1e] p-8 rounded-3xl border border-white/5 shadow-xl">
                    <h4 className="text-xl font-bold text-blue-400 mb-6 flex items-center gap-3"><BookOpen className="w-6 h-6"/> Main Arguments Synthesized</h4>
                    <ul className="space-y-4">
                      {result.main_arguments?.map((pt: string, i: number) => (
                        <li key={i} className="text-gray-300 text-[15px] flex items-start gap-3">
                          <div className="w-2 h-2 rounded-full bg-blue-500 mt-2 shrink-0"></div> {pt}
                        </li>
                      ))}
                    </ul>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-emerald-500/10 border border-emerald-500/20 p-8 rounded-3xl shadow-lg">
                      <h4 className="text-lg font-bold text-emerald-400 mb-4 flex items-center gap-2">🤝 Areas of Agreement</h4>
                      <p className="text-gray-200 text-[15px] leading-relaxed">{result.areas_of_agreement}</p>
                    </div>
                    <div className="bg-rose-500/10 border border-rose-500/20 p-8 rounded-3xl shadow-lg">
                      <h4 className="text-lg font-bold text-rose-400 mb-4 flex items-center gap-2">⚔️ Areas of Disagreement</h4>
                      <p className="text-gray-200 text-[15px] leading-relaxed">{result.areas_of_disagreement}</p>
                    </div>
                  </div>
                  
                  <div className="bg-[#0a0a0a] p-6 rounded-2xl border border-white/10 flex flex-wrap items-center gap-3">
                    <span className="font-bold text-gray-500 uppercase tracking-widest text-sm">Key Scholars: </span>
                    {result.key_scholars?.map((scholar: string, i: number) => (
                      <span key={i} className="px-4 py-1.5 bg-blue-500/10 text-blue-300 border border-blue-500/20 rounded-full text-sm font-bold">{scholar}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* 👁️ PEER REVIEW (ROAST) OUTPUT */}
              {result.roast_text && (
                <div className="space-y-6 max-w-3xl mx-auto">
                  <div className={`p-8 border rounded-3xl shadow-2xl ${result.is_correct ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-[#171717] border-rose-500/40'}`}>
                    <h4 className={`text-2xl font-bold mb-6 flex items-center gap-3 ${result.is_correct ? 'text-emerald-400' : 'text-rose-500'}`}>
                      {result.is_correct ? <CheckCircle className="w-8 h-8"/> : <XCircle className="w-8 h-8"/>}
                      {result.is_correct ? 'Outstanding Analysis' : 'Critical Flaw Detected 🔥'}
                    </h4>
                    <p className={`leading-relaxed text-[16px] ${result.is_correct ? 'text-emerald-100' : 'text-rose-200 italic'}`}>"{result.roast_text}"</p>
                  </div>
                  
                  {!result.is_correct && (
                    <div className="p-8 bg-[#1e1e1e] border border-white/10 rounded-3xl shadow-lg relative overflow-hidden">
                      <div className="absolute top-0 left-0 w-2 h-full bg-emerald-500"></div>
                      <h4 className="text-[13px] font-bold text-gray-400 uppercase tracking-widest mb-4">The Correct Academic Concept</h4>
                      <p className="text-gray-200 leading-relaxed text-[15.5px] font-medium">{result.correct_concept}</p>
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