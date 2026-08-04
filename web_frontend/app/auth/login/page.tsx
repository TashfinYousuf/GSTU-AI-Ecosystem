"use client";

import { useState } from "react";
import { Lock, ArrowRight, Loader2, ShieldAlert, BookOpen, HelpCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { createClient } from "../../utils/supabase/client";

export default function AuthVaultPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [role, setRole] = useState("Student");
  
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [department, setDepartment] = useState("IR");
  const [session, setSession] = useState("");
  const [rollNumber, setRollNumber] = useState("");
  const [designation, setDesignation] = useState("Lecturer");
  const [password, setPassword] = useState("");
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    const supabase = createClient();

    try {
      if (isLogin) {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        router.push("/dashboard");
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
          alert("🔒 Faculty Registration Submitted. Your account is currently 'Pending'. The Admin or Department Chair will review and approve your access shortly.");
        } else {
          alert("Registration successful! You can now log in.");
        }
        setIsLogin(true);
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    // 🔴 Exact Campus Background Vibe
    <div className="min-h-screen flex flex-col justify-center items-center p-4 font-sans relative overflow-hidden bg-[url('https://images.unsplash.com/photo-1541339907198-e08756dedf3f?q=80&w=2070&auto=format&fit=crop')] bg-cover bg-center bg-no-repeat" style={{ backgroundColor: 'rgba(15, 17, 21, 0.85)', backgroundBlendMode: 'overlay' }}>
      
      <div className="w-full max-w-[550px] relative z-10 animate-in fade-in zoom-in-95 duration-300 my-10">
        
        <div className="flex flex-col items-center mb-6">
          <div className="w-16 h-16 rounded-full bg-white flex items-center justify-center shadow-xl mb-3 p-1">
             <div className="w-full h-full rounded-full border-2 border-emerald-600 flex items-center justify-center bg-[#f8f9fa]">
                <BookOpen className="w-6 h-6 text-emerald-600" />
             </div>
          </div>
          <h1 className="text-2xl font-bold text-white mb-1 tracking-wide">GSTU AI Ecosystem</h1>
          <p className="text-gray-400 text-[13px]">
            {isLogin ? "Sign in to access elite agentic research tools" : "Create Account"}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-start gap-3">
            <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-300 leading-relaxed">{error}</p>
          </div>
        )}

        <form onSubmit={handleAuth} className="space-y-4 bg-[#171923]/95 backdrop-blur-xl p-8 rounded-2xl border border-white/10 shadow-2xl">
          
          {!isLogin && (
            <>
              <div>
                <label className="block text-[12px] font-medium text-gray-300 mb-1.5 flex items-center justify-between">
                  <span>I am a:</span> <HelpCircle className="w-3.5 h-3.5 text-gray-500" />
                </label>
                <select value={role} onChange={(e) => setRole(e.target.value)} className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-2.5 px-4 text-gray-200 focus:outline-none focus:border-emerald-500 text-[14px]">
                  <option value="Student">Student</option>
                  <option value="Faculty">Faculty</option>
                </select>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Full Name <span className="text-rose-500">*</span></label>
                  <input type="text" required value={fullName} onChange={(e) => setFullName(e.target.value)} className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px]" placeholder="Full Name" />
                </div>
                <div>
                  <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Username <span className="text-rose-500">*</span></label>
                  <input type="text" required value={username} onChange={(e) => setUsername(e.target.value)} className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px]" placeholder="e.g., ashiq_ir_21" />
                </div>
              </div>
            </>
          )}

          {/* Email (Full Width) & Phone (Conditional) */}
          <div className="space-y-4">
            <div>
              <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Email Address <span className="text-rose-500">*</span></label>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px]" placeholder="name@gstu.edu.bd" />
            </div>
            {!isLogin && (
              <div>
                <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Phone Number</label>
                <input type="text" value={phone} onChange={(e) => setPhone(e.target.value)} className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px]" placeholder="017..." />
              </div>
            )}
          </div>

          {!isLogin && (
            <>
              <div>
                <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Department <span className="text-rose-500">*</span></label>
                <select value={department} onChange={(e) => setDepartment(e.target.value)} className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-2.5 px-4 text-gray-200 focus:outline-none focus:border-emerald-500 text-[14px]">
                  <option value="IR">IR</option>
                  <option value="CSE">CSE</option>
                </select>
              </div>

              {role === "Student" ? (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Academic Session <span className="text-rose-500">*</span></label>
                    <input type="text" required value={session} onChange={(e) => setSession(e.target.value)} className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px]" placeholder="e.g., 2021-22" />
                  </div>
                  <div>
                    <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Roll Number <span className="text-rose-500">*</span></label>
                    <input type="text" required value={rollNumber} onChange={(e) => setRollNumber(e.target.value)} className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px]" placeholder="e.g., 21IR045" />
                  </div>
                </div>
              ) : (
                <>
                  <div>
                    <label className="block text-[12px] font-medium text-gray-300 mb-1.5">Designation <span className="text-rose-500">*</span></label>
                    <select value={designation} onChange={(e) => setDesignation(e.target.value)} className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-2.5 px-4 text-gray-200 focus:outline-none focus:border-emerald-500 text-[14px]">
                      <option value="Lecturer">Lecturer</option>
                      <option value="Professor">Professor</option>
                      <option value="Department Chair">Department Chair</option>
                    </select>
                  </div>
                  <div className="mt-2 p-3 bg-[#1e3a8a]/30 border border-blue-500/30 rounded-lg flex items-start gap-2">
                    <Lock className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                    <p className="text-[11px] text-blue-200/80 leading-relaxed font-medium">
                      <strong className="text-blue-300">Faculty Security Protocol:</strong> Your account will be created as 'Pending'. The Admin or Department Chair will review and approve your access.
                    </p>
                  </div>
                </>
              )}
            </>
          )}

          <div className={`${isLogin ? "pt-2" : "pt-0"}`}>
            <label className="block text-[12px] font-medium text-gray-300 mb-1.5">
              {isLogin ? "Password" : "Create Password"} <span className="text-rose-500">*</span>
            </label>
            <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="w-full bg-[#0b0c10] border border-white/10 rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-emerald-500 text-[14px]" placeholder={isLogin ? "••••••••" : "Minimum 6 characters"} />
          </div>

          <div className="pt-4">
            <button type="submit" disabled={isLoading || !email || !password} className="w-full flex items-center justify-center bg-[#10b981] hover:bg-[#059669] text-white font-bold py-3 rounded-lg transition-all">
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : isLogin ? "Sign In" : "Create Account"}
            </button>
          </div>
          
          <div className="text-center pt-2">
            <button type="button" onClick={() => setIsLogin(!isLogin)} className="text-[#10b981] hover:text-white text-[12.5px] font-medium transition-colors flex items-center justify-center gap-1.5 mx-auto">
              <ArrowRight className="w-3.5 h-3.5" /> {isLogin ? "Need an account? Sign Up" : "Back to Login"}
            </button>
          </div>
        </form>

        <div className="mt-6 text-center">
           <button onClick={() => router.push("/dashboard")} className="text-gray-500 hover:text-gray-300 text-[12px] font-medium transition-colors">
              ⬅ Back to Offline/Guest Dashboard
           </button>
        </div>
      </div>
    </div>
  );
}