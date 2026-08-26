"use client";

import { motion, Variants } from "framer-motion";
import Link from "next/link";
import { 
  Brain, Swords, Target, LineChart, Sparkles, 
  Layers, Rocket, Database, Code2, Cpu, ChevronRight, 
  GraduationCap, Users, ShieldCheck, ArrowRight, ChevronDown
} from "lucide-react";

export default function LandingPage() {
  // Animation Variants with explicit TypeScript typing and 'as const' for ease
  const fadeUp: Variants = {
    hidden: { opacity: 0, y: 40 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: "easeOut" as const } }
  };

  const staggerContainer: Variants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.2 }
    }
  };

  const slideLeft: Variants = {
    hidden: { opacity: 0, x: -50 },
    visible: { opacity: 1, x: 0, transition: { duration: 0.8, ease: "easeOut" as const } }
  };

  const slideRight: Variants = {
    hidden: { opacity: 0, x: 50 },
    visible: { opacity: 1, x: 0, transition: { duration: 0.8, ease: "easeOut" as const } }
  };

  return (
    <div className="min-h-dvh bg-[#050505] text-gray-200 selection:bg-indigo-500/30 overflow-hidden font-sans">
      
      {/* =========================================
          1. HERO SECTION (The Hook)
          ========================================= */}
      <section className="relative min-h-dvh flex flex-col justify-center items-center text-center px-6 pt-20">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-600/20 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-emerald-600/10 rounded-full blur-[120px] pointer-events-none" />

        <motion.div 
          initial="hidden" animate="visible" variants={staggerContainer}
          className="relative z-10 max-w-5xl mx-auto flex flex-col items-center"
        >
          {/* Medium-Big GSTU AI Ecosystem Header */}
          <motion.div variants={fadeUp} className="mb-6">
            <span className="px-6 py-2.5 rounded-full border border-white/10 bg-white/5 backdrop-blur-md text-xl md:text-2xl font-bold tracking-wider uppercase text-indigo-400 flex items-center gap-2">
              <Sparkles className="w-5 h-5" /> GSTU AI Ecosystem
            </span>
          </motion.div>
          
          {/* Subtitle / Main Headline floating up smoothly */}
          <motion.h1 variants={fadeUp} className="text-3xl md:text-5xl lg:text-6xl font-black text-white tracking-tight mb-6 leading-tight">
            The Next Generation of <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-cyan-400">
              Academic Intelligence.
            </span>
          </motion.h1>
          
          <motion.p variants={fadeUp} className="text-base md:text-lg text-gray-400 max-w-2xl mx-auto mb-12 leading-relaxed">
            Transforming traditional university syllabuses into an addictive, endless learning loop. Powered by multi-agent AI, real-time gamification, and enterprise-grade architecture.
          </motion.p>
        </motion.div>
      </section>

      {/* =========================================
          1.5. MID-SECTION BRIDGE (Discover the Vision)
          ========================================= */}
      <div className="py-12 flex flex-col items-center justify-center text-center relative z-10">
        <motion.div 
          initial={{ opacity: 0, y: -10 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ delay: 1, duration: 1, repeat: Infinity, repeatType: "reverse" }}
          className="flex flex-col items-center text-gray-400 text-mx tracking-widest uppercase gap-2"
        >
          <span>Discover the Vision</span>
          <ChevronDown className="w-5 h-5 text-indigo-400 animate-bounce" />
        </motion.div>
      </div>

      {/* =========================================
          2. VISION & IMPACT (The Story)
          ========================================= */}
      <section className="py-32 px-6 relative z-10">
        

        <motion.div 
          initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }}
          variants={fadeUp}
          className="max-w-4xl mx-auto text-center"
        >
          <h2 className="text-3xl md:text-5xl font-bold text-white mb-6">Built for Excellence. <br/>Designed for <span className="text-emerald-400">Impact.</span></h2>
          <p className="text-xl text-gray-400 leading-relaxed">
            Our ambition goes beyond a simple chatbot. We envisioned a 24/7 autonomous copilot that bridges the gap between complex geopolitical theories and modern student psychology. By merging cognitive science with high-speed LLMs, we are setting a new standard for EdTech in Bangladesh.
          </p>
        </motion.div>
      </section>

      {/* Unlock Dashboard Button Positioned Lower with Special Glow */}
        <motion.div variants={fadeUp} className="mt-4 flex flex-col items-center">
          <Link href="/auth/login">
            <button className="group relative inline-flex items-center justify-center px-10 py-4 font-bold text-white transition-all duration-200 bg-indigo-600/30 border border-indigo-500/40 rounded-full hover:bg-indigo-600/50 hover:scale-105 shadow-[0_0_30px_rgba(99,102,241,0.3)] overflow-hidden">
              <span className="absolute inset-0 w-full h-full -mt-1 rounded-lg opacity-30 bg-gradient-to-b from-transparent via-transparent to-black" /> 
              <span className="relative flex items-center gap-2 text-base">
                Unlock Dashboard <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </span>
            </button>
          </Link>
        </motion.div>

      {/* =========================================
          3. THE MOAT / CORE FEATURES (Alternating Slides)
          ========================================= */}
      <section className="py-24 px-6 overflow-hidden">
        <div className="max-w-7xl mx-auto space-y-32">
          
          {/* Feature 1: Flashcards */}
          <motion.div 
            initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }}
            className="flex flex-col lg:flex-row items-center gap-16"
          >
            <motion.div variants={slideLeft} className="lg:w-1/2">
              <div className="w-16 h-16 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl flex items-center justify-center mb-6">
                <Brain className="w-8 h-8 text-indigo-400" />
              </div>
              <h3 className="text-3xl md:text-4xl font-bold text-white mb-4">Adaptive AI Flashcards</h3>
              <p className="text-gray-400 text-lg leading-relaxed">
                Experience an addictive MCQ engine powered by live RAG context. The AI generates obscure, highly analytical questions dynamically. Correct answers push your global rank, while mistakes train the AI to focus on your weaknesses.
              </p>
            </motion.div>
            <motion.div variants={slideRight} className="lg:w-1/2 w-full h-[400px] bg-gradient-to-br from-[#121212] to-[#0a0a0a] border border-white/10 rounded-3xl relative overflow-hidden shadow-2xl flex items-center justify-center group">
              <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-5 group-hover:opacity-10 transition-opacity"></div>
              <div className="p-8 bg-black/40 backdrop-blur-xl border border-white/5 rounded-2xl w-3/4 transform group-hover:scale-105 transition-transform duration-500">
                <div className="h-4 w-1/3 bg-indigo-500/20 rounded-full mb-4"></div>
                <div className="h-6 w-3/4 bg-white/10 rounded-full mb-8"></div>
                <div className="space-y-3">
                  <div className="h-10 w-full bg-white/5 rounded-xl border border-white/5"></div>
                  <div className="h-10 w-full bg-indigo-500/10 border border-indigo-500/30 rounded-xl"></div>
                </div>
              </div>
            </motion.div>
          </motion.div>

          {/* Feature 2: Debate Arena */}
          <motion.div 
            initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }}
            className="flex flex-col lg:flex-row-reverse items-center gap-16"
          >
            <motion.div variants={slideRight} className="lg:w-1/2">
              <div className="w-16 h-16 bg-rose-500/10 border border-rose-500/20 rounded-2xl flex items-center justify-center mb-6">
                <Swords className="w-8 h-8 text-rose-400" />
              </div>
              <h3 className="text-3xl md:text-4xl font-bold text-white mb-4">Live Debate Arena</h3>
              <p className="text-gray-400 text-lg leading-relaxed">
                Step into the ring with an aggressive, sub-40-word AI debater. Back up your geopolitical claims under a strict server-authoritative timer. When the clock runs out, an unbiased AI Judge evaluates the transcript and awards massive XP for victory.
              </p>
            </motion.div>
            <motion.div variants={slideLeft} className="lg:w-1/2 w-full h-[400px] bg-gradient-to-br from-[#1a0b0d] to-[#0a0a0a] border border-rose-500/10 rounded-3xl relative overflow-hidden shadow-2xl flex items-center justify-center">
              <Swords className="w-32 h-32 text-rose-500/20 absolute" />
              <div className="text-center z-10">
                <div className="text-5xl font-black text-white tracking-widest">05:00</div>
                <div className="text-sm font-bold text-rose-400 tracking-widest uppercase mt-2">Server Authoritative</div>
              </div>
            </motion.div>
          </motion.div>

          {/* Feature 3: Faculty Copilot */}
          <motion.div 
            initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }}
            className="flex flex-col lg:flex-row items-center gap-16"
          >
            <motion.div variants={slideLeft} className="lg:w-1/2">
              <div className="w-16 h-16 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl flex items-center justify-center mb-6">
                <ShieldCheck className="w-8 h-8 text-emerald-400" />
              </div>
              <h3 className="text-3xl md:text-4xl font-bold text-white mb-4">The Faculty Copilot</h3>
              <p className="text-gray-400 text-lg leading-relaxed">
                We didn't forget the educators. The system includes strict Role-Based Access Control (RBAC) hiding faculty tools from students. Generate 10-seed analytical MCQs, draft department notices instantly, and utilize AI Grading Rubrics to standardize paper evaluations.
              </p>
            </motion.div>
            <motion.div variants={slideRight} className="lg:w-1/2 w-full h-[400px] bg-gradient-to-br from-[#0a1a12] to-[#050a07] border border-emerald-500/10 rounded-3xl flex items-center justify-center p-8">
               <div className="w-full h-full bg-black/40 border border-white/5 rounded-2xl flex flex-col p-6 gap-4">
                  <div className="flex gap-2 border-b border-white/10 pb-4">
                     <div className="w-24 h-8 bg-emerald-500/20 rounded-lg"></div>
                     <div className="w-24 h-8 bg-white/5 rounded-lg"></div>
                  </div>
                  <div className="flex-1 border border-dashed border-white/10 rounded-xl flex items-center justify-center">
                    <Code2 className="w-10 h-10 text-gray-600" />
                  </div>
               </div>
            </motion.div>
          </motion.div>

        </div>
      </section>

      {/* =========================================
          4. ENTERPRISE TECH STACK (Grid)
          ========================================= */}
      <section className="py-32 px-6 bg-black relative">
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>
        <motion.div 
          initial="hidden" whileInView="visible" viewport={{ once: true }} variants={staggerContainer}
          className="max-w-7xl mx-auto"
        >
          <div className="text-center mb-20">
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-6">Enterprise-Grade Architecture.</h2>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">Zero-downtime microservices built to scale, ensuring real-time syncing and robust security.</p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { icon: Layers, name: "Next.js 15", desc: "Edge Runtime UI" },
              { icon: Cpu, name: "FastAPI", desc: "Core Python Engine" },
              { icon: Database, name: "Supabase", desc: "Realtime PostgreSQL" },
              { icon: Brain, name: "LangChain", desc: "Multi-Model Fallback" },
              { icon: Code2, name: "Groq & Gemini", desc: "Lightning Fast LLMs" },
              { icon: LineChart, name: "Pinecone", desc: "Vector RAG DB" },
              { icon: Rocket, name: "Vercel", desc: "Frontend Hosting" },
              { icon: ShieldCheck, name: "Render", desc: "Backend Docker" },
            ].map((tech, i) => (
              <motion.div key={i} variants={fadeUp} className="bg-[#0a0a0a] border border-white/5 hover:border-white/10 p-6 rounded-2xl transition-colors group">
                <tech.icon className="w-8 h-8 text-gray-500 group-hover:text-white transition-colors mb-4" />
                <h4 className="text-white font-bold mb-1">{tech.name}</h4>
                <p className="text-xs text-gray-500">{tech.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* =========================================
          5. THE JOURNEY & CTA (Final Push)
          ========================================= */}
      <section className="py-32 px-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-indigo-950/20 pointer-events-none"></div>
        
        <motion.div 
          initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp}
          className="max-w-4xl mx-auto text-center relative z-10"
        >
          <div className="inline-flex items-center justify-center p-4 bg-white/5 border border-white/10 rounded-full mb-8">
            <GraduationCap className="w-8 h-8 text-indigo-400" />
          </div>
          <h2 className="text-4xl md:text-6xl font-black text-white mb-8">From Prototype to Production.</h2>
          <p className="text-xl text-gray-400 leading-relaxed mb-16">
            What started as a monolithic Streamlit experiment evolved into a decoupled, zero-conflict microservice powerhouse. We survived dependency hell, conquered strict CORS middlewares, and emerged with a platform built to redefine how universities learn.
          </p>

          <Link href="/dashboard">
            <button className="relative inline-flex h-16 active:scale-95 transition-transform overflow-hidden rounded-full p-[2px] focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2 focus:ring-offset-slate-50">
              <span className="absolute inset-[-1000%] animate-[spin_3s_linear_infinite] bg-[conic-gradient(from_90deg_at_50%_50%,#E2CBFF_0%,#393BB2_50%,#E2CBFF_100%)]" />
              <span className="inline-flex h-full w-full cursor-pointer items-center justify-center rounded-full bg-black px-12 py-1 text-lg font-bold text-white backdrop-blur-3xl gap-3">
                Access GSTU Workspace <ChevronRight className="w-5 h-5" />
              </span>
            </button>
          </Link>
          
          <p className="mt-8 text-sm text-gray-500 tracking-widest uppercase">
            Architected by Mr. Xypher
          </p>
        </motion.div>
      </section>

    </div>
  );
}