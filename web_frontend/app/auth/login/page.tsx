"use client";

import { useState } from "react";
import { Lock, ArrowRight, Loader2, ShieldAlert, CheckCircle2 } from "lucide-react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "../../utils/supabase/client";

export default function LoginPage() {
  // Pure Login States
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  
  // Forgot Password States
  const [isForgotPassword, setIsForgotPassword] = useState(false);
  const [resetEmail, setResetEmail] = useState("");

  // UI States
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccessMsg(null);
    const supabase = createClient();

    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      
      setSuccessMsg("Welcome back to GSTU Ecosystem!");
      setTimeout(() => router.push("/dashboard"), 1500);
    } catch (err: any) {
      setError(err.message || "Authentication failed. Please check your credentials.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async () => {
    if (!resetEmail) {
      setError("Please enter your registered email address.");
      return;
    }
    
    setIsLoading(true);
    setError(null);
    setSuccessMsg(null);
    const supabase = createClient();
    
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(resetEmail, {
        redirectTo: `${window.location.origin}/auth/update-password`,
      });
      if (error) throw error;
      
      setSuccessMsg("Secure link sent! Check your inbox/spam folder.");
      setTimeout(() => setIsForgotPassword(false), 3000);
    } catch (err: any) {
      setError(err.message || "Failed to send reset link.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center p-4 font-sans relative overflow-hidden bg-cover bg-center bg-no-repeat" style={{ backgroundImage: "url('/background_pic.png')" }}>
      
      {/* Heavy Blur Overlay */}
      <div className="absolute inset-0 bg-[#0f1115]/85 backdrop-blur-md"></div>
      
      {/* Success Toast */}
      {successMsg && (
        <div className="absolute top-10 left-1/2 -translate-x-1/2 z-50 animate-in slide-in-from-top-10 fade-in duration-500 w-full max-w-md px-4">
          <div className="bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-3 backdrop-blur-xl">
            <CheckCircle2 className="w-5 h-5 shrink-0" />
            <span className="font-bold tracking-wide text-sm leading-relaxed">{successMsg}</span>
          </div>
        </div>
      )}

      <div className="w-full max-w-[450px] relative z-10 animate-in fade-in zoom-in-95 duration-300 my-10">
        
        <div className="flex flex-col items-center mb-6">
          <div className="w-16 h-16 bg-white/5 rounded-2xl p-2 mb-4 border border-white/10 shadow-lg flex items-center justify-center backdrop-blur-md">
            <img src="/logo.png" alt="GSTU Logo" className="w-full h-full object-contain" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-1 tracking-wide">GSTU AI Ecosystem</h1>
          <p className="text-gray-400 text-[13px]">
            {isForgotPassword ? "Reset your account password" : "Sign in to access elite agentic tools"}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-start gap-3">
            <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-300 leading-relaxed">{error}</p>
          </div>
        )}

        {isForgotPassword ? (
          /* 🔴 FORGOT PASSWORD UI */
          <div className="space-y-4 bg-[#171923]/80 backdrop-blur-2xl p-8 rounded-3xl border border-white/10 shadow-[0_0_40px_rgba(0,0,0,0.5)] animate-in fade-in slide-in-from-bottom-4">
            <h4 className="text-center font-bold text-white text-lg">Reset Password</h4>
            <p className="text-center text-[13px] text-gray-400 mb-4">Enter your registered email. We will send a secure password reset link.</p>
            
            <input 
              type="email" 
              value={resetEmail} 
              onChange={(e) => setResetEmail(e.target.value)} 
              className="w-full bg-[#0b0c10]/80 border border-white/10 rounded-xl py-3.5 px-4 text-white focus:outline-none focus:border-indigo-500 text-[14px] transition-colors" 
              placeholder="name@gstu.edu.bd" 
            />
            
            <button 
              onClick={handleResetPassword}
              disabled={isLoading || !resetEmail}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3.5 rounded-xl transition-all shadow-lg flex items-center justify-center gap-2 mt-2 disabled:opacity-50"
            >
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> : "Send Reset Link"}
            </button>
            
            <button onClick={() => { setIsForgotPassword(false); setError(null); }} className="text-emerald-500 hover:text-emerald-400 text-[13px] font-bold transition-colors flex items-center justify-center gap-1.5 mx-auto mt-4">
              <ArrowRight className="w-3.5 h-3.5" /> Back to login
            </button>
          </div>
        ) : (
          /* 🔴 LOGIN UI */
          <form onSubmit={handleLogin} className="space-y-5 bg-[#171923]/80 backdrop-blur-2xl p-8 rounded-3xl border border-white/10 shadow-[0_0_40px_rgba(0,0,0,0.5)] animate-in fade-in">
            
            <div>
              <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Email Address</label>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full bg-[#0b0c10]/80 border border-white/10 rounded-xl py-3.5 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px] transition-colors" placeholder="name@gstu.edu.bd" />
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="block text-[12px] font-medium text-gray-300">Password</label>
                <button type="button" onClick={() => { setIsForgotPassword(true); setError(null); }} className="text-[11px] text-emerald-500 hover:text-emerald-400 font-bold transition-colors">
                  Forgot Password?
                </button>
              </div>
              <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="w-full bg-[#0b0c10]/80 border border-white/10 rounded-xl py-3.5 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px] transition-colors" placeholder="••••••••" />
            </div>

            <div className="pt-2">
              <button type="submit" disabled={isLoading || !email || !password} className="w-full flex items-center justify-center bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3.5 rounded-xl transition-all shadow-lg shadow-emerald-900/20 disabled:opacity-50">
                {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Sign In"}
              </button>
            </div>
            
            <div className="text-center pt-3 border-t border-white/10 mt-5">
              <Link href="/auth/signup" className="text-emerald-500 hover:text-emerald-400 text-[13px] font-bold transition-colors flex items-center justify-center gap-1.5 mx-auto mt-4">
                <ArrowRight className="w-3.5 h-3.5" /> Apply for Academic Access
              </Link>
            </div>
          </form>
        )}

        <div className="mt-8 text-center">
           <button onClick={() => router.push("/dashboard")} className="text-gray-500 hover:text-gray-300 text-[12px] font-medium transition-colors">
              ⬅ Return to Public Dashboard
           </button>
        </div>
      </div>
    </div>
  );
}