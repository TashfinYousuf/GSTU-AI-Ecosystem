"use client";

import { useState, useEffect } from "react";
import { Sparkles, Clock, Brain, CheckSquare, Bell, Calendar, FileText, Target, ChevronDown, RefreshCw } from "lucide-react";
import { createClient } from "../../utils/supabase/client";
import { fetchAPI } from "../../utils/api";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function AcademicCopilotPage() {
  const [activeTab, setActiveTab] = useState("routine");
  
  const [userRole, setUserRole] = useState("student");
  const [isCheckingAccess, setIsCheckingAccess] = useState(true);

  // 🔴 Input States
  const [inputTopic, setInputTopic] = useState("");
  const [studentContent, setStudentContent] = useState(""); // Missing state added for Academic grading/notices
  const [studyHours, setStudyHours] = useState(4);
  const [isLoading, setIsLoading] = useState(false);

  // 🔴 Output States
  const [result, setResult] = useState<string | null>(null);
  const [routineData, setRoutineData] = useState<any>(null);
  const [assessmentData, setAssessmentData] = useState<any>(null);

  // Toggles for Mock Exam
  const [expandedHints, setExpandedHints] = useState<{ [key: number]: boolean }>({});
  const [expandedAnswers, setExpandedAnswers] = useState<{ [key: number]: boolean }>({});

  // 🔴 On Mount: Fetch Existing Routine
  useEffect(() => {
    const fetchSavedRoutine = async () => {
      try {
        const res = await fetchAPI("/study/routine", { method: "GET" });
        if (res.data && res.data.routine_data) {
          setRoutineData(res.data.routine_data);
        }
      } catch (e) {
        console.log("No saved routine found.");
      }
    };
    fetchSavedRoutine();
  }, []);

  // 🔴 Safe Execution & State Routing
  const executeTask = async () => {
    
    // 1. Dynamic Data Validation Based on Active Tab
    if (activeTab === "routine" || activeTab === "exam") {
      if (!inputTopic.trim()) {
        alert("Please enter a topic first!");
        return;
      }
    } else {
      // For Grading, Formalize, Rubric, etc.
      if (!studentContent.trim()) {
        alert("Please provide the text/content first!");
        return;
      }
    }

    setIsLoading(true);
    setResult(null);
    if (activeTab === "routine") setRoutineData(null);
    if (activeTab === "exam") setAssessmentData(null);

    try {
      if (activeTab === "routine") {
        // 🔴 Fix: Matched with Backend Endpoint (/study/routine/generate)
        const res = await fetchAPI("/study/routine/generate", {
          method: "POST",
          body: JSON.stringify({ 
            focus_area: inputTopic, 
            weak_topics: [inputTopic], 
            strong_topics: [], 
            target_cgpa: 3.8 
          })
        });
        
        if (res.status === "success") {
          setRoutineData(res.data);
          // Note: Backend securely saves the routine to Supabase now. 
          // Frontend redundant insert removed to prevent duplication.
        }
      } 
      else if (activeTab === "exam") {
        // 🔴 Fix: Matched with Assessment Endpoint Payload
        const res = await fetchAPI("/study/assessment", {
          method: "POST",
          body: JSON.stringify({ 
            topic: inputTopic, 
            difficulty: "Medium",
            role: "Student" 
          })
        });
        if (res.status === "success") setAssessmentData(res.data);
      } 
      else {
        // Generic fallback for Grading, Rubric & Notice (Uses standard text generation)
        // 🔴 STRICT PAYLOAD MATCH for /academic/generate
        const payload = { 
          task_type: activeTab, 
          content: studentContent,
          topic: inputTopic || "General Academic Work" 
        }; 
        
        const res = await fetchAPI("/academic/generate", { 
          method: "POST", 
          body: JSON.stringify(payload) 
        });
        setResult(res.result || res.data || "Task completed successfully.");
      }
    } catch (error: any) {
      alert(`Execution Failed: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearRoutine = async () => {
    setIsLoading(true);
    try {
      // 🔴 Fix: Safe backend deletion
      await fetchAPI("/study/routine", { method: "DELETE" });
      setRoutineData(null);
    } catch (error) {
      console.error("Failed to clear routine:", error);
      alert("Failed to clear routine.");
    }
    setIsLoading(false);
  };

  // 🔴 Add this useEffect to fetch the real user role on mount
  useEffect(() => {
    const checkAccess = async () => {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        // Fetch role from metadata and make it lowercase for easy comparison
        const role = session.user.user_metadata?.role?.toLowerCase() || "student";
        setUserRole(role);
      }
      setIsCheckingAccess(false);
    };
    checkAccess();
  }, []);

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
        
        {/* =========================================
            LEFT COLUMN: CONTROLS & INPUTS (Unchanged Layout)
            ========================================= */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* Tools Menu */}
          <div className="bg-[#1e1e1e] border border-white/5 rounded-2xl overflow-hidden shadow-xl p-2">
            <div className="px-4 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Select Tool</div>
            <div className="space-y-1">
              
              {/* ONLY FOR STUDENTS */}
              {userRole === "student" && (
                <>
                  <button onClick={() => { setActiveTab("routine"); setResult(null); setRoutineData(null); setAssessmentData(null); }} className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all ${activeTab === "routine" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-inner" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
                    <Calendar className="w-4 h-4" /> Smart Study Routine
                  </button>
                  <button onClick={() => { setActiveTab("exam"); setResult(null); setRoutineData(null); setAssessmentData(null); }} className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all ${activeTab === "exam" ? "bg-purple-500/10 text-purple-400 border border-purple-500/20 shadow-inner" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
                    <Brain className="w-4 h-4" /> Mock Exam Generator
                  </button>
                </>
              )}

              {/* ONLY FOR FACULTY / ADMIN */}
              {(userRole === "faculty" || userRole === "admin") && (
                <>
                  <button onClick={() => { setActiveTab("exam"); setResult(null); setRoutineData(null); setAssessmentData(null); }} className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all ${activeTab === "exam" ? "bg-purple-500/10 text-purple-400 border border-purple-500/20 shadow-inner" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
                    <Brain className="w-4 h-4" /> Quiz Generator
                  </button>

                  <button onClick={() => { setActiveTab("rubric"); setResult(null); setRoutineData(null); setAssessmentData(null); }} className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all ${activeTab === "rubric" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-inner" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
                    <CheckSquare className="w-4 h-4" /> Grading Rubric
                  </button>
                  
                  <button onClick={() => { setActiveTab("notice"); setResult(null); setRoutineData(null); setAssessmentData(null); }} className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all ${activeTab === "notice" ? "bg-blue-500/10 text-blue-400 border border-blue-500/20 shadow-inner" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
                    <Bell className="w-4 h-4" /> Formal Notice Engine
                  </button>
                </>
              )}
              
            </div>
          </div>

          {/* Input Area */}
          <div className="bg-[#1e1e1e] border border-white/5 rounded-2xl p-6 shadow-xl">
            <label className="block text-sm font-medium text-gray-400 mb-3">
              {activeTab === "notice" ? "Raw Instruction (Banglish/Casual)" : "Focus Topic or Subject"}
            </label>
            
            {activeTab === "notice" ? (
              <textarea value={inputTopic} onChange={(e) => setInputTopic(e.target.value)} placeholder="e.g., Kal class hobe na..." rows={4} className="w-full bg-[#121212] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-amber-500 transition-all resize-none mb-4 text-[15px]" />
            ) : (
              <input type="text" value={inputTopic} onChange={(e) => setInputTopic(e.target.value)} placeholder="e.g., Cold War, Realism" className="w-full bg-[#121212] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-amber-500 transition-all mb-4 text-[15px]" />
            )}

            {activeTab === "routine" && (
              <div className="mb-6">
                <label className="text-sm font-medium text-gray-400 mb-3 flex items-center justify-between">
                  <span>Target Study Hours/Day</span> <span className="text-amber-400 font-bold">{studyHours} hrs</span>
                </label>
                <input type="range" min="1" max="10" value={studyHours} onChange={(e) => setStudyHours(parseInt(e.target.value))} className="w-full accent-amber-500" />
              </div>
            )}

            <button onClick={executeTask} disabled={!inputTopic || isLoading} className="w-full flex items-center justify-center gap-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-bold py-4 rounded-xl transition-all shadow-lg">
              {isLoading ? "Drafting..." : <><Sparkles className="w-5 h-5" /> Generate Now</>}
            </button>
          </div>
        </div>

        {/* =========================================
            RIGHT COLUMN: DYNAMIC RESULTS OUTPUT
            ========================================= */}
        <div className="lg:col-span-8">
          <div className="bg-[#1e1e1e] border border-white/5 rounded-3xl p-8 shadow-xl min-h-125 flex flex-col relative">
            
            {/* Loading & Empty States */}
            {!isLoading && !result && !routineData && !assessmentData && (
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

            {/* 🔴 1. ROUTINE RENDERER (Glassmorphism Cards) */}
            {routineData && !isLoading && (
              <div className="animate-in fade-in space-y-4">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-xl font-bold text-emerald-400">Your Personalized 7-Day Plan</h3>
                  <button onClick={handleClearRoutine} className="flex items-center gap-2 text-sm text-rose-400 hover:text-rose-300 font-bold bg-rose-500/10 px-4 py-2 rounded-lg">
                    <RefreshCw className="w-4 h-4" /> Clear
                  </button>
                </div>
                
                {["day_1", "day_2", "day_3", "day_4", "day_5", "day_6", "day_7"].map((day, idx) => {
                  const data = routineData[day];
                  if (!data) return null;
                  const focus = data.focus_subject || data.focus || "Daily Task";
                  const strategy = data.strategy || data;
                  
                  return (
                    <div key={day} className="bg-linear-to-br from-emerald-500/10 to-slate-900/60 border-l-4 border-emerald-500 border-t border-emerald-500/20 border-r border-emerald-500/20 border-b border-emerald-500/20 p-5 rounded-xl shadow-lg backdrop-blur-md">
                      <h4 className="text-emerald-400 font-bold mb-2 flex items-center gap-2 text-lg">📅 {day.replace('_', ' ').toUpperCase()}</h4>
                      <p className="text-gray-200 text-[15px] leading-relaxed">
                        🎯 <b className="text-white">{focus}:</b> {strategy}
                      </p>
                    </div>
                  );
                })}
                {routineData.ai_advice && (
                  <div className="bg-amber-500/10 border border-amber-500/30 p-5 rounded-xl text-amber-400 text-[15px] font-medium mt-6 flex gap-3 items-start">
                    <Brain className="w-6 h-6 shrink-0" />
                    <p><b>AI Advice:</b> {routineData.ai_advice}</p>
                  </div>
                )}
              </div>
            )}

            {/* 🔴 2. MOCK EXAM RENDERER (Expandable Loop) */}
            {assessmentData && assessmentData.assessment_type === "Mock Exam" && !isLoading && (
              <div className="animate-in fade-in bg-[#171717] p-8 rounded-3xl border border-white/10 shadow-2xl">
                <h3 className="text-2xl font-bold text-white mb-2 flex items-center gap-3"><FileText className="w-6 h-6 text-indigo-400"/> {assessmentData.assessment_type}</h3>
                <p className="text-indigo-400 font-medium mb-8 pb-4 border-b border-white/10 bg-indigo-500/10 p-3 rounded-lg">{assessmentData.exam_rules}</p>

                <div className="space-y-8">
                  {assessmentData.questions?.map((q: any, idx: number) => (
                    <div key={idx} className="bg-[#1e1e1e] p-6 rounded-2xl border border-white/5">
                      <h4 className="text-lg font-bold text-gray-200 mb-4 leading-relaxed">
                        <span className="text-indigo-400 mr-2">Q{idx + 1}.</span> {q.q} 
                        <span className="text-[11px] uppercase tracking-wider ml-3 px-2 py-1 bg-white/10 text-gray-300 rounded-full border border-white/20">{q.difficulty}</span>
                      </h4>
                      
                      <div className="mb-4">
                        <button onClick={() => setExpandedHints({...expandedHints, [idx]: !expandedHints[idx]})} className="flex items-center gap-2 text-[14px] text-amber-400 font-bold hover:text-amber-300">
                          <ChevronDown className={`w-4 h-4 transition-transform ${expandedHints[idx] ? "rotate-180" : ""}`} /> 💡 View Hints
                        </button>
                        {expandedHints[idx] && (
                          <ul className="mt-3 ml-6 list-disc text-gray-300 text-[14px] space-y-1 p-3 bg-[#0a0a0a] rounded-xl border border-white/5">
                            {q.hints?.map((h: string, i: number) => <li key={i}>{h}</li>)}
                          </ul>
                        )}
                      </div>

                      <div>
                        <button onClick={() => setExpandedAnswers({...expandedAnswers, [idx]: !expandedAnswers[idx]})} className="flex items-center gap-2 text-[14px] text-emerald-400 font-bold hover:text-emerald-300">
                          <ChevronDown className={`w-4 h-4 transition-transform ${expandedAnswers[idx] ? "rotate-180" : ""}`} /> 👁️ Reveal Ideal Answer
                        </button>
                        {expandedAnswers[idx] && (
                          <div className="mt-4 p-5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
                            <p className="text-emerald-300 font-bold mb-2">Key points you MUST include:</p>
                            <ul className="list-disc ml-6 text-gray-300 text-[14px] mb-5 space-y-1">
                              {q.key_points?.map((pt: string, i: number) => <li key={i}>{pt}</li>)}
                            </ul>
                            <div className="bg-[#0a0a0a] p-4 rounded-lg border border-emerald-500/10">
                              <p className="text-emerald-400 font-bold mb-2 flex items-center gap-2"><Brain className="w-4 h-4"/> AI Model Answer:</p>
                              <p className="text-gray-200 text-[14.5px] leading-relaxed">{q.model_answer}</p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 🔴 3. STANDARD MARKDOWN RENDERER (For Rubric & Notice) */}
            {result && !isLoading && (
              <div className="animate-in fade-in slide-in-from-bottom-6">
                <h3 className="text-[13px] font-bold text-gray-500 uppercase tracking-wider mb-6 flex items-center justify-between border-b border-white/10 pb-4">
                  <span>Generated Output</span>
                  <button onClick={() => navigator.clipboard.writeText(result)} className="text-amber-400 hover:text-amber-300 normal-case font-medium">Copy Text</button>
                </h3>
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