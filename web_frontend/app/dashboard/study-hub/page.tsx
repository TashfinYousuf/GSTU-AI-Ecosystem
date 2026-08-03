"use client";

import { useState } from "react";
import { Gamepad2, Trophy, Flame, Star, CheckCircle, XCircle, ArrowRight, ShieldAlert } from "lucide-react";

export default function StudyHubPage() {
  const [activeTab, setActiveTab] = useState("flashcards");
  const [topic, setTopic] = useState("");
  
  // Gamification States (Based on your master blueprint)
  const [xp, setXp] = useState(125);
  const [streak, setStreak] = useState(2);
  const [difficulty, setDifficulty] = useState("Medium");
  
  // Flashcard Logic
  const [isGenerating, setIsGenerating] = useState(false);
  const [cards, setCards] = useState<any[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);

  const handleGenerateCards = () => {
    setIsGenerating(true);
    // Mocking the backend RAG delay
    setTimeout(() => {
      setCards([
        { q: "Which theory primarily focuses on the balance of power and survival in an anarchic system?", options: ["Liberalism", "Constructivism", "Neorealism", "Marxism"], ans: "Neorealism", exp: "Neorealism (Structural Realism) argues that the anarchic structure of the international system forces states to prioritize survival and power." },
        { q: "What concept describes a situation where one state's security actions threaten another?", options: ["Security Dilemma", "Hegemonic Stability", "Democratic Peace", "Soft Power"], ans: "Security Dilemma", exp: "Coined by John Herz, it explains how defensive measures by one state are perceived as offensive by others." }
      ]);
      setIsGenerating(false);
      setCurrentIndex(0);
      setSelectedAnswer(null);
      setIsCorrect(null);
    }, 1500);
  };

  const handleAnswerSubmit = (option: string) => {
    setSelectedAnswer(option);
    const correct = option === cards[currentIndex].ans;
    setIsCorrect(correct);
    
    if (correct) {
      setXp(prev => prev + 5);
      setStreak(prev => prev + 1);
      if (streak >= 3) setDifficulty("Hard");
    } else {
      setXp(prev => Math.max(0, prev - 1.5));
      setStreak(0);
      setDifficulty("Easy");
    }
  };

  const nextCard = () => {
    setSelectedAnswer(null);
    setIsCorrect(null);
    setCurrentIndex(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-[#121212] text-gray-200 p-8 md:p-12 font-sans overflow-y-auto custom-scrollbar">
      
      {/* Header */}
      <div className="mb-10 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Gamepad2 className="w-8 h-8 text-rose-500" /> Interactive Study Hub
          </h1>
          <p className="text-gray-400 mt-2 text-[15px]">Turn your academic syllabus into an addictive endless learning loop.</p>
        </div>
        
        {/* Dynamic XP Badge */}
        <div className="flex items-center gap-4 bg-[#1e1e1e] border border-white/10 px-5 py-2.5 rounded-2xl shadow-xl">
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

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 max-w-6xl mx-auto">
        
        {/* Left Area: Flashcards & Engine */}
        <div className="lg:col-span-8 space-y-6">
          
          {/* Controls */}
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
              className="bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white font-bold px-8 py-4 rounded-2xl transition-all shadow-lg shadow-rose-600/20"
            >
              Generate Set 🎲
            </button>
          </div>

          {/* Flashcard Engine */}
          {isGenerating ? (
            <div className="h-[400px] bg-[#1e1e1e] border border-white/5 rounded-3xl flex flex-col items-center justify-center text-rose-400/80 animate-pulse">
              <Gamepad2 className="w-16 h-16 mb-4 animate-bounce" />
              <p className="font-medium tracking-wide">Summoning {difficulty} Level Questions...</p>
            </div>
          ) : cards.length > 0 ? (
            <div className="bg-gradient-to-br from-[#1e1e1e] to-[#171717] border border-white/10 rounded-3xl p-8 shadow-2xl relative overflow-hidden min-h-[400px]">
              
              <div className="flex justify-between items-center mb-8 border-b border-white/10 pb-4">
                <span className="text-sm font-bold text-gray-400">Card {currentIndex + 1} of {cards.length}</span>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${difficulty === 'Hard' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'}`}>Level: {difficulty}</span>
              </div>

              <h2 className="text-xl md:text-2xl font-bold text-white mb-8 leading-relaxed">
                Q: {cards[currentIndex].q}
              </h2>

              <div className="space-y-3">
                {cards[currentIndex].options.map((opt: string, i: number) => {
                  let btnClass = "bg-[#0a0a0a] border-white/10 hover:border-rose-500/50 hover:bg-rose-500/5 text-gray-300";
                  if (selectedAnswer) {
                    if (opt === cards[currentIndex].ans) btnClass = "bg-emerald-500/20 border-emerald-500 text-emerald-100";
                    else if (opt === selectedAnswer) btnClass = "bg-rose-500/20 border-rose-500 text-rose-100";
                    else btnClass = "bg-[#0a0a0a] border-white/5 text-gray-600 opacity-50";
                  }

                  return (
                    <button 
                      key={i} 
                      onClick={() => handleAnswerSubmit(opt)}
                      disabled={!!selectedAnswer}
                      className={`w-full text-left px-6 py-4 rounded-2xl border transition-all font-medium text-[15px] ${btnClass}`}
                    >
                      {opt}
                    </button>
                  );
                })}
              </div>

              {/* Result Area */}
              {selectedAnswer && (
                <div className="mt-8 animate-in fade-in slide-in-from-bottom-4">
                  <div className={`p-5 rounded-2xl border ${isCorrect ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-rose-500/10 border-rose-500/30'}`}>
                    <h3 className={`text-lg font-bold mb-2 flex items-center gap-2 ${isCorrect ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {isCorrect ? <><CheckCircle className="w-5 h-5"/> Correct! +5 XP</> : <><XCircle className="w-5 h-5"/> Incorrect! -1.5 XP. Streak Broken.</>}
                    </h3>
                    <p className="text-gray-300 text-[14.5px] leading-relaxed"><span className="font-bold text-white">Explanation:</span> {cards[currentIndex].exp}</p>
                  </div>
                  
                  {currentIndex < cards.length - 1 ? (
                    <button onClick={nextCard} className="w-full mt-4 bg-white text-black hover:bg-gray-200 font-bold py-4 rounded-2xl flex items-center justify-center gap-2 transition-all">
                      Next Question <ArrowRight className="w-5 h-5" />
                    </button>
                  ) : (
                    <div className="w-full mt-4 bg-emerald-600 text-white font-bold py-4 rounded-2xl flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20">
                      <Trophy className="w-5 h-5" /> Set Completed!
                    </div>
                  )}
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

        {/* Right Area: Leaderboard & AI Avatar */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* Avatar Motivation */}
          <div className="bg-[#1e1e1e] border border-white/5 rounded-3xl p-6 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 rounded-full blur-3xl"></div>
            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
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