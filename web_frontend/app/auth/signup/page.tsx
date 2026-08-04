"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mail, Lock, User, ArrowRight, ShieldCheck, AlertCircle, CheckCircle2 } from "lucide-react";
import { createClient } from "../../utils/supabase/client";

export default function SignupPage() {
  const router = useRouter();
  const supabase = createClient();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg("");
    setSuccessMsg("");
  
    try {
      // ১. Supabase এ একাউন্ট তৈরি
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: fullName },
        },
      });

      if (error) {
        setErrorMsg(error.message);
        setIsLoading(false);
        return; // এখানেই থেমে যাবে
      }

      // ২. সেশন চেক করা
      const session = data.session;
      if (!session) {
        setErrorMsg("Signup successful, but no active session. Please check if Email Confirmation is truly OFF in Supabase.");
        setIsLoading(false);
        return;
      }

      // ৩. FastAPI ব্যাকএন্ডে Sync রিকোয়েস্ট পাঠানো
      if (session?.access_token) {
        const res = await fetch("http://localhost:8000/api/v1/auth/sync", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${session.access_token}`,
            "Content-Type": "application/json"
          }
        });

        if (!res.ok) {
          const errData = await res.text();
          console.error("FastAPI Error:", errData);
          
          // 🔴 ব্যাকএন্ড ফেইল করলে Supabase থেকেও লগআউট করে দেব 
          // যাতে Ghost State তৈরি না হয় এবং ড্যাশবোর্ডে না যায়
          await supabase.auth.signOut(); 
          
          setErrorMsg("Backend sync failed! Token invalid or database error.");
          setIsLoading(false);
          return; // এখানেই থেমে যাবে
        }
      }

      // ৪. সব সফল হলে রিডাইরেক্ট
      setSuccessMsg("Workspace initialized! Redirecting to OS...");
      setTimeout(() => {
        router.push("/dashboard"); 
      }, 2000);

    } catch (err) {
      console.error("Unexpected error:", err);
      setErrorMsg("An unexpected frontend error occurred.");
      setIsLoading(false); // লোডিং স্টাক হবে না
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Glow */}
      <div className="absolute top-1/4 right-1/4 w-100 h-100 bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/4 w-100 h-100 bg-emerald-500/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="w-full max-w-md bg-white/5 border border-white/10 backdrop-blur-xl rounded-3xl p-8 shadow-2xl z-10 relative">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white tracking-tight mb-2">Create account</h1>
          <p className="text-gray-400 text-sm">Join the GSTU Student OS Ecosystem</p>
        </div>

        {errorMsg && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-2 text-red-400 text-sm">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <p>{errorMsg}</p>
          </div>
        )}

        {successMsg && (
          <div className="mb-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center gap-2 text-emerald-400 text-sm">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <p>{successMsg}</p>
          </div>
        )}

        <form onSubmit={handleSignup} className="space-y-4">
          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-300 ml-1">Full Name</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} required className="w-full bg-black/30 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-transparent transition-all" placeholder="John Doe" />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-300 ml-1">University Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="w-full bg-black/30 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-transparent transition-all" placeholder="student@gstu.edu" />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-300 ml-1">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} className="w-full bg-black/30 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-transparent transition-all" placeholder="••••••••" />
            </div>
          </div>

          <button type="submit" disabled={isLoading} className="w-full bg-linear-to-r from-indigo-600 to-emerald-600 hover:from-indigo-500 hover:to-emerald-500 text-white rounded-xl py-3 font-semibold shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 transition-all mt-6">
            {isLoading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <>Create account <ArrowRight className="w-4 h-4" /></>}
          </button>
        </form>

        <p className="text-center text-gray-400 text-sm mt-8">
          Already have an account? <Link href="/auth/login" className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">Sign In</Link>
        </p>
      </div>
    </div>
  );
}