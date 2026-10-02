"use client";

import { useState, useEffect } from "react";
import { Sparkles, Brain, CheckSquare, Bell, Calendar, FileText, ChevronDown, RefreshCw, Copy, Check } from "lucide-react";
import { createClient } from "../../utils/supabase/client";
import { fetchAPI } from "../../utils/api";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function AcademicCopilotPage() {
  const [activeTab, setActiveTab] = useState("routine");
  
  const [userRole, setUserRole] = useState("student");
  const [adminViewMode, setAdminViewMode] = useState<"student" | "faculty">("student");
  const [isCheckingAccess, setIsCheckingAccess] = useState(true);

  // 🔴 Input States
  const [inputTopic, setInputTopic] = useState("");
  const [studentContent, setStudentContent] = useState("");
  const [studyHours, setStudyHours] = useState(4);
  const [isLoading, setIsLoading] = useState(false);

  // 🔴 Output States
  const [result, setResult] = useState<string | null>(null);
  const [routineData, setRoutineData] = useState<any>(null);
  const [assessmentData, setAssessmentData] = useState<any>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Toggles for Assessment Answers
  const [expandedHints, setExpandedHints] = useState<{ [key: number]: boolean }>({});
  const [expandedAnswers, setExpandedAnswers] = useState<{ [key: number]: boolean }>({});
  const [showAllAnswers, setShowAllAnswers] = useState(false);

  // Effective Role (If admin, follows adminViewMode toggle)
  const effectiveRole = userRole === "admin" ? adminViewMode : userRole;

  // 🔴 Role Resolution on Mount
  useEffect(() => {
    const checkAccess = async () => {
      try {
        const supabase = createClient();
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
          const email = (session.user.email || "").toLowerCase();
          const metaRole = (session.user.app_metadata?.role || session.user.user_metadata?.role || "").toLowerCase();
          const activeSavedRole = typeof window !== "undefined" ? localStorage.getItem("gstu_active_role") : null;
          
          let role = activeSavedRole || metaRole || (email === "yousufaltashfin@gmail.com" ? "admin" : "student");
          
          setUserRole(role);
          if (role === "faculty") {
            setActiveTab("exam"); // Quiz Generator
          } else {
            setActiveTab("routine"); // Smart Routine
          }
        }
      } catch (err) {
        console.error("Failed to check user role:", err);
      } finally {
        setIsCheckingAccess(false);
      }
    };
    checkAccess();
  }, []);

  // 🔴 Fetch Existing Routine for Students
  useEffect(() => {
    const fetchSavedRoutine = async () => {
      try {
        const res = await fetchAPI("/study/routine", { method: "GET" });
        if (res?.data?.routine_data) {
          setRoutineData(res.data.routine_data);
        }
      } catch (e) {
        // Silently skip if no saved routine exists
      }
    };
    fetchSavedRoutine();
  }, []);

  // 🔴 Safe Execution & State Routing
  const executeTask = async () => {
    // 1. Precise Data Validation Based on Active Tab
    if (activeTab === "routine" || activeTab === "exam") {
      if (!inputTopic.trim()) {
        alert("Please enter a focus topic or subject first!");
        return;
      }
    } else if (activeTab === "rubric") {
      if (!inputTopic.trim()) {
        alert("Please enter the assignment title or topic for the rubric!");
        return;
      }
    } else if (activeTab === "notice") {
      if (!inputTopic.trim() && !studentContent.trim()) {
        alert("Please provide the message or instruction for the notice!");
        return;
      }
    } else {
      if (!inputTopic.trim() && !studentContent.trim()) {
        alert("Please provide the required topic or content!");
        return;
      }
    }

    setIsLoading(true);
    setResult(null);
    if (activeTab === "routine") setRoutineData(null);
    if (activeTab === "exam") setAssessmentData(null);

    try {
      if (activeTab === "routine") {
        const res = await fetchAPI("/study/routine", {
          method: "POST",
          body: JSON.stringify({ 
            weak_topics: [inputTopic], 
            strong_topics: [], 
            target_cgpa: 3.8 
          })
        });
        
        if (res?.status === "success") {
          setRoutineData(res.data);
        }
      }

      else if (activeTab === "exam") {
        const isFaculty = effectiveRole === "faculty";
        const endpoint = isFaculty ? "/faculty/assessment" : "/study/assessment";
        const body = isFaculty
          ? { topic: inputTopic }
          : { topic: inputTopic, difficulty: "Medium", role: "Student" };

        let res;
        try {
          res = await fetchAPI(endpoint, { method: "POST", body: JSON.stringify(body) });
        } catch (primaryErr: any) {
          // If faculty endpoint hits a role-sync cache, seamlessly fallback to study assessment in Faculty role
          if (isFaculty) {
            console.warn("Primary assessment failed, attempting resilient fallback:", primaryErr);
            res = await fetchAPI("/study/assessment", {
              method: "POST",
              body: JSON.stringify({ topic: inputTopic, difficulty: "Medium", role: "Faculty" })
            });
          } else {
            throw primaryErr;
          }
        }

        if (res?.status === "success") {
          setAssessmentData(res.data || res);
        } else if (res?.result) {
          setResult(res.result);
        }
      }
      
      else if (activeTab === "rubric") {
        const payload = {
          task_type: "rubric",
          topic: inputTopic,
          content: studentContent || inputTopic
        };
        const res = await fetchAPI("/academic/generate", {
          method: "POST",
          body: JSON.stringify(payload)
        });
        setResult(res?.result || res?.data || "Rubric generated successfully.");
      }

      else if (activeTab === "notice") {
        const rawText = (inputTopic || studentContent).trim();
        let res;
        try {
          res = await fetchAPI("/admin/notices", {
            method: "POST",
            body: JSON.stringify({ raw_text: rawText })
          });
        } catch (adminErr: any) {
          console.warn("Admin notice endpoint error, trying academic notice fallback:", adminErr);
          res = await fetchAPI("/academic/generate", {
            method: "POST",
            body: JSON.stringify({ task_type: "notice", topic: rawText, content: rawText })
          });
        }
        setResult(res?.result || res?.data || "Notice generated successfully.");
      } 
      
      else {
        const payload = { 
          task_type: activeTab, 
          content: studentContent || inputTopic, 
          topic: inputTopic || "General Academic Work" 
        };
        const res = await fetchAPI("/academic/generate", { method: "POST", body: JSON.stringify(payload) });
        setResult(res?.result || res?.data || "Task completed successfully.");
      }
    
    } catch (error: any) {
      console.error("Execution error:", error);
      alert(`Execution Failed: ${error.message || "An unexpected error occurred."}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearRoutine = async () => {
    setIsLoading(true);
    try {
      await fetchAPI("/study/routine", { method: "DELETE" });
      setRoutineData(null);
    } catch (error) {
      console.error("Failed to clear routine:", error);
      alert("Failed to clear routine.");
    }
    setIsLoading(false);
  };

  const copyTextToClipboard = (text: string, key: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const copyAssessmentPaper = (data: any) => {
    if (!data) return;
    let paperText = `=========================================\n${data.assessment_type || "UNIVERSITY ASSESSMENT"}\nTopic: ${inputTopic}\n${data.exam_rules ? data.exam_rules + "\n" : ""}=========================================\n\n`;
    
    // Student Mock Exam format
    if (data.questions && data.questions.length > 0) {
      data.questions.forEach((q: any, i: number) => {
        paperText += `Q${i + 1}. [${q.difficulty || "Standard"}] ${q.q}\n`;
        if (q.hints && q.hints.length > 0) {
          paperText += `   Hints:\n`;
          q.hints.forEach((h: string) => { paperText += `   - ${h}\n`; });
        }
        if (q.key_points && q.key_points.length > 0) {
          paperText += `   Key Points Expected:\n`;
          q.key_points.forEach((kp: string) => { paperText += `   - ${kp}\n`; });
        }
        if (q.model_answer) {
          paperText += `   AI Model Answer: ${q.model_answer}\n`;
        }
        paperText += `\n`;
      });
    }

    if (data.mcqs && data.mcqs.length > 0) {
      paperText += `PART A: MULTIPLE CHOICE QUESTIONS (${data.mcqs.length} Questions)\n-----------------------------------------\n\n`;
      data.mcqs.forEach((m: any, i: number) => {
        paperText += `${i + 1}. ${m.q}\n`;
        m.options?.forEach((opt: string, oi: number) => {
          paperText += `   ${String.fromCharCode(65 + oi)}) ${opt.replace(/^[A-Da-d][\.\)\:\-]\s*/, "")}\n`;
        });
        paperText += `   [Correct Answer: ${m.answer}]\n\n`;
      });
    }

    if (data.broad_questions && data.broad_questions.length > 0) {
      paperText += `\nPART B: BROAD ANALYTICAL QUESTIONS (${data.broad_questions.length} Questions)\n-----------------------------------------\n\n`;
      data.broad_questions.forEach((b: any, i: number) => {
        paperText += `Q${i + 1}. ${b.q} (${b.difficulty || "Standard"})\n`;
        if (b.expected_points && b.expected_points.length > 0) {
          paperText += `   Key Evaluation Points:\n`;
          b.expected_points.forEach((pt: string) => {
            paperText += `   - ${pt}\n`;
          });
        }
        paperText += `\n`;
      });
    }

    copyTextToClipboard(paperText, "assessment");
  };

  return (
    <div className="min-h-dvh bg-[#121212] text-gray-200 p-6 md:p-12 font-sans transition-all duration-300">
      
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-3">
          <Sparkles className="w-8 h-8 text-amber-500" /> Academic Copilot
        </h1>
        <p className="text-gray-400 mt-2 text-[15px]">
          Automated academic assistant for syllabus planning, assessment engineering, and administrative notices.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* =========================================
            LEFT COLUMN: CONTROLS & INPUTS
            ========================================= */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* Admin Role Switcher Banner (Superadmin preview & testing) */}
          {userRole === "admin" && (
            <div className="bg-[#1e1e1e] border border-amber-500/20 rounded-2xl p-3 shadow-xl flex items-center justify-between">
              <span className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" /> Admin Simulator:
              </span>
              <div className="flex gap-1.5">
                <button
                  onClick={() => { setAdminViewMode("student"); setActiveTab("routine"); setResult(null); setRoutineData(null); setAssessmentData(null); }}
                  className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${adminViewMode === "student" ? "bg-amber-500 text-black shadow-md font-black" : "bg-white/5 text-gray-400 hover:text-white"}`}
                >
                  Student
                </button>
                <button
                  onClick={() => { setAdminViewMode("faculty"); setActiveTab("exam"); setResult(null); setRoutineData(null); setAssessmentData(null); }}
                  className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${adminViewMode === "faculty" ? "bg-purple-600 text-white shadow-md font-black" : "bg-white/5 text-gray-400 hover:text-white"}`}
                >
                  Faculty
                </button>
              </div>
            </div>
          )}

          {/* Tools Menu */}
          <div className="bg-[#1e1e1e] border border-white/5 rounded-2xl overflow-hidden shadow-xl p-2">
            <div className="px-4 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider flex items-center justify-between">
              <span>Select Academic Tool</span>
              <span className="text-[10px] text-amber-400 font-bold uppercase">{effectiveRole} Mode</span>
            </div>
            <div className="space-y-1">
              
              {/* FOR STUDENTS (ONLY Smart Study Routine & 3h Mock Exam) */}
              {effectiveRole === "student" && (
                <>
                  <button 
                    onClick={() => { setActiveTab("routine"); setResult(null); setRoutineData(null); setAssessmentData(null); }} 
                    className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all cursor-pointer ${activeTab === "routine" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-inner font-semibold" : "text-gray-400 hover:text-white hover:bg-white/5"}`}
                  >
                    <Calendar className="w-4 h-4" /> Smart Study Routine
                  </button>
                  <button 
                    onClick={() => { setActiveTab("exam"); setResult(null); setRoutineData(null); setAssessmentData(null); }} 
                    className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all cursor-pointer ${activeTab === "exam" ? "bg-purple-500/10 text-purple-400 border border-purple-500/20 shadow-inner font-semibold" : "text-gray-400 hover:text-white hover:bg-white/5"}`}
                  >
                    <Brain className="w-4 h-4" /> Mock Exam (3h / 60m)
                  </button>
                </>
              )}

              {/* FOR FACULTY (ONLY Quiz, Grading Rubric, Formal Notice) */}
              {effectiveRole === "faculty" && (
                <>
                  <button 
                    onClick={() => { setActiveTab("exam"); setResult(null); setRoutineData(null); setAssessmentData(null); }} 
                    className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all cursor-pointer ${activeTab === "exam" ? "bg-purple-500/10 text-purple-400 border border-purple-500/20 shadow-inner font-semibold" : "text-gray-400 hover:text-white hover:bg-white/5"}`}
                  >
                    <Brain className="w-4 h-4" /> Quiz Generator
                  </button>

                  <button 
                    onClick={() => { setActiveTab("rubric"); setResult(null); setRoutineData(null); setAssessmentData(null); }} 
                    className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all cursor-pointer ${activeTab === "rubric" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-inner font-semibold" : "text-gray-400 hover:text-white hover:bg-white/5"}`}
                  >
                    <CheckSquare className="w-4 h-4" /> Grading Rubric
                  </button>
                  
                  <button 
                    onClick={() => { setActiveTab("notice"); setResult(null); setRoutineData(null); setAssessmentData(null); }} 
                    className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all cursor-pointer ${activeTab === "notice" ? "bg-blue-500/10 text-blue-400 border border-blue-500/20 shadow-inner font-semibold" : "text-gray-400 hover:text-white hover:bg-white/5"}`}
                  >
                    <Bell className="w-4 h-4" /> Formal Notice Engine
                  </button>
                </>
              )}
              
            </div>
          </div>

          {/* Input Area */}
          <div className="bg-[#1e1e1e] border border-white/5 rounded-2xl p-6 shadow-xl">
            <label className="block text-sm font-medium text-gray-300 mb-3">
              {activeTab === "notice" 
                ? "Notice Instructions (Banglish / English)" 
                : activeTab === "rubric" 
                ? "Assignment Subject or Topic" 
                : "Focus Subject or Topic"}
            </label>
            
            {activeTab === "notice" ? (
              <textarea 
                value={inputTopic} 
                onChange={(e) => setInputTopic(e.target.value)} 
                placeholder="e.g., Kal 10 tay department ar sob student der presentation room 302 te hobe. Late attendance allow kora hobe na..." 
                rows={5} 
                className="w-full bg-[#121212] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-amber-500 transition-all resize-none mb-4 text-[14.5px] leading-relaxed" 
              />
            ) : activeTab === "rubric" ? (
              <>
                <input 
                  type="text" 
                  value={inputTopic} 
                  onChange={(e) => setInputTopic(e.target.value)} 
                  placeholder="e.g., Term Paper on US Hegemony and Multipolarity" 
                  className="w-full bg-[#121212] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-amber-500 transition-all mb-3 text-[14.5px]" 
                />
                <label className="block text-xs font-medium text-gray-400 mb-2">
                  Specific Evaluation Guidelines (Optional)
                </label>
                <textarea 
                  value={studentContent} 
                  onChange={(e) => setStudentContent(e.target.value)} 
                  placeholder="e.g., Total 100 marks, focus on empirical case study, 1500 words limit, APA citations..." 
                  rows={3} 
                  className="w-full bg-[#121212] border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-amber-500 transition-all resize-none mb-4 text-[13.5px]" 
                />
              </>
            ) : (
              <input 
                type="text" 
                value={inputTopic} 
                onChange={(e) => setInputTopic(e.target.value)} 
                placeholder={effectiveRole === "faculty" ? "e.g., Nuclear Deterrence & MAD Theory (Quiz topic)" : "e.g., Cold War, Realism, Foreign Policy (Exam subject)"} 
                className="w-full bg-[#121212] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-amber-500 transition-all mb-4 text-[14.5px]" 
              />
            )}

            {activeTab === "routine" && (
              <div className="mb-6">
                <label className="text-sm font-medium text-gray-400 mb-3 flex items-center justify-between">
                  <span>Target Study Hours/Day</span> <span className="text-amber-400 font-bold">{studyHours} hrs</span>
                </label>
                <input 
                  type="range" 
                  min="1" 
                  max="10" 
                  value={studyHours} 
                  onChange={(e) => setStudyHours(parseInt(e.target.value))} 
                  className="w-full accent-amber-500" 
                />
              </div>
            )}

            <button 
              onClick={executeTask} 
              disabled={(!inputTopic.trim() && !studentContent.trim()) || isLoading} 
              className="w-full flex items-center justify-center gap-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-40 disabled:hover:bg-amber-600 text-white font-bold py-3.5 rounded-xl transition-all shadow-lg cursor-pointer disabled:cursor-not-allowed"
            >
              {isLoading ? "Generating..." : <><Sparkles className="w-5 h-5" /> Generate Now</>}
            </button>
          </div>
        </div>

        {/* =========================================
            RIGHT COLUMN: DYNAMIC RESULTS OUTPUT
            ========================================= */}
        <div className="lg:col-span-8">
          <div className="bg-[#1e1e1e] border border-white/5 rounded-3xl p-6 md:p-8 shadow-xl min-h-125 flex flex-col relative">
            
            {/* Loading & Empty States */}
            {!isLoading && !result && !routineData && !assessmentData && (
              <div className="flex-1 flex flex-col items-center justify-center text-gray-500 py-16">
                <FileText className="w-16 h-16 mb-4 opacity-50" />
                <p className="text-[15px] font-medium text-gray-400">Select a tool and enter parameters to generate academic content.</p>
                <p className="text-xs text-gray-500 mt-1">Quiz generator, grading rubrics, and notices will appear here.</p>
              </div>
            )}
            
            {isLoading && (
              <div className="flex-1 flex flex-col items-center justify-center text-gray-400 py-20">
                <Sparkles className="w-12 h-12 mb-4 text-amber-500 animate-bounce" />
                <p className="text-[15px] font-medium tracking-wide text-white">Copilot is drafting your academic document...</p>
                <p className="text-xs text-gray-400 mt-1">Applying curriculum standards and department context</p>
              </div>
            )}

            {/* 🔴 1. ROUTINE RENDERER */}
            {routineData && !isLoading && (
              <div className="animate-in fade-in space-y-4">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-xl font-bold text-emerald-400">Your Personalized 7-Day Plan</h3>
                  <button onClick={handleClearRoutine} className="flex items-center gap-2 text-sm text-rose-400 hover:text-rose-300 font-bold bg-rose-500/10 px-4 py-2 rounded-lg">
                    <RefreshCw className="w-4 h-4" /> Clear
                  </button>
                </div>
                
                {["day_1", "day_2", "day_3", "day_4", "day_5", "day_6", "day_7"].map((day) => {
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

            {/* 🔴 2A. STUDENT MOCK EXAM RENDERER */}
            {assessmentData && assessmentData.assessment_type === "Mock Exam" && !isLoading && (
              <div className="animate-in fade-in bg-[#171717] p-6 md:p-8 rounded-3xl border border-white/10 shadow-2xl space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-white/10">
                  <h3 className="text-2xl font-bold text-white flex items-center gap-3">
                    <FileText className="w-6 h-6 text-indigo-400"/> {assessmentData.assessment_type}
                  </h3>
                  <button
                    onClick={() => copyTextToClipboard(JSON.stringify(assessmentData, null, 2), "exam_raw")}
                    className="text-xs text-gray-400 hover:text-white flex items-center gap-1.5 px-3 py-1.5 bg-white/5 rounded-lg border border-white/10"
                  >
                    {copiedKey === "exam_raw" ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedKey === "exam_raw" ? "Copied" : "Copy JSON"}
                  </button>
                </div>
                
                {assessmentData.exam_rules && (
                  <p className="text-indigo-400 font-medium pb-2 border-b border-white/10 bg-indigo-500/10 p-3 rounded-lg text-sm">
                    {assessmentData.exam_rules}
                  </p>
                )}

                <div className="space-y-6">
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

            {/* 🔴 2B. FACULTY QUIZ & QUESTION PAPER RENDERER */}
            {assessmentData && (assessmentData.assessment_type === "Faculty Question Paper" || assessmentData.assessment_type === "Quiz" || (assessmentData.mcqs && assessmentData.mcqs.length > 0)) && !isLoading && (
              <div className="animate-in fade-in bg-[#171717] p-6 md:p-8 rounded-3xl border border-white/10 shadow-2xl space-y-8">
                
                {/* Header with quick actions */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-white/10">
                  <div>
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                        {assessmentData.assessment_type || "Faculty Assessment"}
                      </span>
                      {assessmentData.mcqs && (
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-white/5 text-gray-300 border border-white/10">
                          {assessmentData.mcqs.length} MCQs
                        </span>
                      )}
                      {assessmentData.broad_questions && (
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-white/5 text-gray-300 border border-white/10">
                          {assessmentData.broad_questions.length} Broad Questions
                        </span>
                      )}
                    </div>
                    <h3 className="text-xl md:text-2xl font-bold text-white flex items-center gap-2">
                      <Brain className="w-6 h-6 text-purple-400" />
                      University Assessment Sheet
                    </h3>
                  </div>
                  
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      onClick={() => setShowAllAnswers(!showAllAnswers)}
                      className="text-xs font-semibold px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-gray-300 border border-white/10 transition-all cursor-pointer"
                    >
                      {showAllAnswers ? "Hide All Answers" : "Reveal All Answers"}
                    </button>
                    <button
                      onClick={() => copyAssessmentPaper(assessmentData)}
                      className="flex items-center gap-1.5 text-xs font-bold px-3 py-2 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 transition-all cursor-pointer"
                    >
                      {copiedKey === "assessment" ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      {copiedKey === "assessment" ? "Copied Paper!" : "Copy Full Paper"}
                    </button>
                  </div>
                </div>

                {/* Section A: MCQs */}
                {assessmentData.mcqs && assessmentData.mcqs.length > 0 && (
                  <div className="space-y-4">
                    <h4 className="text-xs font-bold text-purple-400 uppercase tracking-wider flex items-center gap-2">
                      <span>Part A: Multiple Choice Questions</span>
                      <span className="text-gray-500">({assessmentData.mcqs.length} Items)</span>
                    </h4>

                    <div className="grid grid-cols-1 gap-4">
                      {assessmentData.mcqs.map((mcq: any, idx: number) => {
                        const isRevealed = showAllAnswers || expandedAnswers[idx];
                        return (
                          <div key={idx} className="bg-[#1e1e1e] p-5 rounded-2xl border border-white/5 hover:border-purple-500/20 transition-all">
                            <div className="flex items-start gap-3 mb-3">
                              <span className="shrink-0 w-7 h-7 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-300 font-bold text-sm flex items-center justify-center">
                                {idx + 1}
                              </span>
                              <p className="text-gray-100 font-medium text-[15px] leading-relaxed">
                                {mcq.q}
                              </p>
                            </div>

                            {/* Options Grid */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 my-3 ml-0 sm:ml-10">
                              {mcq.options?.map((opt: string, optIdx: number) => {
                                const optLetter = String.fromCharCode(65 + optIdx);
                                const rawCleanOpt = opt.replace(/^[A-Da-d][\.\)\:\-]\s*/, "").trim();
                                const isCorrect = isRevealed && (
                                  mcq.answer === opt || 
                                  mcq.answer?.trim().toLowerCase() === rawCleanOpt.toLowerCase() ||
                                  mcq.answer?.trim().toUpperCase() === optLetter ||
                                  mcq.answer?.startsWith(optLetter)
                                );

                                return (
                                  <div
                                    key={optIdx}
                                    className={`px-3.5 py-2.5 rounded-xl border text-sm transition-all flex items-start gap-2 ${
                                      isCorrect
                                        ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300 font-semibold"
                                        : "bg-[#141414] border-white/5 text-gray-300"
                                    }`}
                                  >
                                    <span className="text-gray-400 font-mono text-xs">{optLetter}.</span>
                                    <span className="leading-snug">{rawCleanOpt}</span>
                                  </div>
                                );
                              })}
                            </div>

                            {/* Answer reveal toggle */}
                            <div className="ml-0 sm:ml-10 mt-2 flex items-center justify-between pt-2 border-t border-white/5">
                              <button
                                onClick={() => setExpandedAnswers({ ...expandedAnswers, [idx]: !expandedAnswers[idx] })}
                                className="text-xs font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1 cursor-pointer"
                              >
                                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isRevealed ? "rotate-180" : ""}`} />
                                {isRevealed ? "Hide Answer" : "Reveal Answer"}
                              </button>
                              {isRevealed && (
                                <span className="text-xs text-emerald-400 font-semibold bg-emerald-500/10 px-2.5 py-1 rounded-md border border-emerald-500/20">
                                  Correct: {mcq.answer}
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Section B: Broad Questions */}
                {assessmentData.broad_questions && assessmentData.broad_questions.length > 0 && (
                  <div className="space-y-4 pt-4 border-t border-white/10">
                    <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-2">
                      <span>Part B: Broad Analytical Questions</span>
                      <span className="text-gray-500">({assessmentData.broad_questions.length} Items)</span>
                    </h4>

                    <div className="space-y-4">
                      {assessmentData.broad_questions.map((bq: any, idx: number) => {
                        const diffColor = 
                          bq.difficulty === "Critical" ? "bg-rose-500/10 text-rose-400 border-rose-500/20" :
                          bq.difficulty === "Medium" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                          "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
                        return (
                          <div key={idx} className="bg-[#1e1e1e] p-5 rounded-2xl border border-white/5 space-y-3">
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex items-start gap-3">
                                <span className="shrink-0 w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 font-bold text-sm flex items-center justify-center">
                                  Q{idx + 1}
                                </span>
                                <p className="text-gray-100 font-semibold text-[15px] leading-relaxed">
                                  {bq.q}
                                </p>
                              </div>
                              {bq.difficulty && (
                                <span className={`shrink-0 text-[11px] uppercase tracking-wider px-2 py-0.5 rounded-full border ${diffColor}`}>
                                  {bq.difficulty}
                                </span>
                              )}
                            </div>

                            {bq.expected_points && bq.expected_points.length > 0 && (
                              <div className="ml-0 sm:ml-10 p-3.5 bg-[#141414] rounded-xl border border-white/5">
                                <p className="text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wide">Key Points Expected in Answer:</p>
                                <ul className="list-disc ml-5 space-y-1 text-sm text-gray-300">
                                  {bq.expected_points.map((pt: string, pIdx: number) => (
                                    <li key={pIdx}>{pt}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 🔴 3. STANDARD MARKDOWN RENDERER (For Rubric & Notice) */}
            {result && !isLoading && (
              <div className="animate-in fade-in slide-in-from-bottom-6">
                <div className="text-[13px] font-bold text-gray-400 uppercase tracking-wider mb-6 flex items-center justify-between border-b border-white/10 pb-4">
                  <span className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-amber-500" />
                    {activeTab === "rubric" ? "Curriculum Grading Rubric" : activeTab === "notice" ? "Formal Bilingual Notice" : "Generated Output"}
                  </span>
                  <button 
                    onClick={() => copyTextToClipboard(result, "result")} 
                    className="flex items-center gap-1.5 text-xs text-amber-400 hover:text-amber-300 font-medium bg-amber-500/10 px-3 py-1.5 rounded-lg border border-amber-500/20 transition-all cursor-pointer"
                  >
                    {copiedKey === "result" ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedKey === "result" ? "Copied!" : "Copy Text"}
                  </button>
                </div>
                
                <div className="text-gray-200 text-[15px] leading-relaxed">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({node, ...props}) => <p className="mb-4 last:mb-0 leading-relaxed" {...props} />,
                      strong: ({node, ...props}) => <strong className="font-semibold text-white" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc pl-6 mb-4 space-y-2 marker:text-amber-500" {...props} />,
                      ol: ({node, ...props}) => <ol className="list-decimal pl-6 mb-4 space-y-2 marker:text-amber-500" {...props} />,
                      h1: ({node, ...props}) => <h1 className="text-2xl font-bold mb-4 mt-6 text-white border-b border-white/10 pb-2" {...props} />,
                      h2: ({node, ...props}) => <h2 className="text-xl font-bold mb-3 mt-5 text-amber-400" {...props} />,
                      h3: ({node, ...props}) => <h3 className="text-lg font-bold mb-3 mt-4 text-white" {...props} />,
                      table: ({node, ...props}) => (
                        <div className="overflow-x-auto my-6 rounded-xl border border-white/10">
                          <table className="w-full text-left text-sm text-gray-200 border-collapse" {...props} />
                        </div>
                      ),
                      thead: ({node, ...props}) => <thead className="bg-white/10 text-white uppercase text-xs tracking-wider" {...props} />,
                      tbody: ({node, ...props}) => <tbody className="divide-y divide-white/5 bg-[#171717]" {...props} />,
                      tr: ({node, ...props}) => <tr className="hover:bg-white/5 transition-colors" {...props} />,
                      th: ({node, ...props}) => <th className="px-4 py-3 font-semibold text-white border-b border-white/10" {...props} />,
                      td: ({node, ...props}) => <td className="px-4 py-3 border-b border-white/5 text-gray-300 align-top" {...props} />,
                      blockquote: ({node, ...props}) => (
                        <blockquote className="border-l-4 border-amber-500/50 pl-4 py-1 my-4 bg-white/5 rounded-r-lg text-gray-300 italic" {...props} />
                      ),
                      code: ({node, ...props}) => (
                        <code className="bg-white/10 px-1.5 py-0.5 rounded text-amber-300 font-mono text-sm" {...props} />
                      )
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