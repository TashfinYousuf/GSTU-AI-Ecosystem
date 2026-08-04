"use client";

import { useState, useEffect } from "react";
import { Clock, Brain, Target, TrendingUp, BookOpen, PenTool, CheckSquare, FileQuestion, Users, Lock, Loader2 } from "lucide-react";
import Link from "next/link";
import { createClient } from "../utils/supabase/client";
import { fetchAPI } from "../utils/api";

export default function MainDashboardPage() {
  const [userRole, setUserRole] = useState("guest"); 
  const [userName, setUserName] = useState("");
  const [stats, setStats] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadDashboardData() {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        setUserRole("guest");
        setIsLoading(false);
        return;
      }

      // 🔴 1. Get Real User Data & Role from Supabase
      const role = session.user.user_metadata?.role?.toLowerCase() || "student";
      const name = session.user.user_metadata?.full_name?.split(" ")[0] || "Scholar";
      setUserRole(role);
      setUserName(name);

      // 🔴 2. Fetch Real Stats from FastAPI Backend
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

        // 🔴 Strict Dynamic Action: If API fails, set stats to empty object so it shows 0 (no fake data)
        setStats({});
      } finally {
        setIsLoading(false);
      }
    }

    loadDashboardData();
  }, []);

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

        {/* 🔴 RBAC: Dynamic Analytics Monitor (100% Realtime, no fake data) */}
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