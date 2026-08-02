"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mail, Lock, ArrowRight, AlertCircle } from "lucide-react";
import { createClient } from "../../utils/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const supabase = createClient();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg("");
    setSuccessMsg("");

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (!error) {
      // Supabase থেকে সেশন টোকেন নিন
      const { data: { session } } = await supabase.auth.getSession();
      
      if (session?.access_token) {
        // FastAPI ব্যাকএন্ডে রিকোয়েস্ট পাঠান (আপনার ব্যাকএন্ড URL অনুযায়ী পোর্ট ঠিক করে নিন)
        try {
          await fetch("http://localhost:8000/api/v1/auth/sync", {
            method: "POST",
            headers: {
              "Authorization": `Bearer ${session.access_token}`,
              "Content-Type": "application/json"
            }
          });
          console.log("Backend sync successful!");
        } catch (err) {
          console.error("Backend sync failed:", err);
        }
      }

      setSuccessMsg("Workspace initialized! Redirecting to OS...");
      setTimeout(() => {
        router.push("/dashboard"); 
      }, 2000);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Glow Effects */}
      <div className="absolute top-1/3 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="w-full max-w-md bg-white/5 border border-white/10 backdrop-blur-xl rounded-3xl p-8 shadow-2xl z-10 relative">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white tracking-tight mb-2">Welcome Back</h1>
          <p className="text-gray-400 text-sm">Sign in to GSTU Student OS</p>
        </div>

        {errorMsg && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-2 text-red-400 text-sm">
            <AlertCircle className="w-4 h-4" />
            <p>{errorMsg}</p>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-5">
          {/* Email Input */}
          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-300 ml-1">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="w-full bg-black/30 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent transition-all" placeholder="student@gstu.edu" />
            </div>
          </div>

          {/* Password Input */}
          <div className="space-y-1">
            <div className="flex justify-between items-center ml-1">
              <label className="text-sm font-medium text-gray-300">Password</label>
            </div>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="w-full bg-black/30 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent transition-all" placeholder="••••••••" />
            </div>
          </div>

          <button type="submit" disabled={isLoading} className="w-full bg-linear-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl py-3 font-semibold shadow-lg shadow-blue-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-50 mt-4">
            {isLoading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <>Sign In <ArrowRight className="w-4 h-4" /></>}
          </button>
        </form>

        <p className="text-center text-gray-400 text-sm mt-8">
          Don't have an account? <Link href="/auth/signup" className="text-blue-400 hover:text-blue-300 font-medium transition-colors">Create Account</Link>
        </p>
      </div>
    </div>
  );
}