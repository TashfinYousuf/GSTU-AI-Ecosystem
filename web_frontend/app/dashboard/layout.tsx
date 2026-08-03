"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "../utils/supabase/client";
import { 
  LogOut, 
  LayoutDashboard, 
  FolderKey,
  BookOpen,
  FolderGit2,
  UserCircle,
  PanelLeftClose,
  PanelLeft,
  Brain,
  Sparkles, 
  ShieldCheck,
  Plus,
  MessageSquare, 
  FolderOpen, 
  MoreHorizontal, 
  Edit,
  Pencil, 
  FolderDown, 
  Share, 
  Trash2,
  Search,
  Gamepad2
} from "lucide-react";

type Workspace = {
  id: string;
  name: string;
  description: string;
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [activeMenuId, setActiveMenuId] = useState<number | null>(null);
  const router = useRouter();
  const pathname = usePathname();
  const supabase = createClient();
  
  const [isLoading, setIsLoading] = useState(false);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isFetching, setIsFetching] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true); // 🔴 Sidebar Toggle State

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
    <div className="min-h-screen bg-[#212121] flex text-gray-100 font-sans overflow-hidden selection:bg-indigo-500/30">
      
      {/* 🔴 Sidebar (Absolute Locked & Independent Scroll) */}
      <aside className={`${isSidebarOpen ? "w-64 border-r border-white/5" : "w-0 border-none"} transition-all duration-300 ease-in-out bg-[#171717] h-screen flex flex-col shrink-0 z-30 overflow-hidden`}>

        {/* 🔴 STRICT WIDTH WRAPPER (Prevents squishing and overlapping) */}
        <div className="flex flex-col h-full w-64">

          {/* 1. STICKY HEADER & SEARCH BAR */}
          <div className="shrink-0 p-4 border-b border-white/5 bg-[#171717] z-20">
            <div className="flex items-center justify-between min-w-[14rem]">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-sm shadow-lg shadow-indigo-500/25">
                  OS
                </div>
                <div>
                  <h2 className="font-bold text-[15px] text-gray-200 leading-tight">GSTU IR</h2>
                  <p className="text-[11px] text-indigo-400 font-medium">Student Ecosystem</p>
                </div>
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
            
            <Link href="/dashboard" className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${pathname === "/dashboard" ? "bg-[#2f2f2f] text-gray-100" : "text-gray-400 hover:bg-[#2f2f2f] hover:text-gray-200"}`}>
              <LayoutDashboard className="w-4 h-4" />
              <span className="font-medium text-sm">Dashboard</span>
            </Link>
            
            {/* Apps & Tools Section */}
            <div>
              <h3 className="text-[11px] font-bold text-gray-500 uppercase tracking-wider mb-2 ml-3">Apps & Tools</h3>
              <div className="space-y-0.5">
                <Link href="/dashboard/scholar-hub" className="flex items-center gap-3 px-3 py-2.5 text-[13px] font-medium text-white-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                  <Brain className="w-4 h-4 text-indigo-400" /> Scholar Hub
                </Link>
                <Link href="/dashboard/study-hub" className={`flex items-center gap-3 px-3 py-2.5 text-[13px] font-medium transition-colors rounded-lg ${pathname.includes("study-hub") ? "bg-white/10 text-white" : "text-white-400 hover:text-white hover:bg-white/5"}`}>
                  <Gamepad2 className="w-4 h-4 text-rose-400" /> Interactive Study Hub
                </Link>
                <Link href="/dashboard/copilot" className="flex items-center gap-3 px-3 py-2.5 text-[13px] font-medium text-white-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                  <Sparkles className="w-4 h-4 text-amber-400" /> Academic Copilot
                </Link>
                <Link href="/dashboard/admin" className="flex items-center gap-3 px-3 py-2.5 text-[13px] font-medium text-white-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" /> Faculty Node
                </Link>
              </div>
            </div>
              
            {/* Your Workspaces */}
            <div>
              <div className="flex items-center justify-between px-3 mb-2">
                <h3 className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">Your Workspaces</h3>
                <button className="text-gray-500 hover:text-gray-300"><Plus className="w-3.5 h-3.5" /></button>
              </div>
              <div className="space-y-0.5">
                {workspaces.map((ws) => (
                  <Link key={ws.id} href={`/dashboard/workspaces/${ws.id}`} className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${pathname.includes(ws.id) ? "bg-[#2f2f2f] text-gray-100" : "text-white-400 hover:bg-[#2f2f2f] hover:text-gray-200"}`}>
                    <FolderOpen className="w-4 h-4 shrink-0 text-gray-500" />
                    <span className="font-medium text-[13px] truncate">{ws.name}</span>
                  </Link>
                ))}
              </div>
            </div>

            {/* Recent Chats (With 3-Dot Menu) */}
            <div className="pb-4">
              <h3 className="text-[11px] font-bold text-gray-500 uppercase tracking-wider mb-2 px-3">Recent Chats</h3>
              <div className="space-y-0.5">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="group flex items-center justify-between px-3 py-2 rounded-lg text-white-400 hover:bg-white/5 hover:text-gray-200 transition-colors cursor-pointer relative">
                    <Link href={`/dashboard/chat/${i}`} className="flex items-center gap-3 truncate pr-2 flex-1">
                      <MessageSquare className="w-3.5 h-3.5 shrink-0" />
                      <span className="text-[13px] font-medium truncate">Political Geography Session {i}</span>
                    </Link>
                    <button onClick={(e) => { e.preventDefault(); setActiveMenuId(activeMenuId === i ? null : i); }} className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-white transition-opacity p-0.5 rounded focus:outline-none">
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                    {activeMenuId === i && (
                      <div className="absolute right-4 top-8 w-44 bg-[#212121] border border-white/10 rounded-xl shadow-2xl z-50 py-1.5 animate-in fade-in zoom-in-95">
                        <button className="w-full flex items-center gap-3 px-3 py-2 text-[13px] font-medium text-gray-300 hover:bg-white/5"><Pencil className="w-3.5 h-3.5"/> Rename</button>
                        <button className="w-full flex items-center gap-3 px-3 py-2 text-[13px] font-medium text-gray-300 hover:bg-white/5"><FolderDown className="w-3.5 h-3.5"/> Move to...</button>
                        <button className="w-full flex items-center gap-3 px-3 py-2 text-[13px] font-medium text-gray-300 hover:bg-white/5"><Share className="w-3.5 h-3.5"/> Share</button>
                        <div className="h-px bg-white/10 my-1"></div>
                        <button className="w-full flex items-center gap-3 px-3 py-2 text-[13px] font-medium text-red-400 hover:bg-red-500/10"><Trash2 className="w-3.5 h-3.5"/> Delete</button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </nav>

          {/* 3. STICKY USER FOOTER */}
          <div className="shrink-0 p-3 min-w-[16rem] border-t border-white/5 bg-[#171717] z-20">
            <button onClick={handleLogout} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-colors text-sm font-medium">
              <LogOut className="w-4 h-4" /> Sign Out
            </button>
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
      </main>
    </div>
  );
}