"use client";

import { useState, useEffect } from "react";
import { Clock, Brain, Target, TrendingUp, BookOpen, PenTool, CheckSquare, FileQuestion, Users, Lock, Loader2, Flame, X, Moon, Smile, Activity, } from "lucide-react";
import Link from "next/link";
import { createClient } from "../utils/supabase/client";
import { fetchAPI } from "../utils/api";

export default function MainDashboardPage() {
  const [userRole, setUserRole] = useState("guest"); 
  const [userName, setUserName] = useState("");
  const [stats, setStats] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  // 🔴 Toast & Logger States
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [showToast, setShowToast] = useState(false);
  const [logTopic, setLogTopic] = useState("");
  const [logMinutes, setLogMinutes] = useState("");
  const [isLogging, setIsLogging] = useState(false);

  // 🔴 Daily Logger Modal States
  const [showDailyModal, setShowDailyModal] = useState(false);
  const [logData, setLogData] = useState({ study_hours: "", sleep_hours: "", mood: "Focused" });

  const [mappingData, setMappingData] = useState<any[]>([]);

  useEffect(() => {
    async function loadDashboardData() {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        setUserRole("guest");
        setIsLoading(false);
        return;
      }

      // 1. Get Real User Data & Role from Supabase
      const role = session.user.user_metadata?.role?.toLowerCase() || "student";
      const name = session.user.user_metadata?.full_name?.split(" ")[0] || "Scholar";
      setUserRole(role);
      setUserName(name);

      // 2. Fetch Real Stats
      try {
        if (role === "student") {
          const res = await fetchAPI(`/academic/analytics/${session.user.id}`);
          setStats(res.data);
        } else if (role === "faculty" || role === "admin") {
          const res = await fetchAPI("/admin/analytics");
          setStats(res.data);
        }
      } catch (error) {
        console.error("API Error: Backend offline or endpoint missing.", error);
        setStats({}); // Fallback
      } finally {
        setIsLoading(false);
      }

      const todayDate = new Date().toISOString().split('T')[0];

      // 🔴 1. AI Push Notification (Toast) - ONLY ONCE A DAY
      const lastToast = localStorage.getItem("gstu_last_toast");
      if (lastToast !== todayDate && role !== "guest") {
        try {
          const toastRes = await fetchAPI("/logger/toast");
          if (toastRes && toastRes.message) {
            setToastMessage(toastRes.message);
            setTimeout(() => setShowToast(true), 1500); 
            setTimeout(() => setShowToast(false), 8000); 
            // Mark as shown for today
            localStorage.setItem("gstu_last_toast", todayDate);
          }
        } catch (e) {
          console.log("Toast notification system offline.");
        }
      }

      // 🔴 2. Auto-Popup Logger - ONLY ONCE A DAY
      const lastLogged = localStorage.getItem("gstu_last_daily_log");
      if (lastLogged !== todayDate && (role === "student" || role === "pro_scholar")) {
        // Delay popup to let user see dashboard first
        setTimeout(() => setShowDailyModal(true), 3000);
      }
      
      // 🔴 3. Student Mapping Data Fetch
      if (role === "student" || role === "pro_scholar") {
        try {
          const mapRes = await fetchAPI("/logger/mapping");
          if (mapRes.data) setMappingData(mapRes.data);
        } catch (e) { }
      }
    }

    loadDashboardData();
  }, []);

  
  // 🔴 Submit Daily Log
  const handleDailySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLogging(true);
    
    try {
      const res = await fetchAPI("/logger/daily-log", {
        method: "POST",
        body: JSON.stringify({
          study_hours: parseInt(logData.study_hours),
          sleep_hours: parseInt(logData.sleep_hours),
          mood: logData.mood
        })
      });
      
      // Save today's date in local storage so it doesn't pop up again today
      localStorage.setItem("gstu_last_daily_log", new Date().toISOString().split('T')[0]);
      setShowDailyModal(false);
      alert(res.message);
      
    } catch (error) {
      alert("Failed to save daily log.");
    } finally {
      setIsLogging(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-screen bg-[#212121] items-center justify-center text-indigo-500 flex-col gap-4 w-full">
        <Loader2 className="w-12 h-12 animate-spin" />
        <p className="font-medium tracking-widest text-sm uppercase text-gray-400">Syncing Ecosystem...</p>
      </div>
    );
  }
  

  return (
    <div className="flex flex-col h-screen bg-[#212121] overflow-y-auto w-full custom-scrollbar p-8 md:p-12">
      {/* 🔴 FLOATING TOAST NOTIFICATION */}
      {showToast && toastMessage && (
        <div className="fixed top-8 right-8 z-50 animate-in slide-in-from-right-10 fade-in duration-500">
          <div className="bg-[#1e1e1e] border border-emerald-500/30 text-white p-4 rounded-2xl shadow-[0_10px_40px_rgba(16,185,129,0.2)] flex items-start gap-4 max-w-sm">
            <div className="bg-emerald-500/20 p-2 rounded-full shrink-0">
              <Flame className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h4 className="font-bold text-sm text-gray-200">AI Assistant Says:</h4>
              <p className="text-[13px] text-emerald-100 mt-1 leading-snug">{toastMessage}</p>
            </div>
            <button onClick={() => setShowToast(false)} className="text-gray-500 hover:text-white shrink-0 mt-1">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
      
      {/* 🔴 AUTO-POPUP DAILY LOGGER MODAL */}
      {showDailyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-[#171717] border border-emerald-500/30 rounded-3xl p-8 max-w-md w-full shadow-2xl relative animate-in zoom-in-95">
            <button onClick={() => setShowDailyModal(false)} className="absolute top-4 right-4 text-gray-500 hover:text-white"><X className="w-5 h-5"/></button>
            
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center border-2 border-emerald-500/20">
                <Target className="w-8 h-8 text-emerald-400" />
              </div>
            </div>
            
            <h2 className="text-2xl font-bold text-white text-center mb-2">Daily Progress Sync</h2>
            <p className="text-sm text-gray-400 text-center mb-8">Log your vital stats for precise AI Student Mapping and study planning.</p>
            
            <form onSubmit={handleDailySubmit} className="space-y-5">
              <div className="flex items-center gap-4">
                <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-3 flex-1 flex flex-col">
                  <label className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1 flex items-center gap-1"><Clock className="w-3 h-3 text-indigo-400"/> Study Hours</label>
                  <input type="number" required min="0" max="24" value={logData.study_hours} onChange={(e) => setLogData({...logData, study_hours: e.target.value})} className="bg-transparent text-white text-xl font-bold focus:outline-none" placeholder="e.g. 4" />
                </div>
                <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-3 flex-1 flex flex-col">
                  <label className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1 flex items-center gap-1"><Moon className="w-3 h-3 text-purple-400"/> Sleep Hours</label>
                  <input type="number" required min="0" max="24" value={logData.sleep_hours} onChange={(e) => setLogData({...logData, sleep_hours: e.target.value})} className="bg-transparent text-white text-xl font-bold focus:outline-none" placeholder="e.g. 7" />
                </div>
              </div>
              
              <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-4">
                 <label className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1"><Smile className="w-3 h-3 text-amber-400"/> Today's Mood / Energy</label>
                 <select value={logData.mood} onChange={(e) => setLogData({...logData, mood: e.target.value})} className="w-full bg-transparent text-white text-sm focus:outline-none cursor-pointer">
                    <option className="bg-[#171717]">Highly Motivated 🔥</option>
                    <option className="bg-[#171717]">Focused 🎯</option>
                    <option className="bg-[#171717]">Tired but trying ☕</option>
                    <option className="bg-[#171717]">Burned out 🥀</option>
                 </select>
              </div>

              <button type="submit" disabled={isLogging} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-4 rounded-xl transition-all shadow-lg flex justify-center items-center gap-2">
                {isLogging ? <Loader2 className="w-5 h-5 animate-spin"/> : <><Activity className="w-5 h-5"/> Sync to Database</>}
              </button>
            </form>
          </div>
        </div>
      )}
      
      {/* 🔴 Only authentic Supabase roles will work now */}
      <div className="max-w-4xl mx-auto w-full animate-in fade-in slide-in-from-bottom-4 pt-10">
        
        {/* Welcome Header */}
        <div className="mb-10">
          <div className="w-16 h-16 rounded-full bg-[#f8f9fa] flex items-center justify-center shadow-2xl shadow-emerald-500/20 mb-6 p-1 overflow-hidden">
             <img src="/logo.png" alt="GSTU Logo" className="w-full h-full object-cover rounded-full" />
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">
            {userRole === "guest" ? "Welcome, Guest Scholar ✨" : `Welcome back, ${userName} ✨`}
          </h1>
          <p className="text-gray-400 text-[16px] max-w-2xl leading-relaxed">
            {userRole === "guest" 
              ? "Sign in to unlock personalized study plans, enterprise AI models, and document analytics." 
              : "Your centralized intelligence hub for International Relations."}
          </p>
        </div>


        {/* 🔴 STUDY LOGGER WIDGET (Hidden for Guests & Admins) */}
        {(userRole === "student" || userRole === "pro_scholar") && (
          <div className="mb-10 bg-gradient-to-r from-[#1e1e1e] to-[#121212] border border-indigo-500/30 rounded-3xl p-8 shadow-xl flex flex-col md:flex-row gap-8 items-center">
            <div className="flex-1">
              <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2"><Target className="w-5 h-5 text-indigo-400" /> Log Today's Progress</h3>
              <p className="text-sm text-gray-400 mb-4">Track your study hours. Every minute logged awards you XP on the Global Leaderboard.</p>
              
              <form onSubmit={handleDailySubmit} className="flex flex-col sm:flex-row gap-3">
                <input 
                  type="text" 
                  required
                  value={logTopic}
                  onChange={(e) => setLogTopic(e.target.value)}
                  placeholder="What did you study? (e.g., Cold War)" 
                  className="flex-1 bg-[#0a0a0a] border border-white/10 rounded-xl px-4 py-3 text-white text-sm focus:border-indigo-500 focus:outline-none"
                />
                <input 
                  type="number" 
                  required
                  min="1"
                  max="600"
                  value={logMinutes}
                  onChange={(e) => setLogMinutes(e.target.value)}
                  placeholder="Minutes" 
                  className="w-28 bg-[#0a0a0a] border border-white/10 rounded-xl px-4 py-3 text-white text-sm focus:border-indigo-500 focus:outline-none"
                />
                <button 
                  type="submit" 
                  disabled={isLogging}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-6 py-3 rounded-xl transition-all shadow-lg flex items-center justify-center disabled:opacity-50"
                >
                  {isLogging ? "Saving..." : "Log Time 🚀"}
                </button>
              </form>
            </div>
            
            <div className="w-32 h-32 shrink-0 rounded-full bg-indigo-500/10 border-4 border-indigo-500/20 flex flex-col items-center justify-center text-center shadow-[0_0_30px_rgba(79,70,229,0.15)]">
              <Clock className="w-8 h-8 text-indigo-400 mb-1" />
              <span className="text-xs font-bold text-gray-400 uppercase">Tracker</span>
            </div>
          </div>
        )}

        {/* 🔴 STUDENT MAPPING (DATA VISUALIZATION) */}
        {(userRole === "student" || userRole === "pro_scholar") && mappingData.length > 0 && (
          <div className="mb-10 bg-[#171717] border border-white/5 rounded-3xl p-8 shadow-xl animate-in fade-in slide-in-from-bottom-6">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-indigo-400" /> AI Student Mapping
                </h3>
                <p className="text-sm text-gray-400 mt-1">Your cognitive load analysis (Study vs Sleep hours)</p>
              </div>
              <div className="px-3 py-1 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-indigo-400 text-xs font-bold uppercase tracking-wider">
                Last 7 Days
              </div>
            </div>
            
            {/* Tailwind Pure CSS Bar Chart */}
            <div className="flex items-end justify-between gap-2 md:gap-4 h-48 mt-4 border-b border-white/10 pb-2">
              {mappingData.map((log: any, i: number) => {
                 // Calculate relative height (Max assumed 12 hours for visual scale)
                 const studyHours = log.study_minutes / 60;
                 const studyHeight = Math.min((studyHours / 12) * 100, 100); 
                 const sleepHeight = Math.min((log.sleep_hours / 12) * 100, 100);
                 
                 const dateLabel = new Date(log.created_at).toLocaleDateString('en-US', { weekday: 'short' });

                 return (
                   <div key={i} className="flex-1 flex flex-col items-center justify-end gap-2 group relative">
                     <div className="w-full flex justify-center gap-1 items-end h-full relative">
                       
                       {/* Hover Tooltip */}
                       <div className="absolute bottom-full mb-2 hidden group-hover:block bg-[#2a2a2a] text-xs p-3 rounded-xl whitespace-nowrap z-10 border border-white/10 shadow-2xl">
                         <div className="font-bold text-gray-200 mb-1">{new Date(log.created_at).toLocaleDateString()}</div>
                         <div className="text-indigo-400">Study: {studyHours.toFixed(1)} hrs</div>
                         <div className="text-purple-400">Sleep: {log.sleep_hours} hrs</div>
                         <div className="text-amber-400 mt-1 pt-1 border-t border-white/5">Mood: {log.mood}</div>
                       </div>
                       
                       {/* Study Bar */}
                       <div style={{ height: `${studyHeight}%` }} className="w-1/3 md:w-8 bg-indigo-500 rounded-t-md transition-all duration-500 ease-out group-hover:opacity-80"></div>
                       {/* Sleep Bar */}
                       <div style={{ height: `${sleepHeight}%` }} className="w-1/3 md:w-8 bg-purple-500/40 rounded-t-md transition-all duration-500 ease-out group-hover:opacity-80"></div>
                     </div>
                     <span className="text-[10px] md:text-xs font-bold text-gray-500 uppercase mt-2">
                        {dateLabel}
                     </span>
                   </div>
                 )
              })}
            </div>
            
            {/* Chart Legend */}
            <div className="flex gap-6 mt-6 justify-center">
               <div className="flex items-center gap-2 text-xs font-bold text-gray-400">
                 <div className="w-3 h-3 bg-indigo-500 rounded-sm"></div> Study Focus
               </div>
               <div className="flex items-center gap-2 text-xs font-bold text-gray-400">
                 <div className="w-3 h-3 bg-purple-500/40 rounded-sm"></div> Rest / Sleep
               </div>
            </div>
          </div>
        )}

        {/* 🔴 RBAC: Guest Banner */}
        {userRole === "guest" && (
          <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-2xl p-6 mb-10 flex items-center justify-between">
             <div>
               <h3 className="text-white font-bold mb-1 flex items-center gap-2"><Lock className="w-4 h-4 text-indigo-400"/> Guest Mode Active</h3>
               <p className="text-sm text-gray-400">You have 20 basic AI chat limits today. Unlock premium tools by logging in.</p>
             </div>
             <Link href="/auth/login" className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl transition-all shadow-lg">Authenticate Now</Link>
          </div>
        )}

        {/* 🔴 RBAC: Dynamic Analytics Monitor (100% Realtime) */}
        {userRole !== "guest" && stats && (
          <div className="w-full bg-gradient-to-br from-[#1e1e1e] to-[#171717] border border-white/5 rounded-3xl p-8 shadow-2xl mb-10">
            <h3 className="text-sm font-bold text-gray-300 uppercase tracking-wider mb-6 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-400" /> 
              {userRole === "faculty" ? "Faculty Productivity Monitor" : "Your Academic ROI & Impact"}
            </h3>
            
            {userRole === "student" ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="bg-black/20 border border-white/5 rounded-2xl p-5 border-b-2 border-b-indigo-500">
                  <div className="text-3xl font-bold text-white mb-2 flex items-center gap-2"><Clock className="w-6 h-6 text-indigo-400"/> {stats.hours_saved ?? 0} <span className="text-sm text-gray-500 font-normal">hrs</span></div>
                  <div className="text-[12px] font-medium text-gray-400 uppercase tracking-wide">Reading Time Saved</div>
                </div>
                <div className="bg-black/20 border border-white/5 rounded-2xl p-5 border-b-2 border-b-emerald-500">
                  <div className="text-3xl font-bold text-white mb-2 flex items-center gap-2"><Brain className="w-6 h-6 text-emerald-400"/> +{stats.retention_boost ?? 0}%</div>
                  <div className="text-[12px] font-medium text-gray-400 uppercase tracking-wide">Memory Retention</div>
                </div>
                <div className="bg-gradient-to-br from-amber-500/10 to-transparent border border-amber-500/20 rounded-2xl p-5 border-b-2 border-b-amber-500">
                  <div className="text-3xl font-bold text-amber-400 mb-2 flex items-center gap-2"><Target className="w-6 h-6"/> {stats.predicted_cgpa ?? "0.00"}</div>
                  <div className="text-[12px] font-medium text-amber-500/70 uppercase tracking-wide">Predicted CGPA Boost</div>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="bg-black/20 border border-white/5 rounded-2xl p-5 border-b-2 border-b-emerald-500">
                  <div className="text-3xl font-bold text-white mb-2 flex items-center gap-2"><Clock className="w-6 h-6 text-emerald-400"/> {stats.faculty_hours_saved ?? 0} <span className="text-sm text-gray-500 font-normal">hrs</span></div>
                  <div className="text-[12px] font-medium text-gray-400 uppercase tracking-wide">Grading & Prep Saved</div>
                </div>
                <div className="bg-black/20 border border-white/5 rounded-2xl p-5 border-b-2 border-b-purple-500">
                  <div className="text-3xl font-bold text-white mb-2 flex items-center gap-2"><FileQuestion className="w-6 h-6 text-purple-400"/> {stats.questions_generated ?? 0}</div>
                  <div className="text-[12px] font-medium text-gray-400 uppercase tracking-wide">Questions Generated</div>
                </div>
                <div className="bg-black/20 border border-white/5 rounded-2xl p-5 border-b-2 border-b-blue-500">
                  <div className="text-3xl font-bold text-white mb-2 flex items-center gap-2"><Users className="w-6 h-6 text-blue-400"/> {stats.active_students ?? 0}</div>
                  <div className="text-[12px] font-medium text-gray-400 uppercase tracking-wide">Active Students Monitored</div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 🔴 RBAC: Dynamic Quick Actions */}
        <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4 ml-1">Quick Launch Workspace</h3>
        
        {userRole === "guest" ? (
           <div className="grid grid-cols-1 md:grid-cols-3 gap-4 opacity-50 pointer-events-none">
             {[1, 2, 3].map((i) => (
                <div key={i} className="p-5 bg-[#1e1e1e] border border-white/5 rounded-2xl flex flex-col items-center text-center">
                  <Lock className="w-6 h-6 text-gray-500 mb-3" />
                  <h4 className="text-white font-semibold mb-1">Locked Tool</h4>
                  <p className="text-xs text-gray-500">Authentication Required</p>
                </div>
             ))}
           </div>
        ) : userRole === "student" ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link href="/dashboard/copilot" className="group p-5 bg-[#1e1e1e] border border-white/5 hover:border-indigo-500/30 hover:bg-white/5 rounded-2xl transition-all cursor-pointer">
              <BookOpen className="w-6 h-6 text-indigo-400 mb-3 group-hover:scale-110 transition-transform" />
              <h4 className="text-white font-semibold mb-1">Smart Routine</h4>
              <p className="text-xs text-gray-500">Generate personalized 7-day study plans.</p>
            </Link>
            <Link href="/dashboard/copilot" className="group p-5 bg-[#1e1e1e] border border-white/5 hover:border-purple-500/30 hover:bg-white/5 rounded-2xl transition-all cursor-pointer">
              <CheckSquare className="w-6 h-6 text-purple-400 mb-3 group-hover:scale-110 transition-transform" />
              <h4 className="text-white font-semibold mb-1">Mock Exam</h4>
              <p className="text-xs text-gray-500">Test your knowledge with AI assessments.</p>
            </Link>
            <Link href="/dashboard/scholar-hub" className="group p-5 bg-[#1e1e1e] border border-white/5 hover:border-emerald-500/30 hover:bg-white/5 rounded-2xl transition-all cursor-pointer">
              <PenTool className="w-6 h-6 text-emerald-400 mb-3 group-hover:scale-110 transition-transform" />
              <h4 className="text-white font-semibold mb-1">Research Hub</h4>
              <p className="text-xs text-gray-500">Find gaps and synthesize literature instantly.</p>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link href="/dashboard/copilot" className="group p-5 bg-[#1e1e1e] border border-white/5 hover:border-emerald-500/30 hover:bg-white/5 rounded-2xl transition-all cursor-pointer">
              <FileQuestion className="w-6 h-6 text-emerald-400 mb-3 group-hover:scale-110 transition-transform" />
              <h4 className="text-white font-semibold mb-1">Quiz Generator</h4>
              <p className="text-xs text-gray-500">Instantly generate class quizzes & MCQs.</p>
            </Link>
            <Link href="/dashboard/copilot" className="group p-5 bg-[#1e1e1e] border border-white/5 hover:border-purple-500/30 hover:bg-white/5 rounded-2xl transition-all cursor-pointer">
              <CheckSquare className="w-6 h-6 text-purple-400 mb-3 group-hover:scale-110 transition-transform" />
              <h4 className="text-white font-semibold mb-1">Grading Rubric</h4>
              <p className="text-xs text-gray-500">Create standard evaluation rubrics.</p>
            </Link>
            <Link href="/dashboard/department" className="group p-5 bg-[#1e1e1e] border border-white/5 hover:border-blue-500/30 hover:bg-white/5 rounded-2xl transition-all cursor-pointer">
              <Users className="w-6 h-6 text-blue-400 mb-3 group-hover:scale-110 transition-transform" />
              <h4 className="text-white font-semibold mb-1">Department Hub</h4>
              <p className="text-xs text-gray-500">Manage notices, analytics, and students.</p>
            </Link>
          </div>
        )}

      </div>
    </div>
  );
}