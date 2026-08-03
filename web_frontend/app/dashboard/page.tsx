"use client";

import { Clock, Brain, Target, TrendingUp, BookOpen, PenTool, CheckSquare } from "lucide-react";
import Link from "next/link";

export default function MainDashboardPage() {
  return (
    <div className="flex flex-col h-screen bg-[#212121] overflow-y-auto w-full custom-scrollbar p-8 md:p-12">
      
      <div className="max-w-4xl mx-auto w-full animate-in fade-in slide-in-from-bottom-4 pt-10">
        
        {/* Welcome Header */}
        <div className="mb-10">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-2xl shadow-indigo-500/20 mb-6">
            <span className="text-white font-bold text-2xl">OS</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">Welcome to GSTU IR Ecosystem ✨</h1>
          <p className="text-gray-400 text-[16px] max-w-2xl leading-relaxed">
            Your centralized intelligence hub for International Relations. 
          </p>
        </div>

        {/* Productivity Monitor */}
        <div className="w-full bg-gradient-to-br from-[#1e1e1e] to-[#171717] border border-white/5 rounded-3xl p-8 shadow-2xl mb-10">
          <h3 className="text-sm font-bold text-gray-300 uppercase tracking-wider mb-6 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" /> Your Academic ROI & Impact
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="bg-black/20 border border-white/5 rounded-2xl p-5 border-b-2 border-b-indigo-500">
              <div className="text-3xl font-bold text-white mb-2 flex items-center gap-2"><Clock className="w-6 h-6 text-indigo-400"/> 12.5 <span className="text-sm text-gray-500 font-normal">hrs</span></div>
              <div className="text-[12px] font-medium text-gray-400 uppercase tracking-wide">Reading Time Saved</div>
            </div>
            <div className="bg-black/20 border border-white/5 rounded-2xl p-5 border-b-2 border-b-emerald-500">
              <div className="text-3xl font-bold text-white mb-2 flex items-center gap-2"><Brain className="w-6 h-6 text-emerald-400"/> +25%</div>
              <div className="text-[12px] font-medium text-gray-400 uppercase tracking-wide">Memory Retention</div>
            </div>
            <div className="bg-gradient-to-br from-amber-500/10 to-transparent border border-amber-500/20 rounded-2xl p-5 border-b-2 border-b-amber-500 relative overflow-hidden">
              <div className="absolute right-[-10px] bottom-[-10px] opacity-10"><Target className="w-24 h-24 text-amber-500" /></div>
              <div className="text-3xl font-bold text-amber-400 mb-2 flex items-center gap-2 relative z-10"><Target className="w-6 h-6"/> 3.45</div>
              <div className="text-[12px] font-medium text-amber-500/70 uppercase tracking-wide relative z-10">Predicted CGPA Boost (From 2.88)</div>
            </div>
          </div>
        </div>

        {/* Quick Action Cards */}
        <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4 ml-1">Quick Launch</h3>
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

      </div>
    </div>
  );
}