"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "../utils/supabase/client";
import { 
  LogOut, LayoutDashboard, FolderKey, BookOpen, FolderGit2,
  UserCircle, PanelLeftClose, PanelLeft, Brain, Sparkles, 
  ShieldCheck, Plus, MessageSquare, FolderOpen, MoreHorizontal, 
  Edit, Pencil, FolderDown, Share, Trash2,
  Search, Gamepad2, Settings, User, Monitor, 
  CreditCard, Gift, X, CheckCircle, Zap, 
  ArrowRight, XCircle, DownloadCloud, Building2, Loader2, Lock,

} from "lucide-react";
import { fetchAPI } from "../utils/api";

type Workspace = {
  id: string;
  name: string;
  description: string;
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {

  const [activeMenuId, setActiveMenuId] = useState<number | null>(null);
  const router = useRouter();
  const pathname = usePathname();
  const supabase = createClient();
  
  const [isLoading, setIsLoading] = useState(false);
  const [isFetching, setIsFetching] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true); // 🔴 Sidebar Toggle State

  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState("billing"); // "general", "billing", "rewards", "memory"

  // 🔴 Dynamic User State
  const [userData, setUserData] = useState({
    name: "Scholar",
    email: "",
    tier: "free",
    role: "student",
    credits: 0 // 🔴 Dynamic Credits State
  });
  
  const [theme, setTheme] = useState("dark"); // 🔴 Dynamic Theme State

  // 🔴 1. Dynamic Workspaces State
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [isWorkspacesLoading, setIsWorkspacesLoading] = useState(true);

  // 🔴 2. Fetch Real Workspaces from Backend
  useEffect(() => {
    async function loadWorkspaces() {
      setIsWorkspacesLoading(true);
      try {
        const res = await fetchAPI("/workspaces"); // ব্যাকএন্ডের রাউট
        // API যদি { status: "success", data: [...] } রিটার্ন করে
        if (res && res.data) {
          setWorkspaces(res.data);
        } else if (Array.isArray(res)) {
          setWorkspaces(res);
        }
      } catch (error) {
        console.error("Failed to load workspaces:", error);
      } finally {
        setIsWorkspacesLoading(false);
      }
    }
    
    // শুধুমাত্র ইউজার লগইন থাকলেই ফেচ করবে
    if (userData.email) {
      loadWorkspaces();
    }
  }, [userData.email]);

  // 🔴 1. STRICT GUEST ROUTE GUARD (The Unbreakable Wall)
  useEffect(() => {
    if (userData.role === 'guest') {
      // Guest রা শুধু মেইন ড্যাশবোর্ড এবং চ্যাট বক্সে যেতে পারবে
      const isAllowed = pathname === '/dashboard' || pathname.startsWith('/dashboard/workspaces');
      if (!isAllowed) {
        alert("🔒 Clearance Level: Guest. You cannot access premium modules. Redirecting...");
        router.push('/dashboard');
      }
    }
  }, [pathname, userData.role, router]);

  // 🔴 2. NEW CHAT GENERATOR FIX
  const handleNewChat = () => {
    const newWorkspaceId = `proj_${Date.now()}`; // Unique ID তৈরি
    router.push(`/dashboard/workspaces/${newWorkspaceId}`);
  };

  useEffect(() => {
    async function fetchUser() {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        setUserData({
          name: session.user.user_metadata?.full_name || "Scholar",
          email: session.user.email || "",
          tier: session.user.user_metadata?.tier || "free",
          role: session.user.user_metadata?.role || "student",
          credits: session.user.user_metadata?.credits || 0
        });
      }
    }
    fetchUser();
  }, []);

  // ব্যাকএন্ড থেকে ওয়ার্কস্পেস ফেচ করার লজিক
  useEffect(() => {
    const fetchWorkspaces = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (session?.access_token) {
        try {
          const res = await fetch("http://localhost:8000/api/v1/workspaces", {
            headers: {
              "Authorization": `Bearer ${session.access_token}`
            }
          });
          
          if (res.ok) {
            const data = await res.json();
            setWorkspaces(data);
          }
        } catch (error) {
          console.error("Failed to fetch workspaces:", error);
        }
      }
      setIsFetching(false);
    };

    fetchWorkspaces();
  }, []);

  const handleLogout = async () => {
    setIsLoading(true);
    await supabase.auth.signOut();
    router.push("/auth/login");
  };

  const getWorkspaceIcon = (name: string) => {
    if (name.includes("International Relations")) return <BookOpen className="w-4 h-4" />;
    if (name.includes("Projects")) return <FolderGit2 className="w-4 h-4" />;
    if (name.includes("Personal")) return <UserCircle className="w-4 h-4" />;
    return <FolderKey className="w-4 h-4" />;
  };

  return ( 
    <div className="flex h-screen text-gray-200 font-sans relative overflow-hidden bg-[url('/background_pic.png')] bg-cover bg-center bg-no-repeat" style={{ backgroundColor: 'rgba(15, 17, 21, 0.92)', backgroundBlendMode: 'overlay' }}> 
      {/* 🔴 Sidebar (Absolute Locked & Independent Scroll) */}
      <aside className={`${isSidebarOpen ? "w-64 border-r border-white/5" : "w-0 border-none"} transition-all duration-300 ease-in-out bg-[#171717] h-screen flex flex-col shrink-0 z-30 overflow-hidden`}>
        {/* 🔴 STRICT WIDTH WRAPPER (Prevents squishing and overlapping) */}
        <div className="flex flex-col h-full w-64">
          {/* 1. STICKY HEADER & SEARCH BAR */}
          <div className="shrink-0 p-4 border-b border-white/5 bg-[#171717] z-20">
            <div className="flex items-center justify-between min-w-[14rem]">
              {/* Logo & Brand */}
              <div className="h-20 flex px-3 border-b border-white/5 shrink-0">
                <Link href="/dashboard" className="flex items-center gap-3 group">
                  {/* 🔴 Dynamic GSTU Logo Placeholder */}
                  <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform p-0.5 overflow-hidden">
                    <img src="/logo.png" alt="GSTU Logo" className="w-full h-full object-cover rounded-full" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-lg font-black text-white tracking-wide">GSTU IR AI</span>
                    <span className="text-[10px] font-bold text-emerald-500 uppercase tracking-widest">Ecosystem</span>
                  </div>
                </Link>
              </div>
              <button onClick={() => setIsSidebarOpen(false)} className="text-gray-400 hover:text-white p-1 rounded-md transition-colors">
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </div>

            {/* Premium Search Bar */}
            <div className="mt-5 relative min-w-[14rem]">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-gray-500" />
              <input 
                type="text" 
                placeholder="Search projects..." 
                className="w-full bg-black/20 border border-white/10 rounded-lg pl-9 pr-3 py-2 text-[13px] text-gray-200 focus:outline-none focus:border-indigo-500/50 transition-colors shadow-inner"
              />
            </div>
          </div>

          {/* 2. SCROLLABLE NAVIGATION (Independent Scroll) */}
          <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-6 min-w-[16rem] custom-scrollbar">
            
            <Link href="/dashboard" className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${pathname === "/dashboard" ? "bg-[#2f2f2f] text-white-100" : "text-white-400 hover:bg-[#2f2f2f] hover:text-gray-200"}`}>
              <LayoutDashboard className="w-4 h-4" />
              <span className="font-medium text-sm">Dashboard</span>
            </Link>
            
            {/* Apps & Tools Section */}
            <div>
              <h3 className="text-[11px] font-bold text-gray-500 uppercase tracking-wider mb-2 ml-3">Apps & Tools</h3>
              <div className="space-y-0.5">
                <Link href="/dashboard/scholar-hub" className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-[13px] font-medium transition-colors ${userData.role === 'guest' ? 'opacity-40 pointer-events-none' : ''} ${pathname === '/dashboard/scholar-hub' ? 'bg-gray-500/10 text-white-400' : "text-white-400 hover:text-gray-200 hover:bg-white/5"}`}>
                  <Brain className="w-4 h-4 text-blue-400" /> Scholar Hub {userData.role === 'guest' && <Lock className="w-3 h-3 ml-auto"/>}
                </Link>
                <Link href="/dashboard/study-hub" className={`flex items-center gap-3 px-3 py-2.5 text-[13px] font-medium transition-colors rounded-lg ${pathname.includes("study-hub") ? "bg-white/10 text-white" : "text-white-400 hover:text-gray-200 hover:bg-white/5"}`}>
                  <Gamepad2 className="w-4 h-4 text-rose-400" /> Interactive Study Hub {userData.role === 'guest' && <Lock className="w-3 h-3 ml-auto"/>}
                </Link>
                <Link href="/dashboard/department" className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-[13px] font-medium transition-colors ${pathname === '/dashboard/department' ? 'bg-white/10 text-white-400' : 'text-white-400 hover:text-gray-200 hover:bg-white/5'}`}>
                  <Building2 className="w-4 h-4 text-blue-400" /> Department Hub {userData.role === 'guest' && <Lock className="w-3 h-3 ml-auto"/>}
                </Link>
                <Link href="/dashboard/copilot" className={`flex items-center gap-3 px-3 py-2.5 text-[13px] font-medium transition-colors ${userData.role === 'guest' ? 'opacity-40 pointer-events-none' : ''} ${pathname === '/dashboard/copilot' ? 'bg-amber-500/10 text-amber-400' : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'}`}>
                  <Sparkles className="w-4 h-4 text-amber-400" /> Academic Copilot {userData.role === 'guest' && <Lock className="w-3 h-3 ml-auto"/>}
                </Link>
                <Link href="/dashboard/admin" className={`flex items-center gap-3 px-3 py-2.5 text-[13px] font-medium transition-colors ${userData.role === 'guest' ? 'opacity-40 pointer-events-none' : ''} ${pathname === '/dashboard/admin' ? 'bg-emerald-500/10 text-emerald-400' : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'}`}>
                  <ShieldCheck className="w-4 h-4 text-emerald-400" /> Faculty Node {userData.role === 'guest' && <Lock className="w-3 h-3 ml-auto"/>}
                </Link>
              </div>
            </div>
              
            {/* 🔴 5. Workspaces with + Button Fix */}
            <div className="mb-8">
              <div className="flex items-center justify-between px-4 mb-2">
                <p className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">Your Workspaces</p>
                <button onClick={handleNewChat} className="text-gray-500 hover:text-white hover:bg-white/10 p-1 rounded-md transition-colors">
                  <Plus className="w-4 h-4" />
                </button>
              </div>
              <div className="space-y-1">
                {isWorkspacesLoading ? (
                  <div className="px-4 py-3 text-sm text-gray-500 flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> Syncing...
                  </div>
                ) : workspaces.length > 0 ? (
                  workspaces.map((ws) => (
                    <Link key={ws.id} href={`/dashboard/workspaces/${ws.id}`} className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-[13px] font-medium transition-colors ${pathname === `/dashboard/workspaces/${ws.id}` ? 'bg-indigo-500/10 text-indigo-400' : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'}`}>
                      <MessageSquare className="w-4 h-4 shrink-0" />
                      <span className="truncate">{ws.title || "Untitled Research"}</span>
                    </Link>
                  ))
                ) : (
                  <p className="px-5 py-2 text-xs text-white-600 italic">No recent workspaces.</p>
                )}
              </div>
            </div>
          </nav>

          {/* 🔴 3. STICKY USER FOOTER (100% Dynamic) */}
          <div className="shrink-0 p-3 border-t border-white/5 bg-[#171717] z-20 relative">
            
            {/* Profile Popover Menu */}
            {isProfileMenuOpen && (
              <div className="absolute bottom-[110%] left-3 w-56 bg-[#212121] border border-white/10 rounded-xl shadow-2xl z-50 py-1.5 overflow-hidden animate-in fade-in slide-in-from-bottom-2">
                <div className="px-4 py-3 border-b border-white/5 mb-1">
                  <p className="text-sm font-bold text-white truncate">{userData.name}</p>
                  <p className="text-[11px] text-gray-400 truncate">{userData.email}</p>
                </div>
                <button className="w-full flex items-center gap-3 px-4 py-2.5 text-[13px] font-medium text-gray-300 hover:bg-white/5 hover:text-white transition-colors">
                  <User className="w-4 h-4" /> Change Avatar
                </button>
                <button onClick={handleLogout} className="w-full flex items-center gap-3 px-4 py-2.5 text-[13px] font-medium text-red-400 hover:bg-red-500/10 transition-colors">
                  <LogOut className="w-4 h-4" /> Sign Out
                </button>
              </div>
            )}

            {/* Account Bar */}
            <div className="flex items-center justify-between p-1.5 hover:bg-white/5 rounded-xl transition-colors group">
              
              <div onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)} className="flex items-center gap-3 cursor-pointer flex-1 min-w-0">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-xs shadow-inner shrink-0">
                  {userData.name.charAt(0).toUpperCase()}
                </div>
                <div className="flex flex-col min-w-0 pr-2">
                  <span className="text-[13px] font-bold text-gray-200 leading-tight truncate">{userData.name.split(' ')[0]}</span>
                  {/* 🔴 Dynamic Plan Badge */}
                  <span className={`text-[9px] font-bold uppercase tracking-wider ${userData.tier === 'pro_scholar' ? 'text-indigo-400' : 'text-gray-500'}`}>
                    {userData.tier === 'pro_scholar' ? 'PRO SCHOLAR' : 'FREE PLAN'}
                  </span>
                </div>
              </div>
              
              {/* Gear Icon */}
              <button onClick={() => { setIsSettingsOpen(true); setIsProfileMenuOpen(false); }} className="p-2 text-gray-500 hover:text-white hover:bg-white/10 rounded-lg transition-all focus:outline-none shrink-0">
                <Settings className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* 🔴 Main Content Area (Dynamically takes 100% width when collapsed) */}
      <main className="flex-1 min-w-0 relative flex flex-col h-screen bg-[#212121]">
        
        {/* Expand Icon (Visible only when sidebar is closed) */}
        {!isSidebarOpen && (
          <div className="absolute top-4 left-4 z-50">
            <button 
              onClick={() => setIsSidebarOpen(true)} 
              className="p-2.5 bg-[#2f2f2f] text-gray-400 hover:text-white rounded-lg shadow-xl border border-white/5 transition-colors"
              title="Open sidebar"
            >
              <PanelLeft className="w-5 h-5" />
            </button>
          </div>
        )}
        
        <div className="flex-1 overflow-y-auto relative z-10 w-full">
          {children}
        </div>

        {/* 🔴 GLOBAL SETTINGS MODAL (100% Dynamic Tech Giant Standard) */}
        {isSettingsOpen && (
          <div className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-[#171717] w-full max-w-5xl h-[85vh] rounded-2xl shadow-2xl flex overflow-hidden border border-white/10 animate-in fade-in zoom-in-95 font-sans">
              
              {/* Left Sidebar (Settings Tabs) */}
              <div className="w-64 bg-[#121212] border-r border-white/5 flex flex-col shrink-0">
                <div className="p-6 pb-4">
                  <h2 className="text-xl font-bold text-white">Settings</h2>
                </div>
                <div className="flex-1 px-3 space-y-1">
                  <button onClick={() => setSettingsTab("general")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[14px] font-medium transition-all ${settingsTab === "general" ? "bg-white/10 text-white" : "text-gray-400 hover:bg-white/5 hover:text-gray-200"}`}><Monitor className="w-4 h-4"/> General</button>
                  <button onClick={() => setSettingsTab("billing")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[14px] font-medium transition-all ${settingsTab === "billing" ? "bg-indigo-500/10 text-indigo-400" : "text-gray-400 hover:bg-white/5 hover:text-gray-200"}`}><CreditCard className="w-4 h-4"/> Billing & Pro</button>
                  <button onClick={() => setSettingsTab("rewards")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[14px] font-medium transition-all ${settingsTab === "rewards" ? "bg-amber-500/10 text-amber-400" : "text-gray-400 hover:bg-white/5 hover:text-gray-200"}`}><Gift className="w-4 h-4"/> Earn Rewards</button>
                  <button onClick={() => setSettingsTab("memory")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[14px] font-medium transition-all ${settingsTab === "memory" ? "bg-emerald-500/10 text-emerald-400" : "text-gray-400 hover:bg-white/5 hover:text-gray-200"}`}><Brain className="w-4 h-4"/> AI Memory</button>
                </div>
              </div>

              {/* Right Content Area */}
              <div className="flex-1 bg-[#171717] flex flex-col">
                <div className="flex justify-end p-4 shrink-0">
                  <button onClick={() => setIsSettingsOpen(false)} className="p-2 text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-colors"><X className="w-5 h-5"/></button>
                </div>
                
                <div className="flex-1 overflow-y-auto px-10 pb-12 custom-scrollbar">
                  
                  {/* 💳 BILLING TAB */}
                  {settingsTab === "billing" && (
                    <div className="max-w-3xl mx-auto animate-in fade-in">
                      <h3 className="text-2xl font-bold text-white mb-8">Subscription & Billing</h3>
                      
                      {/* Highly Highlighted Lifetime Impact */}
                      <div className="bg-gradient-to-r from-indigo-500/20 via-purple-500/10 to-transparent border border-indigo-500/30 rounded-3xl p-8 mb-10 flex items-center justify-between relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/20 rounded-full blur-3xl"></div>
                        <div className="relative z-10">
                          <h4 className="text-xl font-bold text-white mb-1">Your Lifetime Impact</h4>
                          <p className="text-sm text-indigo-200/70">Track your academic progress through GSTU OS.</p>
                        </div>
                        <div className="flex gap-8 relative z-10">
                          <div className="text-center">
                            <div className="text-4xl font-black text-white mb-1">142</div>
                            <div className="text-[11px] font-bold text-indigo-300 uppercase tracking-wider">Queries</div>
                          </div>
                          <div className="w-px h-14 bg-indigo-500/30"></div>
                          <div className="text-center">
                            <div className="text-4xl font-black text-white mb-1">12</div>
                            <div className="text-[11px] font-bold text-indigo-300 uppercase tracking-wider">PDFs Analyzed</div>
                          </div>
                        </div>
                      </div>

                      {/* Pricing Cards */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        
                        {/* Basic Tier */}
                        <div className={`bg-[#1e1e1e] border ${userData.tier === 'free' ? 'border-gray-500/50 shadow-[0_0_20px_rgba(255,255,255,0.05)]' : 'border-white/5'} rounded-3xl p-8`}>
                          <h3 className="text-xl font-bold text-white mb-2">Basic Tier</h3>
                          <div className="text-3xl font-bold text-white mb-6">৳0 <span className="text-sm text-gray-500 font-normal">/mo</span></div>
                          <ul className="space-y-4 mb-8">
                            <li className="flex items-center gap-3 text-sm text-gray-300"><CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" /> Standard Fast Engine (Llama 4)</li>
                            <li className="flex items-center gap-3 text-sm text-gray-300"><CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" /> Basic RAG limit (2 PDFs)</li>
                            <li className="flex items-center gap-3 text-sm text-gray-500 opacity-50"><XCircle className="w-4 h-4 shrink-0" /> No Multimodal Vision</li>
                          </ul>
                          <button disabled className="w-full py-3.5 rounded-xl bg-white/5 text-gray-400 font-semibold border border-white/10">{userData.tier === 'free' ? 'Current Plan' : 'Free Tier'}</button>
                        </div>

                        {/* Pro Tier */}
                        <div className="bg-gradient-to-b from-[#1e1e1e] to-[#121212] border border-indigo-500/50 rounded-3xl p-8 shadow-[0_0_30px_rgba(99,102,241,0.15)] relative">
                          <div className="absolute top-0 right-0 bg-indigo-500 text-white text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-bl-xl">Recommended</div>
                          <h3 className="text-xl font-bold text-indigo-400 mb-2 flex items-center gap-2"><Zap className="w-5 h-5"/> GSTU Pro Scholar</h3>
                          <div className="text-3xl font-bold text-white mb-6">৳99 <span className="text-sm text-gray-500 font-normal">/mo</span></div>
                          <ul className="space-y-4 mb-8">
                            <li className="flex items-center gap-3 text-sm text-gray-200"><CheckCircle className="w-4 h-4 text-indigo-400 shrink-0" /> Unlimited Premium AI</li>
                            <li className="flex items-center gap-3 text-sm text-gray-200"><CheckCircle className="w-4 h-4 text-indigo-400 shrink-0" /> Advanced Vision & Voice AI</li>
                          </ul>
                          
                          {userData.tier === 'pro_scholar' ? (
                             <button disabled className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-emerald-600/20 border border-emerald-500/50 text-emerald-400 font-bold">
                               <CheckCircle className="w-4 h-4" /> You are Pro
                             </button>
                          ) : (
                            <>
                              <button className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold transition-all shadow-lg shadow-indigo-600/20">
                                Upgrade to Pro <ArrowRight className="w-4 h-4" />
                              </button>
                              {/* 🔴 Dynamic Manual bKash Integration */}
                              <div className="p-2 bg-white/5 border border-white/10 rounded-xl mt-4">
                                <p className="text-[12px] text-gray-300 mb-3 ml-1"><span className="text-rose-400 font-bold">bKash Personal:</span> 01705587837 (Send ৳99)</p>
                                <div className="flex gap-2">
                                  <input 
                                    type="text" 
                                    id="trxId"
                                    placeholder="bKash TrxID..." 
                                    className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" 
                                  />
                                  <button 
                                    onClick={() => {
                                      const el = document.getElementById('trxId') as HTMLInputElement;
                                      if(!el.value) return alert("Enter TrxID!");
                                      el.value = "Verifying...";
                                      setTimeout(() => alert("Transaction sent to Admin for approval!"), 1500);
                                    }}
                                    className="px-4 bg-[#2a2a2a] hover:bg-indigo-600 text-white rounded-lg text-sm font-medium transition-colors">
                                    Verify
                                  </button>
                                </div>
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* ⚙️ GENERAL TAB */}
                  {settingsTab === "general" && (
                    <div className="max-w-2xl animate-in fade-in">
                      <h3 className="text-2xl font-bold text-white mb-8">General Settings</h3>
                      <div className="space-y-6">
                        <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl flex justify-between items-center">
                          <div>
                            <h4 className="font-bold text-white">App Theme</h4>
                            <p className="text-sm text-gray-400">Select your preferred interface color.</p>
                          </div>
                          <select 
                            value={theme}
                            onChange={(e) => setTheme(e.target.value)}
                            className="bg-[#121212] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none text-sm"
                          >
                            <option value="dark">Dark Mode (Default)</option>
                            <option value="light">Light Mode</option>
                            <option value="system">System</option>
                          </select>
                        </div>
                        <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl flex justify-between items-center">
                          <div>
                            <h4 className="font-bold text-white">Account Role (RBAC)</h4>
                            <p className="text-sm text-gray-400">Your registered ecosystem role.</p>
                          </div>
                          <select 
                            disabled={userData.role === 'student'} 
                            value={userData.role}
                            className="bg-[#121212] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none text-sm disabled:opacity-50 capitalize"
                          >
                            <option value="student">Student Mode</option>
                            <option value="faculty">Faculty / Admin Node</option>
                            <option value="admin">Super Admin</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* 🎁 EARN REWARDS TAB */}
                  {settingsTab === "rewards" && (
                    <div className="max-w-2xl animate-in fade-in">
                      <h3 className="text-2xl font-bold text-white mb-8 flex items-center gap-3"><Gift className="w-6 h-6 text-rose-500"/> Earn Free Credits</h3>
                      <div className="bg-[#111827] border border-rose-500/20 rounded-2xl p-6 mb-6">
                        <p className="text-gray-300 text-lg flex items-center gap-3"><div className="w-5 h-5 rounded-full bg-gradient-to-r from-gray-300 to-gray-500 flex items-center justify-center text-[11px] text-black font-bold">C</div> Your Current Balance: <strong className="text-white">{userData.credits} Credits</strong></p>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        <button onClick={() => alert("Connecting to ad network...")} className="bg-[#1e293b] hover:bg-[#334155] border border-white/5 rounded-2xl p-6 flex items-center gap-4 transition-colors text-left">
                          <Monitor className="w-8 h-8 text-gray-400 shrink-0" />
                          <div>
                            <span className="text-white font-bold block mb-1">Watch Video</span>
                            <span className="text-emerald-400 text-sm font-bold">+10 Credits</span>
                          </div>
                        </button>
                        <button onClick={() => alert("Fetching partner offers...")} className="bg-[#1e293b] hover:bg-[#334155] border border-white/5 rounded-2xl p-6 flex items-center gap-4 transition-colors text-left">
                          <DownloadCloud className="w-8 h-8 text-amber-400 shrink-0" />
                          <div>
                            <span className="text-white font-bold block mb-1">Try Partner App</span>
                            <span className="text-emerald-400 text-sm font-bold">+50 Credits</span>
                          </div>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* 🧠 AI MEMORY TAB (New dynamic logic) */}
                  {settingsTab === "memory" && (
                    <div className="max-w-2xl animate-in fade-in">
                      <h3 className="text-2xl font-bold text-white mb-8 flex items-center gap-3"><Brain className="w-6 h-6 text-emerald-500"/> AI Memory Management</h3>
                      <div className="space-y-6">
                        <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl flex justify-between items-center">
                          <div>
                            <h4 className="font-bold text-white mb-1">Clear AI Cache</h4>
                            <p className="text-sm text-gray-400">Wipes local browser cache to speed up the dashboard.</p>
                          </div>
                          <button 
                            onClick={() => alert("Local AI cache cleared successfully!")}
                            className="bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 px-5 py-2.5 rounded-lg text-sm font-bold transition-colors"
                          >
                            Clear Cache
                          </button>
                        </div>

                        <div className="bg-[#1e1e1e] border border-rose-500/20 p-6 rounded-2xl flex justify-between items-center">
                          <div>
                            <h4 className="font-bold text-white mb-1">Delete Chat History</h4>
                            <p className="text-sm text-gray-400">Permanently erases all your workspace conversations from the database.</p>
                          </div>
                          <button 
                            onClick={() => {
                              if(confirm("Are you sure? This cannot be undone.")) {
                                alert("Request sent to server.");
                              }
                            }}
                            className="bg-rose-600 hover:bg-rose-700 text-white px-5 py-2.5 rounded-lg text-sm font-bold transition-colors shadow-lg"
                          >
                            Wipe Data
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}