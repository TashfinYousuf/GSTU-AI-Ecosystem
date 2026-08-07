"use client";

import { useState } from "react";
import { Lock, ArrowRight, Loader2, ShieldAlert, CheckCircle2, HelpCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { createClient } from "../../utils/supabase/client";

export default function AuthVaultPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [role, setRole] = useState("Student");
  
  // Form States
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [department, setDepartment] = useState("IR");
  const [session, setSession] = useState("");
  const [rollNumber, setRollNumber] = useState("");
  const [designation, setDesignation] = useState("Lecturer");
  const [password, setPassword] = useState("");
  
  // UI States
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const router = useRouter();

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccessMsg(null);
    const supabase = createClient();

    try {
      if (isLogin) {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        
        setSuccessMsg("Welcome back to GSTU Ecosystem!");
        setTimeout(() => router.push("/dashboard"), 1500);

      } else {
        // 🔴 High-Security RBAC & Pending Logic
        let assignedRole = role.toLowerCase();
        let accountStatus = "active";
        
        if (assignedRole === "faculty") {
          accountStatus = "pending"; 
          if (!email.toLowerCase().endsWith("@gstu.edu.bd")) {
            throw new Error("Faculty accounts MUST use a valid @gstu.edu.bd institutional email.");
          }
        }

        // Admin Override 
        if (email.toLowerCase() === "yousufaltashfin@gmail.com" || email.toLowerCase() === "admin@gstu.edu.bd") {
          assignedRole = "admin";
          accountStatus = "active";
        }

        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: fullName,
              username: username,
              phone: phone,
              department: department,
              role: assignedRole,
              account_status: accountStatus, 
              academic_session: role === "Student" ? session : null,
              roll_number: role === "Student" ? rollNumber : null,
              designation: role === "Faculty" ? designation : null,
              tier: assignedRole === "admin" ? "pro_scholar" : "free"
            }
          }
        });

        if (error) throw error;
        
        if (accountStatus === "pending") {
          setSuccessMsg("🔒 Faculty Registration Submitted. Your account is 'Pending' Admin approval.");
        } else {
          setSuccessMsg("Registration successful! You can now log in.");
        }
        
        setTimeout(() => {
          setIsLogin(true);
          setSuccessMsg(null);
        }, 3000);
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    // 🔴 Blurry Campus Background Integration
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

      <div className="w-full max-w-137.5 relative z-10 animate-in fade-in zoom-in-95 duration-300 my-10">
        
        {/* Dynamic Logo & Branding */}
        <div className="flex flex-col items-center mb-6">
          <div className="w-16 h-16 bg-white/5 rounded-2xl p-2 mb-4 border border-white/10 shadow-lg flex items-center justify-center backdrop-blur-md">
            <img src="/logo.png" alt="GSTU Logo" className="w-full h-full object-contain" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-1 tracking-wide">GSTU AI Ecosystem</h1>
          <p className="text-gray-400 text-[13px]">
            {isLogin ? "Sign in to access elite agentic research tools" : "Create your Academic Account"}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-start gap-3">
            <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-300 leading-relaxed">{error}</p>
          </div>
        )}

        <form onSubmit={handleAuth} className="space-y-4 bg-[#171923]/80 backdrop-blur-2xl p-8 rounded-3xl border border-white/10 shadow-[0_0_40px_rgba(0,0,0,0.5)]">
          
          {!isLogin && (
            <div className="animate-in fade-in slide-in-from-top-2">
              <div className="mb-4">
                <label className="text-[12px] font-medium text-gray-300 mb-1.5 flex items-center justify-between">
                  <span>I am a:</span> <HelpCircle className="w-3.5 h-3.5 text-gray-500" />
                </label>
                <select value={role} onChange={(e) => setRole(e.target.value)} className="w-full bg-[#0b0c10]/80 border border-white/10 rounded-xl py-3 px-4 text-gray-200 focus:outline-none focus:border-emerald-500 text-[14px] transition-colors">
                  <option value="Student">Student</option>
                  <option value="Faculty">Faculty</option>
                </select>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Full Name <span className="text-rose-500">*</span></label>
                  <input type="text" required value={fullName} onChange={(e) => setFullName(e.target.value)} className="w-full bg-[#0b0c10]/80 border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px] transition-colors" placeholder="Full Name" />
                </div>
                <div>
                  <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Username <span className="text-rose-500">*</span></label>
                  <input type="text" required value={username} onChange={(e) => setUsername(e.target.value)} className="w-full bg-[#0b0c10]/80 border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px] transition-colors" placeholder="e.g., ashiq_ir_21" />
                </div>
              </div>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Email Address <span className="text-rose-500">*</span></label>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full bg-[#0b0c10]/80 border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px] transition-colors" placeholder="name@gstu.edu.bd" />
            </div>
            {!isLogin && (
              <div className="animate-in fade-in">
                <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Phone Number</label>
                <input type="text" value={phone} onChange={(e) => setPhone(e.target.value)} className="w-full bg-[#0b0c10]/80 border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px] transition-colors" placeholder="017..." />
              </div>
            )}
          </div>

          {!isLogin && (
            <div className="animate-in fade-in slide-in-from-top-2 space-y-4 pt-2">
              <div>
                <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Department <span className="text-rose-500">*</span></label>
                <select value={department} onChange={(e) => setDepartment(e.target.value)} className="w-full bg-[#0b0c10]/80 border border-white/10 rounded-xl py-3 px-4 text-gray-200 focus:outline-none focus:border-emerald-500 text-[14px] transition-colors">
                  <option value="IR">IR</option>
                  <option value="CSE">CSE</option>
                </select>
              </div>

              {role === "Student" ? (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Academic Session <span className="text-rose-500">*</span></label>
                    <input type="text" required value={session} onChange={(e) => setSession(e.target.value)} className="w-full bg-[#0b0c10]/80 border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px] transition-colors" placeholder="e.g., 2021-22" />
                  </div>
                  <div>
                    <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Roll Number <span className="text-rose-500">*</span></label>
                    <input type="text" required value={rollNumber} onChange={(e) => setRollNumber(e.target.value)} className="w-full bg-[#0b0c10]/80 border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px] transition-colors" placeholder="e.g., 21IR045" />
                  </div>
                </div>
              ) : (
                <>
                  <div>
                    <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Designation <span className="text-rose-500">*</span></label>
                    <select value={designation} onChange={(e) => setDesignation(e.target.value)} className="w-full bg-[#0b0c10]/80 border border-white/10 rounded-xl py-3 px-4 text-gray-200 focus:outline-none focus:border-emerald-500 text-[14px] transition-colors">
                      <option value="Lecturer">Lecturer</option>
                      <option value="Assistant Professor">Assistant Professor</option>
                      <option value="Professor">Professor</option>
                      <option value="Department Chair">Department Chair</option>
                    </select>
                  </div>
                  <div className="p-3.5 bg-[#1e3a8a]/20 border border-blue-500/20 rounded-xl flex items-start gap-2.5 backdrop-blur-sm">
                    <Lock className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                    <p className="text-[11px] text-blue-200/80 leading-relaxed font-medium">
                      <strong className="text-blue-300">Faculty Protocol:</strong> Your account will be created as 'Pending'. The Admin must review and approve your access before you can enter.
                    </p>
                  </div>
                </>
              )}
            </div>
          )}

          <div className={`${isLogin ? "pt-2" : "pt-4"}`}>
            <label className="block text-[12px] font-medium text-gray-300 mb-1.5">
              {isLogin ? "Password" : "Create Password"} <span className="text-rose-500">*</span>
            </label>
            <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="w-full bg-[#0b0c10]/80 border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px] transition-colors" placeholder={isLogin ? "••••••••" : "Minimum 6 characters"} />
          </div>

          <div className="pt-6">
            <button type="submit" disabled={isLoading || !email || !password} className="w-full flex items-center justify-center bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3.5 rounded-xl transition-all shadow-lg shadow-emerald-900/20">
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : isLogin ? "Sign In" : "Submit"}
            </button>
          </div>
          
          <div className="text-center pt-4">
            <button type="button" onClick={() => {setIsLogin(!isLogin); setError(null);}} className="text-emerald-500 hover:text-emerald-400 text-[13px] font-bold transition-colors flex items-center justify-center gap-1.5 mx-auto">
              <ArrowRight className="w-3.5 h-3.5" /> {isLogin ? "Create Account" : "Back to Login"}
            </button>
          </div>
        </form>

        <div className="mt-8 text-center">
           <button onClick={() => router.push("/dashboard")} className="text-gray-500 hover:text-gray-300 text-[12px] font-medium transition-colors">
              ⬅ Return to Public Dashboard
           </button>
        </div>
      </div>
    </div>
  );
}