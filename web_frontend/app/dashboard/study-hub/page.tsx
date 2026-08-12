"use client";

import { useState, useEffect } from "react";
import { Gamepad2, Star, Flame, CheckCircle, XCircle, Trophy, LineChart, Swords, Brain, ShieldAlert, Loader2 } from "lucide-react";
import { fetchAPI } from "../../utils/api";
import { createClient } from "../../utils/supabase/client";

export default function InteractiveStudyHubPage() {
  const [activeModal, setActiveModal] = useState<"routine" | "debate" | "assessment" | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [userRole, setUserRole] = useState("student");

  const ADMIN_OVERRIDE_EMAIL = "yousufaltashfin@gmail.com";
  const [isBlocked, setIsBlocked] = useState(false);
  const [isCheckingAccess, setIsCheckingAccess] = useState(true);

  useEffect(() => {
    const checkAccess = async () => {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        const role = session.user.user_metadata?.role || "student";
        const email = session.user.email?.toLowerCase() || "";
        setUserRole(role);
        if (role === "faculty" && email !== ADMIN_OVERRIDE_EMAIL) setIsBlocked(true);
      }
      setIsCheckingAccess(false);
    };
    checkAccess();
  }, []);

  const [activeTab, setActiveTab] = useState("flashcards");

  // Predictor State
  const [courseCode, setCourseCode] = useState("");
  const [isPredicting, setIsPredicting] = useState(false);
  const [predictions, setPredictions] = useState<any[]>([]);

  // Debate State
  const [debateStance, setDebateStance] = useState("");
  const [aiPersona, setAiPersona] = useState("Aggressive Realist");
  const [isDebating, setIsDebating] = useState(false);
  
  const [debateDuration, setDebateDuration] = useState(5); 
  const [timeLeft, setTimeLeft] = useState<number | null>(null); 
  const [debateHistory, setDebateHistory] = useState<any[]>([]); 
  const [judgeVerdict, setJudgeVerdict] = useState<any>(null);
  const [arenaStarted, setArenaStarted] = useState(false);
  
  // Gamification States
  const [xp, setXp] = useState(0);
  const [streak, setStreak] = useState(0);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  
  // Flashcard States
  const [topic, setTopic] = useState("");
  const [cards, setCards] = useState<any[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
  const [difficulty, setDifficulty] = useState("Medium");
  const [isGenerating, setIsGenerating] = useState(false);

  // Battle Mode State
  const [isSearching, setIsSearching] = useState(false);

  const handleFindOpponent = () => {
    setIsSearching(true);
    setTimeout(() => {
      alert("No opponents currently online in your batch. Try challenging a bot in the Debate Arena for now!");
      setIsSearching(false);
    }, 3500);
  };

  // 🔴 1. DYNAMIC FLASHCARDS
  const handleGenerateCards = async () => {
    setIsGenerating(true);
    setCards([]);
    try {
      const res = await fetchAPI("/study/gamify", {
        method: "POST",
        body: JSON.stringify({ topic, feature_type: "flashcards", extra_data: { difficulty } })
      });
      if (res.data && res.data.flashcards) {
        const formatted = res.data.flashcards.map((c: any) => ({
          q: c.q, options: c.options, ans: c.correct_option, exp: c.explanation
        }));
        setCards(formatted);
      }
    } catch (error) {
      alert("Failed to generate flashcards.");
    } finally {
      setIsGenerating(false);
      setCurrentIndex(0);
      setSelectedAnswer(null);
    }
  };

  // 🔴 2. DYNAMIC EXAM PREDICTOR
  const handlePredictExam = async () => {
    setIsPredicting(true);
    try {
      const res = await fetchAPI("/study/gamify", {
        method: "POST",
        body: JSON.stringify({ topic: courseCode, feature_type: "predictor", extra_data: {} })
      });
      if (res.data && res.data.predictions) {
        setPredictions(res.data.predictions);
      }
    } catch (error) {
      alert("Failed to predict exam topics.");
    } finally {
      setIsPredicting(false);
    }
  };

  // 🔴 Fetch Initial Gamification Data & SET UP REALTIME SUBSCRIPTION
  useEffect(() => {
    let isMounted = true;
    const supabase = createClient();

    // Function to load the absolute truth from the database
    async function loadGamification() {
      try {
        const res = await fetchAPI("/study/profile");
        if (res.status === "success" && isMounted) {
          setXp(res.xp);
          setStreak(res.streak);
          setLeaderboard(res.leaderboard || []);
        }
      } catch (error) {
        console.error("Failed to load profile data");
      }
    }

    // 1. Initial Load
    loadGamification();

    // 2. ⚡ THE MAGIC: Supabase Realtime WebSocket Connection
    const profileSubscription = supabase
      .channel('live-leaderboard')
      .on(
        'postgres_changes',
        { 
          event: 'UPDATE', 
          schema: 'public', 
          table: 'user_profiles' 
        },
        (payload) => {
          console.log("⚡ Realtime Update Detected:", payload);
          // Whenever ANY user's profile updates (XP changes), instantly re-sync the leaderboard!
          loadGamification();
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          console.log("🟢 Connected to GSTU Realtime Network");
        }
      });

    // Cleanup subscription on unmount
    return () => {
      isMounted = false;
      supabase.removeChannel(profileSubscription);
    };
  }, []);

  const getAtlasQuote = () => {
    if (xp === 0) return "Zero XP? Are you studying or just staring at the screen? Start swiping those flashcards!";
    if (streak > 2) return `Woah, ${streak} streak! You are officially a geopolitical threat right now! Keep pushing!`;
    return `Okay, ${xp} XP is a decent start. But your retention rate won't fix itself. Next card!`;
  };

  const handleAnswerSubmit = (opt: string) => {
      setSelectedAnswer(opt);
      const correct = opt === cards[currentIndex].ans;
      setIsCorrect(correct);
      const delta = correct ? 5 : -2.5; // 🔴 Updated to -2.5 per requirement
      setXp(prev => Math.max(0, prev + delta));
      if (!correct) setStreak(0);
      else setStreak(prev => prev + 1);
      
      fetchAPI(`/study/xp?amount=${delta}`, { method: "POST" }).catch(err =>
        console.error("Failed to persist XP:", err)
      );
    };

  const nextCard = () => {
    setCurrentIndex(prev => prev + 1);
    setSelectedAnswer(null);
    setIsCorrect(null);
  };

  // ==========================================
  // ⏱️ TIMER LOGIC
  // ==========================================
  useEffect(() => {
    if (timeLeft === null || timeLeft <= 0 || judgeVerdict) return;
    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev !== null && prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [timeLeft, judgeVerdict]);

  // ==========================================
  // ⚔️ START/SEND ARGUMENT LOGIC
  // ==========================================
  const handleStartDebate = async () => {
    if (!debateStance.trim()) return;

    const currentInput = debateStance;
    const newHistory = [...debateHistory, { role: "User", content: currentInput }];
    
    setDebateHistory(newHistory);
    setDebateStance(""); 
    setIsDebating(true); 

    try {
      // 🔴 FIX: Changed from /powerups/gamify to /study/gamify
      const res = await fetchAPI("/study/gamify", {
        method: "POST",
        body: JSON.stringify({ 
          topic: currentInput, 
          feature_type: "debate", 
          extra_data: { history: newHistory } 
        })
      });

      if (res?.data) {
        const aiResponseText = res.data.ai_response || res.data;
        setDebateHistory(prev => [...prev, { role: "AI", content: aiResponseText }]);
      } else {
        alert("Failed to get AI response.");
      }
    } catch (error) {
      console.error("Debate Error:", error);
      alert("Network error during debate. Ensure API keys are active.");
    } finally {
      setIsDebating(false);
    }
  };

  // ==========================================
  // ⚖️ SUMMON JUDGE AI LOGIC
  // ==========================================
  const handleSummonJudge = async () => {
    if (debateHistory.length === 0) {
      alert("No debate history to judge!");
      return;
    }
    
    setIsDebating(true); 
    try {
      const transcript = debateHistory.map((m) => `${m.role}: ${m.content}`).join("\n");
      
      // 🔴 FIX: Changed endpoint to /study/gamify
      const res = await fetchAPI("/study/gamify", {
        method: "POST",
        body: JSON.stringify({ 
          topic: "Evaluate this debate", 
          feature_type: "judge", 
          extra_data: { transcript: transcript } 
        })
      });

      if (res?.data) {
        setJudgeVerdict(res.data);
        // 🔴 AWARD XP IF USER WINS!
        if (res.data.winner?.toLowerCase().includes("user")) {
           const reward = debateDuration;
           fetchAPI(`/study/xp?amount=${reward}`, { method: "POST" })
             .then(xpres => setXp(xpres.xp))
             .catch(e => console.error(e));
        }
      } else {
        alert("⚠️ Judge AI failed to evaluate. Try again.");
      }
    } catch (error) {
      console.error("Judge API Error:", error);
      alert("⚠️ Network Error while summoning the Judge.");
    } finally {
      setIsDebating(false);
    }
  };
  
  if (isCheckingAccess) return null;
  if (isBlocked) {
    return (
      <div className="min-h-screen bg-[#121212] flex flex-col items-center justify-center text-gray-400">
        <ShieldAlert className="w-12 h-12 mb-4 opacity-40" />
        <p>Interactive Study Hub is a student-only module.</p>
      </div>
    );
  }

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

          {/* TAB 1: FLASHCARDS */}
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
                  {isGenerating ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> : "Generate 🎲"}
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
                      {currentIndex < cards.length - 1 && (
                        <button onClick={() => { setCurrentIndex(prev => prev + 1); setSelectedAnswer(null); setIsCorrect(null); }} className="mt-4 w-full bg-white/10 hover:bg-white/20 text-white font-bold py-3 rounded-xl transition-colors">
                          Next Card ➡️
                        </button>
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
          )}

          {/* TAB 2: EXAM PREDICTOR */}
          {activeTab === "predictor" && (
            <div className="bg-[#1e293b]/40 border border-emerald-500/20 rounded-3xl p-8 animate-in fade-in min-h-[500px]">
              <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2"><LineChart className="w-5 h-5 text-emerald-400"/> Predictive Exam Analytics</h3>
              <p className="text-sm text-gray-400 mb-6">AI analyzes past papers and current geopolitical trends from the Knowledge Base to predict upcoming exam topics.</p>
              <div className="flex gap-4 mb-8">
                <input type="text" value={courseCode} onChange={(e) => setCourseCode(e.target.value)} placeholder="Enter Course Code (e.g., IR-202)" className="flex-1 bg-[#0f172a] border border-white/10 rounded-xl px-4 py-4 text-white focus:outline-none focus:border-emerald-500" />
                <button onClick={handlePredictExam} disabled={!courseCode || isPredicting} className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold px-8 py-4 rounded-xl transition-colors shadow-lg">
                  {isPredicting ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> : "Run Engine"}
                </button>
              </div>

              <div className="space-y-4">
                {predictions.map((pred, i) => (
                  <div key={i} className="p-5 bg-[#0f172a] border border-white/5 rounded-xl flex justify-between items-center">
                    <div>
                      <h4 className="text-white font-bold text-lg">{pred.topic}</h4>
                      <p className="text-sm text-gray-400 mt-1">{pred.reason}</p>
                    </div>
                    <div className="text-center bg-emerald-500/10 px-4 py-2 rounded-lg border border-emerald-500/20">
                      <span className="block text-2xl font-black text-emerald-400">{pred.probability}%</span>
                      <span className="text-[10px] uppercase font-bold text-emerald-500">Probability</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 3: DEBATE ARENA */}
          {activeTab === "debate" && (
            <div className="bg-[#2a1215]/40 border border-indigo-500/20 rounded-3xl p-8 animate-in fade-in min-h-[500px]">
              <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2"><Swords className="w-5 h-5 text-indigo-400"/> AI Debate Arena</h3>
              <p className="text-sm text-gray-400 mb-6">Challenge the AI on geopolitics. An unbiased AI Judge will score your factual accuracy.</p>
              
              {!arenaStarted && !judgeVerdict ? (
                <div className="space-y-5 max-w-lg mx-auto bg-[#1a0b0d] p-8 rounded-2xl border border-white/5">
                  <div>
                    <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">⏱️ Select Duration</label>
                    <select value={debateDuration} onChange={(e) => setDebateDuration(Number(e.target.value))} className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none">
                      <option value={5}>5 Minutes</option>
                      <option value={10}>10 Minutes</option>
                      <option value={15}>15 Minutes</option>
                    </select>
                  </div>
                  <button onClick={() => { setArenaStarted(true); setTimeLeft(debateDuration * 60); setDebateHistory([]); setJudgeVerdict(null); }} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 rounded-xl shadow-lg mt-2">
                    Initialize Debate Arena 🥊
                  </button>
                </div>
              ) : (
                <div className="space-y-6">
                  {!judgeVerdict && (
                    <div className="flex justify-between items-center bg-[#1a0b0d] p-4 rounded-xl border border-white/5">
                      <h3 className={`text-2xl font-bold ${timeLeft! < 60 ? 'text-rose-500 animate-pulse' : 'text-white'}`}>
                        ⏱️ {Math.floor(timeLeft! / 60)}:{(timeLeft! % 60).toString().padStart(2, '0')}
                      </h3>
                      <button onClick={() => setTimeLeft(0)} className="px-4 py-2 bg-rose-600/20 text-rose-400 rounded-lg text-sm font-bold hover:bg-rose-600/40">
                        End Early 🛑
                      </button>
                    </div>
                  )}

                  <div className="space-y-4 max-h-[400px] overflow-y-auto custom-scrollbar p-2">
                    {debateHistory.map((msg, i) => (
                      <div key={i} className={`p-4 rounded-xl border ${msg.role === 'User' ? 'bg-indigo-500/10 border-indigo-500/20 ml-auto max-w-[80%]' : 'bg-[#171717] border-white/10 mr-auto max-w-[80%]'}`}>
                        <span className={`text-[11px] font-bold uppercase block mb-1 ${msg.role === 'User' ? 'text-indigo-400' : 'text-gray-400'}`}>{msg.role}:</span>
                        <p className="text-gray-200 text-[15px]">{msg.content}</p>
                      </div>
                    ))}
                  </div>

                  {timeLeft === 0 && !judgeVerdict ? (
                    <div className="text-center p-6 border border-amber-500/30 bg-amber-500/10 rounded-2xl">
                      <h3 className="text-xl font-bold text-amber-400 mb-4">⏳ Time's Up!</h3>
                      <button onClick={handleSummonJudge} disabled={isDebating} className="bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-bold px-8 py-4 rounded-xl shadow-[0_0_15px_rgba(245,158,11,0.3)]">
                        {isDebating ? "Analyzing Facts..." : "Summon Judge AI for Verdict ⚖️"}
                      </button>
                    </div>
                  ) : !judgeVerdict ? (
                    <div className="flex gap-3">
                      <input type="text" value={debateStance} onChange={(e) => setDebateStance(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && handleStartDebate()} placeholder="Type your argument..." className="flex-1 bg-[#1a0b0d] border border-white/10 rounded-xl px-5 py-4 text-white focus:outline-none focus:border-indigo-500" />
                      <button onClick={handleStartDebate} disabled={!debateStance || isDebating} className="bg-indigo-600 hover:bg-indigo-700 text-white px-8 rounded-xl font-bold disabled:opacity-50">
                        Send 💬
                      </button>
                    </div>
                  ) : null}

                  {judgeVerdict && (
                    <div className="bg-[#171717] border border-emerald-500/30 p-8 rounded-3xl animate-in slide-in-from-bottom-4 shadow-2xl">
                      <h3 className="text-2xl font-bold text-center text-emerald-400 mb-6">🏆 WINNER: {judgeVerdict.winner}</h3>
                      <div className="grid grid-cols-2 gap-4 mb-6">
                        <div className="text-center p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
                          <p className="text-3xl font-black text-indigo-400">{judgeVerdict.user_score}</p>
                          <p className="text-xs uppercase font-bold text-gray-400 mt-1">Your Score</p>
                        </div>
                        <div className="text-center p-4 bg-gray-800 border border-white/10 rounded-xl">
                          <p className="text-3xl font-black text-gray-300">{judgeVerdict.ai_score}</p>
                          <p className="text-xs uppercase font-bold text-gray-400 mt-1">AI Score</p>
                        </div>
                      </div>
                      <div className="bg-[#0a0a0a] p-5 rounded-xl border border-white/5">
                        <p className="text-amber-400 font-bold mb-2 flex items-center gap-2">⚖️ Judge Summary:</p>
                        <p className="text-gray-300 text-[14.5px] leading-relaxed">{judgeVerdict.verdict_summary}</p>
                      </div>
                      <button onClick={() => { setArenaStarted(false); setJudgeVerdict(null); setDebateHistory([]); setTimeLeft(null); }} className="w-full mt-6 bg-white/10 hover:bg-white/20 text-white font-bold py-3 rounded-xl transition-colors">
                        Start New Debate 🔄
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: BATTLE MODE */}
          {activeTab === "battle" && (
            <div className="bg-[#291a0b]/40 border border-amber-500/20 rounded-3xl p-10 text-center animate-in fade-in h-[500px] flex flex-col justify-center items-center relative overflow-hidden">
              {isSearching && <div className="absolute inset-0 bg-amber-500/5 animate-pulse rounded-3xl"></div>}
              
              <Trophy className={`w-20 h-20 text-amber-500 mb-6 ${isSearching ? 'animate-spin' : 'animate-bounce'}`} />
              <h3 className="text-3xl font-bold text-white mb-3">1 VS 1 Battle Mode</h3>
              <p className="text-gray-400 mb-8 max-w-md relative z-10">Compete against your batchmates in real-time MCQ battles based on your current syllabus.</p>
              
              <button 
                onClick={handleFindOpponent}
                disabled={isSearching}
                className="bg-amber-500 hover:bg-amber-600 disabled:bg-amber-700/50 text-black disabled:text-gray-300 font-black uppercase tracking-widest px-10 py-5 rounded-2xl transition-all shadow-[0_0_40px_rgba(245,158,11,0.3)] hover:scale-105 disabled:hover:scale-100 flex items-center gap-3 relative z-10"
              >
                {isSearching ? (
                  <><Loader2 className="w-5 h-5 animate-spin" /> Searching Server...</>
                ) : (
                  "Find Opponent 🔍"
                )}
              </button>
            </div>
          )}

        </div>

        {/* RIGHT AREA: AI Avatar & Leaderboard */}
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
                <p className="text-[13px] italic font-medium text-emerald-300">
                  "{getAtlasQuote()}"
                </p>
              </div>
            </div>
          </div>

          {/* Global Leaderboard */}
          <div className="bg-[#1e1e1e] border border-white/5 rounded-3xl p-6 shadow-xl">
            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-6 flex items-center gap-2">
              <Trophy className="w-4 h-4 text-amber-400" /> Live Leaderboard
            </h3>
            <div className="space-y-4">
              {leaderboard.length > 0 ? (
                leaderboard.map((user, i) => {
                  const medals = ["🥇", "🥈", "🥉"];
                  const medal = i < 3 ? medals[i] : "🏅";
                  return (
                    <div key={i} className="flex items-center justify-between p-3 rounded-xl transition-all hover:bg-white/5">
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{medal}</span>
                        <span className="font-semibold text-[14px] text-gray-300 capitalize">{user.name || "Scholar"}</span>
                      </div>
                      <span className="font-bold text-gray-400 text-sm">{user.xp} XP</span>
                    </div>
                  );
                })
              ) : (
                <div className="text-center text-gray-500 py-4 text-sm">No leaderboard data yet.</div>
              )}

              {/* CURRENT USER HIGHLIGHT */}
              <div className="flex items-center justify-between p-3 rounded-xl transition-all bg-amber-500/10 border border-amber-500/20 mt-4">
                <div className="flex items-center gap-3">
                  <span className="text-xl">✨</span>
                  <span className="font-semibold text-[14px] text-amber-400">You</span>
                </div>
                <span className="font-bold text-gray-400 text-sm">{xp} XP</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}