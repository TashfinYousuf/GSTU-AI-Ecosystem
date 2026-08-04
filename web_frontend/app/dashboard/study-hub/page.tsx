"use client";

import { useState } from "react";
import { Gamepad2, Star, Flame, CheckCircle, XCircle, ArrowRight, Trophy, LineChart, Swords, Brain, ShieldAlert } from "lucide-react";

export default function InteractiveStudyHubPage() {
  // Navigation State
  const [activeTab, setActiveTab] = useState("flashcards"); // flashcards, predictor, debate, battle
  
  // Gamification States
  const [xp, setXp] = useState(120);
  const [streak, setStreak] = useState(3);
  
  // Flashcard States
  const [topic, setTopic] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [cards, setCards] = useState<any[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
  const [difficulty, setDifficulty] = useState("Medium");

  // Dummy Generator for UI
  const handleGenerateCards = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setCards([
        { q: "What is the primary focus of Neorealism?", options: ["Human Nature", "Anarchic System", "Institutions", "Economy"], ans: "Anarchic System", exp: "Kenneth Waltz argued that the anarchic structure of the international system forces states to seek security." }
      ]);
      setIsGenerating(false);
      setCurrentIndex(0);
      setSelectedAnswer(null);
    }, 1500);
  };

  const handleAnswerSubmit = (opt: string) => {
    setSelectedAnswer(opt);
    const correct = opt === cards[currentIndex].ans;
    setIsCorrect(correct);
    if (correct) { setXp(prev => prev + 5); } 
    else { setStreak(0); }
  };

  const nextCard = () => {
    setCurrentIndex(prev => prev + 1);
    setSelectedAnswer(null);
    setIsCorrect(null);
  };

  return (
    <div className="min-h-screen bg-[#121212] text-gray-200 p-8 md:p-12 font-sans overflow-y-auto custom-scrollbar">
      
      {/* Header & Badges */}
      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Gamepad2 className="w-8 h-8 text-rose-500" /> Interactive Study Hub
          </h1>
          <p className="text-gray-400 mt-2 text-[15px]">Turn your academic syllabus into an addictive endless learning loop.</p>
        </div>
        
        {/* Dynamic XP Badge */}
        <div className="flex items-center gap-4 bg-[#1e1e1e] border border-white/10 px-5 py-2.5 rounded-2xl shadow-xl shrink-0">
          <div className="flex items-center gap-2">
            <Star className="w-5 h-5 text-amber-400" />
            <span className="font-bold text-lg text-white">{xp} <span className="text-xs text-gray-500 font-medium uppercase">XP</span></span>
          </div>
          <div className="w-px h-6 bg-white/10"></div>
          <div className="flex items-center gap-2">
            <Flame className={`w-5 h-5 ${streak > 2 ? 'text-orange-500 animate-pulse' : 'text-gray-500'}`} />
            <span className="font-bold text-lg text-white">{streak} <span className="text-xs text-gray-500 font-medium uppercase">Streak</span></span>
          </div>
        </div>
      </div>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 max-w-7xl mx-auto">
        
        {/* LEFT AREA: Hub Tools */}
        <div className="lg:col-span-8 space-y-6">
          
          {/* Sub Navigation */}
          <div className="flex flex-wrap gap-2 border-b border-white/10 pb-4">
            <button onClick={() => setActiveTab("flashcards")} className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === "flashcards" ? "bg-rose-500/20 text-rose-400" : "bg-[#1e1e1e] text-gray-400 hover:text-white"}`}>🃏 Flashcards</button>
            <button onClick={() => setActiveTab("predictor")} className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === "predictor" ? "bg-emerald-500/20 text-emerald-400" : "bg-[#1e1e1e] text-gray-400 hover:text-white"}`}>📈 Exam Predictor</button>
            <button onClick={() => setActiveTab("debate")} className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === "debate" ? "bg-indigo-500/20 text-indigo-400" : "bg-[#1e1e1e] text-gray-400 hover:text-white"}`}>⚔️ Debate Arena</button>
            <button onClick={() => setActiveTab("battle")} className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === "battle" ? "bg-amber-500/20 text-amber-400" : "bg-[#1e1e1e] text-gray-400 hover:text-white"}`}>🏆 Battle Mode</button>
          </div>

          {/* 🃏 TAB 1: FLASHCARDS */}
          {activeTab === "flashcards" && (
            <div className="space-y-6 animate-in fade-in">
              <div className="bg-[#1e1e1e] border border-white/5 rounded-3xl p-6 shadow-xl flex gap-4">
                <input 
                  type="text" 
                  value={topic} 
                  onChange={(e) => setTopic(e.target.value)} 
                  placeholder="Topic to Master (e.g., Geopolitics)" 
                  className="flex-1 bg-[#0a0a0a] border border-white/10 rounded-2xl px-5 py-4 text-white focus:outline-none focus:ring-2 focus:ring-rose-500 transition-all text-[15px]" 
                />
                <button 
                  onClick={handleGenerateCards} 
                  disabled={!topic || isGenerating} 
                  className="bg-rose-600 hover:bg-rose-700 text-white font-bold px-8 py-4 rounded-2xl transition-all shadow-lg"
                >
                  Generate 🎲
                </button>
              </div>

              {isGenerating ? (
                <div className="h-[400px] bg-[#1e1e1e] border border-white/5 rounded-3xl flex flex-col items-center justify-center text-rose-400/80 animate-pulse">
                  <Gamepad2 className="w-16 h-16 mb-4 animate-bounce" />
                  <p className="font-medium tracking-wide">Summoning {difficulty} Level Questions...</p>
                </div>
              ) : cards.length > 0 ? (
                <div className="bg-gradient-to-br from-[#1e1e1e] to-[#171717] border border-white/10 rounded-3xl p-8 shadow-2xl relative min-h-[400px]">
                  <div className="flex justify-between items-center mb-8 border-b border-white/10 pb-4">
                    <span className="text-sm font-bold text-gray-400">Card {currentIndex + 1} of {cards.length}</span>
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400">Level: {difficulty}</span>
                  </div>
                  <h2 className="text-xl md:text-2xl font-bold text-white mb-8 leading-relaxed">Q: {cards[currentIndex].q}</h2>
                  <div className="space-y-3">
                    {cards[currentIndex].options.map((opt: string, i: number) => {
                      let btnClass = "bg-[#0a0a0a] border-white/10 hover:border-rose-500/50 hover:bg-rose-500/5 text-gray-300";
                      if (selectedAnswer) {
                        if (opt === cards[currentIndex].ans) btnClass = "bg-emerald-500/20 border-emerald-500 text-emerald-100";
                        else if (opt === selectedAnswer) btnClass = "bg-rose-500/20 border-rose-500 text-rose-100";
                        else btnClass = "bg-[#0a0a0a] border-white/5 text-gray-600 opacity-50";
                      }
                      return (
                        <button key={i} onClick={() => handleAnswerSubmit(opt)} disabled={!!selectedAnswer} className={`w-full text-left px-6 py-4 rounded-2xl border transition-all font-medium text-[15px] ${btnClass}`}>
                          {opt}
                        </button>
                      );
                    })}
                  </div>
                  {selectedAnswer && (
                    <div className="mt-8 animate-in fade-in">
                      <div className={`p-5 rounded-2xl border ${isCorrect ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-rose-500/10 border-rose-500/30'}`}>
                        <h3 className={`text-lg font-bold mb-2 flex items-center gap-2 ${isCorrect ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {isCorrect ? <><CheckCircle className="w-5 h-5"/> Correct! +5 XP</> : <><XCircle className="w-5 h-5"/> Incorrect! -1.5 XP.</>}
                        </h3>
                        <p className="text-gray-300 text-[14.5px]"><span className="font-bold text-white">Explanation:</span> {cards[currentIndex].exp}</p>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="h-[400px] border-2 border-dashed border-white/10 rounded-3xl flex flex-col items-center justify-center text-gray-500">
                  <Gamepad2 className="w-12 h-12 mb-3 opacity-20" />
                  <p>Enter a topic to generate your first deck.</p>
                </div>
              )}
            </div>
          )}

          {/* 📈 TAB 2: EXAM PREDICTOR */}
          {activeTab === "predictor" && (
            <div className="bg-[#1e293b]/40 border border-emerald-500/20 rounded-3xl p-8 animate-in fade-in h-[500px]">
              <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2"><LineChart className="w-5 h-5 text-emerald-400"/> Predictive Exam Analytics</h3>
              <p className="text-sm text-gray-400 mb-6">AI analyzes past papers and current geopolitical trends from the Knowledge Base to predict upcoming exam topics.</p>
              <div className="flex gap-4 mb-8">
                <input type="text" placeholder="Enter Course Code (e.g., IR-202)" className="flex-1 bg-[#0f172a] border border-white/10 rounded-xl px-4 py-4 text-white focus:outline-none focus:border-emerald-500" />
                <button className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-8 py-4 rounded-xl transition-colors shadow-lg">Run Engine</button>
              </div>
            </div>
          )}

          {/* ⚔️ TAB 3: DEBATE ARENA */}
          {activeTab === "debate" && (
            <div className="bg-[#2a1215]/40 border border-indigo-500/20 rounded-3xl p-8 animate-in fade-in h-[500px]">
              <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2"><Swords className="w-5 h-5 text-indigo-400"/> AI Debate Arena</h3>
              <p className="text-sm text-gray-400 mb-6">Challenge the AI on any geopolitical topic. An unbiased AI Judge will score your factual accuracy.</p>
              <div className="space-y-5">
                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Debate Topic / Your Stance</label>
                  <textarea rows={3} placeholder="e.g., Sanctions are ineffective in modern geopolitics because..." className="w-full bg-[#1a0b0d] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500 resize-none"></textarea>
                </div>
                <button className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 rounded-xl transition-colors shadow-lg mt-2">Enter Arena 🥊</button>
              </div>
            </div>
          )}

          {/* 🏆 TAB 4: BATTLE MODE */}
          {activeTab === "battle" && (
            <div className="bg-[#291a0b]/40 border border-amber-500/20 rounded-3xl p-10 text-center animate-in fade-in h-[500px] flex flex-col justify-center items-center">
              <Trophy className="w-20 h-20 text-amber-500 mb-6 animate-bounce" />
              <h3 className="text-3xl font-bold text-white mb-3">1 VS 1 Battle Mode</h3>
              <p className="text-gray-400 mb-8 max-w-md">Compete against your batchmates in real-time MCQ battles based on your current syllabus.</p>
              <button className="bg-amber-500 hover:bg-amber-600 text-black font-black uppercase tracking-widest px-10 py-5 rounded-2xl transition-all shadow-[0_0_40px_rgba(245,158,11,0.3)] hover:scale-105">Find Opponent 🔍</button>
            </div>
          )}

        </div>

        {/* RIGHT AREA: AI Avatar & Leaderboard */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* Avatar Motivation */}
          <div className="bg-[#1e1e1e] border border-white/5 rounded-3xl p-6 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 rounded-full blur-3xl"></div>
            <h3 className="text-sm font-bold text-white-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-indigo-400" /> Mr. Atlas (AI Mentor)
            </h3>
            <div className="flex items-start gap-4">
              <img src="https://api.dicebear.com/7.x/bottts/svg?seed=Atlas&backgroundColor=6366f1" alt="Atlas" className="w-16 h-16 rounded-2xl bg-[#0a0a0a] border border-white/10 shadow-inner" />
              <div className="bg-[#0a0a0a] border border-white/10 p-4 rounded-2xl rounded-tl-none relative flex-1">
                {xp < 100 ? (
                  <p className="text-[13px] text-gray-300 italic">"Zero XP? Are you studying or just staring at the screen? Start swiping those flashcards!"</p>
                ) : streak > 2 ? (
                  <p className="text-[13px] text-emerald-300 italic font-medium">"Woah, {streak} streak! You are officially a geopolitical threat right now! Keep pushing!"</p>
                ) : (
                  <p className="text-[13px] text-gray-300 italic">"Okay, {xp} XP is a decent start. But your retention rate won't fix itself. Next card!"</p>
                )}
              </div>
            </div>
          </div>

          {/* Global Leaderboard */}
          <div className="bg-[#1e1e1e] border border-white/5 rounded-3xl p-6 shadow-xl">
            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-6 flex items-center gap-2">
              <Trophy className="w-4 h-4 text-amber-400" /> Live Leaderboard
            </h3>
            <div className="space-y-4">
              {[
                { name: "Fahim (IR 2.1)", xp: 3450, medal: "🥇" },
                { name: "Samia (IR 3.1)", xp: 2890, medal: "🥈" },
                { name: "Noman (IR 1.2)", xp: 2150, medal: "🥉" },
                { name: "You", xp: xp, medal: "4️⃣" },
              ].map((user, i) => (
                <div key={i} className={`flex items-center justify-between p-3 rounded-xl transition-all ${user.name === "You" ? "bg-amber-500/10 border border-amber-500/20" : "hover:bg-white/5"}`}>
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{user.medal}</span>
                    <span className={`font-semibold text-[14px] ${user.name === "You" ? "text-amber-400" : "text-gray-300"}`}>{user.name}</span>
                  </div>
                  <span className="font-bold text-gray-400 text-sm">{user.xp} XP</span>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}