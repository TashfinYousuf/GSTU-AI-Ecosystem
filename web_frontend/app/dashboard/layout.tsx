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
  PanelLeft
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
      
      {/* 🔴 Sidebar (Collapsible & Dynamic Width) */}
      <aside className={`${isSidebarOpen ? "w-64" : "w-0"} transition-all duration-300 ease-in-out bg-[#171717] flex flex-col shrink-0 z-30 overflow-hidden border-r border-white/5`}>
        
        {/* Logo/Brand & Close Button */}
        <div className="p-4 flex items-center justify-between min-w-[16rem] border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-linear-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-sm shadow-lg shadow-indigo-500/25">
              OS
            </div>
            <div>
              <h2 className="font-medium text-sm text-gray-200">GSTU IR</h2>
              <p className="text-[11px] text-indigo-400">Student Ecosystem</p>
            </div>
          </div>
          
          {/* Collapse Icon INSIDE Sidebar */}
          <button 
            onClick={() => setIsSidebarOpen(false)} 
            className="text-gray-400 hover:text-white p-1.5 rounded-md hover:bg-white/10 transition-colors"
            title="Close sidebar"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Links & Workspaces */}
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5 min-w-[16rem]">
          <Link href="/dashboard" className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${pathname === "/dashboard" ? "bg-[#2f2f2f] text-gray-100" : "text-gray-400 hover:bg-[#2f2f2f] hover:text-gray-200"}`}>
            <LayoutDashboard className="w-4 h-4" />
            <span className="font-medium text-sm">Dashboard</span>
          </Link>

          <div className="pt-6 pb-2">
            <p className="px-3 text-xs font-semibold text-gray-500 tracking-wide uppercase">Your Workspaces</p>
          </div>
          
          {/* Dynamic Workspaces Render */}
          {isFetching ? (
            <div className="px-3 py-2 text-sm text-gray-500 animate-pulse">Loading workspaces...</div>
          ) : workspaces.length > 0 ? (
            workspaces.map((ws) => (
              <Link 
                key={ws.id} 
                href={`/dashboard/workspaces/${ws.id}`} 
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${pathname.includes(ws.id) ? "bg-[#2f2f2f] text-gray-100" : "text-gray-400 hover:bg-[#2f2f2f] hover:text-gray-200"}`}
              >
                {getWorkspaceIcon(ws.name)}
                <span className="font-medium text-sm truncate">{ws.name}</span>
              </Link>
            ))
          ) : (
            <div className="px-3 py-2 text-sm text-gray-500">No workspaces found.</div>
          )}
        </nav>

        {/* User Footer & Logout */}
        <div className="p-3 min-w-[16rem] border-t border-white/5">
          <button 
            onClick={handleLogout}
            disabled={isLoading}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-colors text-sm font-medium"
          >
            <LogOut className="w-4 h-4" />
            <span>{isLoading ? "Signing out..." : "Sign Out"}</span>
          </button>
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