"use client";

import { useState } from "react";
import { Sparkles, Clock, Brain, CheckSquare, Bell, Calendar, FileText } from "lucide-react";
import { createClient } from "../../utils/supabase/client";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function AcademicCopilotPage() {
  const [activeTab, setActiveTab] = useState("routine");
  const [inputTopic, setInputTopic] = useState("");
  const [studyHours, setStudyHours] = useState(4); // Only for Routine
  const [result, setResult] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleCopilotAction = async (endpoint: string, payload: any) => {
    setIsLoading(true);
    setResult(null);
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    
    if (session?.access_token) {
      try {
        const res = await fetch(`http://localhost:8000/api/v1/academic/${endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${session.access_token}` },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          const data = await res.json();
          setResult(data.result);
        } else {
          setResult("❌ Failed to process request. Please try again.");
        }
      } catch (error) {
        setResult("❌ Network error. Ensure the backend is running.");
      } finally {
        setIsLoading(false);
      }
    }
  };

  const executeTask = () => {
    const payload: any = { workspace_id: "global", topic: inputTopic };
    
    if (activeTab === "routine") {
      handleCopilotAction("routine", { workspace_id: "global", study_hours: studyHours, focus_areas: [inputTopic] });
    } else if (activeTab === "exam") {
      handleCopilotAction("mock-exam", { ...payload, difficulty: "University Level" });
    } else if (activeTab === "rubric") {
      handleCopilotAction("generate", { ...payload, task_type: "rubric" });
    } else if (activeTab === "notice") {
      handleCopilotAction("notice", { raw_text: inputTopic });
    }
  };

  return (
    <div className="min-h-screen bg-[#121212] text-gray-200 p-8 md:p-12 font-sans transition-all duration-300">
      
      {/* Premium Header */}
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <Sparkles className="w-8 h-8 text-amber-500" /> Academic Copilot
        </h1>
        <p className="text-gray-400 mt-2 text-[15px]">Your automated assistant for study planning, assessments, and academic administration.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: Controls & Inputs */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* Tools Menu */}
          <div className="bg-[#1e1e1e] border border-white/5 rounded-2xl overflow-hidden shadow-xl p-2">
            <div className="px-4 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Select Tool</div>
            <div className="space-y-1">
              <button onClick={() => { setActiveTab("routine"); setResult(null); }} className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all ${activeTab === "routine" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
                <Calendar className="w-4 h-4" /> Smart Study Routine
              </button>
              <button onClick={() => { setActiveTab("exam"); setResult(null); }} className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all ${activeTab === "exam" ? "bg-purple-500/10 text-purple-400 border border-purple-500/20" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
                <Brain className="w-4 h-4" /> Mock Exam Generator
              </button>
              <button onClick={() => { setActiveTab("rubric"); setResult(null); }} className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all ${activeTab === "rubric" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
                <CheckSquare className="w-4 h-4" /> Grading Rubric
              </button>
              <button onClick={() => { setActiveTab("notice"); setResult(null); }} className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all ${activeTab === "notice" ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
                <Bell className="w-4 h-4" /> Formal Notice Engine
              </button>
            </div>
          </div>

          {/* Input Area */}
          <div className="bg-[#1e1e1e] border border-white/5 rounded-2xl p-6 shadow-xl">
            <label className="block text-sm font-medium text-gray-400 mb-3">
              {activeTab === "notice" ? "Raw Instruction (Banglish/Casual)" : "Focus Topic or Subject"}
            </label>
            
            {activeTab === "notice" ? (
              <textarea value={inputTopic} onChange={(e) => setInputTopic(e.target.value)} placeholder="e.g., Kal class hobe na, next week e makeup nite bolben..." rows={4} className="w-full bg-[#121212] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-1 focus:ring-amber-500 transition-all resize-none mb-4 text-[15px]" />
            ) : (
              <input type="text" value={inputTopic} onChange={(e) => setInputTopic(e.target.value)} placeholder="e.g., Foreign Policy of Bangladesh" className="w-full bg-[#121212] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-1 focus:ring-amber-500 transition-all mb-4 text-[15px]" />
            )}

            {activeTab === "routine" && (
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-400 mb-3 flex items-center justify-between">
                  <span>Target Study Hours</span> <span className="text-amber-400 font-bold">{studyHours} hrs</span>
                </label>
                <input type="range" min="1" max="10" value={studyHours} onChange={(e) => setStudyHours(parseInt(e.target.value))} className="w-full accent-amber-500" />
              </div>
            )}

            <button onClick={executeTask} disabled={!inputTopic || isLoading} className="w-full flex items-center justify-center gap-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-medium py-3.5 rounded-xl transition-all">
              <Sparkles className="w-5 h-5" /> Generate Now
            </button>
          </div>
        </div>

        {/* Right Column: Results Output */}
        <div className="lg:col-span-8">
          <div className="bg-[#1e1e1e] border border-white/5 rounded-2xl p-8 shadow-xl min-h-[500px] flex flex-col relative">
            
            {!isLoading && !result && (
              <div className="flex-1 flex flex-col items-center justify-center text-gray-500 opacity-70">
                <FileText className="w-16 h-16 mb-4" />
                <p className="text-[15px]">Select a tool and enter a topic to generate content.</p>
              </div>
            )}

            {isLoading && (
              <div className="flex-1 flex flex-col items-center justify-center text-gray-400 animate-pulse">
                <Sparkles className="w-12 h-12 mb-4 text-amber-500/50 animate-bounce" />
                <p className="text-[15px] font-medium tracking-wide">Copilot is drafting...</p>
              </div>
            )}

            {result && !isLoading && (
              <div className="animate-in fade-in slide-in-from-bottom-6">
                <h3 className="text-[13px] font-bold text-gray-500 uppercase tracking-wider mb-6 flex items-center justify-between border-b border-white/10 pb-4">
                  <span>Generated Output</span>
                  <button onClick={() => navigator.clipboard.writeText(result)} className="text-amber-400 hover:text-amber-300 normal-case font-medium">Copy Text</button>
                </h3>
                
                {/* Premium Markdown Renderer for Output */}
                <div className="text-gray-200 text-[15.5px] leading-relaxed">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({node, ...props}) => <p className="mb-4 last:mb-0" {...props} />,
                      strong: ({node, ...props}) => <strong className="font-semibold text-white" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc pl-6 mb-4 space-y-2 marker:text-amber-500" {...props} />,
                      ol: ({node, ...props}) => <ol className="list-decimal pl-6 mb-4 space-y-2 marker:text-amber-500" {...props} />,
                      h1: ({node, ...props}) => <h1 className="text-2xl font-bold mb-4 mt-6 text-white" {...props} />,
                      h2: ({node, ...props}) => <h2 className="text-xl font-bold mb-3 mt-5 text-amber-400" {...props} />,
                      h3: ({node, ...props}) => <h3 className="text-lg font-bold mb-3 mt-4 text-white" {...props} />,
                    }}
                  >
                    {result}
                  </ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}