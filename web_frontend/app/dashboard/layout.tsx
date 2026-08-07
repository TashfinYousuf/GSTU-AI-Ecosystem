"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "../utils/supabase/client";
import {
  LogOut, LayoutDashboard, FolderKey, BookOpen, FolderGit2,
  UserCircle, PanelLeftClose, PanelLeft, Brain, Sparkles,
  ShieldCheck, Plus, MessageSquare, FolderOpen, MoreHorizontal,
  Edit, Pencil, FolderDown, Share, Trash2, Star, Move,
  Folder, FolderPlus, ChevronRight, ChevronDown, Clock,
  Search, Gamepad2, Settings, User, Monitor,
  CreditCard, Gift, X, CheckCircle, Zap,
  ArrowRight, XCircle, DownloadCloud, Building2, Loader2,
  Lock, Target, ShieldAlert, Activity, MessageCircle,
  Send,
} from "lucide-react";
import { fetchAPI } from "../utils/api";

type ChatItem = {
  id: string;
  title: string;
  is_starred: boolean;
  project_id: string | null;
  updated_at?: string;
};

type Project = {
  id: string;
  name: string;
  chat_count?: number;
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const supabase = createClient();

  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  // 🔴 FIX: this used to be TWO separate state variables — `settingsTab`
  // (general/billing/rewards/memory) and `activeSettingsTab` (only ever
  // "performance"). Because they were independent, the Performance section's
  // visibility condition (`activeSettingsTab === "performance"`) stayed true
  // regardless of which settingsTab button was clicked, so Performance
  // rendered underneath every other tab at once. Merged into a single state.
  const [settingsTab, setSettingsTab] = useState("billing");

  const [userStats, setUserStats] = useState({ queries: 0, documents_analyzed: 0 });
  const [isClearingCache, setIsClearingCache] = useState(false);
  const [isWipingData, setIsWipingData] = useState(false);

  const [userData, setUserData] = useState({
    name: "Scholar",
    email: "",
    tier: "free",
    role: "",           // 🔴 was "student" — empty string lets the route-guard
                         // effect correctly wait for the real value to load
                         // instead of acting on a false default.
    credits: 0,
    createdAt: "",
    avatarUrl: ""
  });

  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploadingAvatar(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const formData = new FormData();
      formData.append("file", file);

      // 🔴 STRICT ABSOLUTE URL: Bypasses Next.js relative routing bugs
      const res = await fetch("http://127.0.0.1:8000/api/v1/auth/avatar", {
        method: "POST",
        headers: { "Authorization": `Bearer ${session.access_token}` },
        body: formData, 
      });

      if (!res.ok) throw new Error("Upload failed on backend");
      
      const data = await res.json();

      if (res.ok && data.avatar_url) {
        setUserData(prev => ({ ...prev, avatarUrl: data.avatar_url }));
        setIsProfileMenuOpen(false);
      } else {
        alert(data.detail || "Avatar upload failed.");
      }
    } catch (err) {
      console.error("Avatar upload failed:", err);
      alert("Network error during avatar upload.");
    } finally {
      setIsUploadingAvatar(false);
      e.target.value = "";
    }
  };

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

// 🔴 Real-time Debounced Search Effect
useEffect(() => {
  if (searchQuery.trim().length < 2) {
    setSearchResults([]);
    return;
  }
  
  const timer = setTimeout(async () => {
    setIsSearching(true);
    try {
      const res = await fetchAPI(`/chat/search?q=${encodeURIComponent(searchQuery)}`);
      if (res.data) setSearchResults(res.data);
    } catch (e) {
      console.error("Search failed", e);
    } finally {
      setIsSearching(false);
    }
  }, 400); // 400ms delay to prevent API spam

  return () => clearTimeout(timer);
}, [searchQuery]);

  const [hasPremiumAccess, setHasPremiumAccess] = useState(false);
  const [daysLeftInTrial, setDaysLeftInTrial] = useState(0);

  const [mappingData, setMappingData] = useState<any[]>([]);
  const [aiEvaluation, setAiEvaluation] = useState("");
  const [logData, setLogData] = useState({ study_hours: "", sleep_hours: "", mood: "Focused" });
  const [isLogging, setIsLogging] = useState(false);

  const [theme, setThemeState] = useState("dark");

  // 🔴 NEW: real theme persistence + system-preference detection. Applies a
  // `data-theme` attribute to <html>. NOTE: this makes the toggle itself
  // fully functional and persistent, but most of this app's components use
  // hardcoded hex colors (bg-[#212121] etc.) rather than Tailwind's `dark:`
  // variant or CSS custom properties, so "Light Mode" will only visibly
  // repaint sections that have been migrated to reference theme-aware
  // colors. This sets up the correct mechanism to build on incrementally.
  useEffect(() => {
    const stored = localStorage.getItem("gstu-theme") || "dark";
    applyTheme(stored);
    setThemeState(stored);
  }, []);

  const applyTheme = (value: string) => {
    const root = document.documentElement;
    if (value === "system") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      root.setAttribute("data-theme", prefersDark ? "dark" : "light");
    } else {
      root.setAttribute("data-theme", value);
    }
  };

  const handleThemeChange = (value: string) => {
    setThemeState(value);
    localStorage.setItem("gstu-theme", value);
    applyTheme(value);
  };

  // 🔴 NEW: profile editing state
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [profileDraft, setProfileDraft] = useState({ full_name: "", email: "" });
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isChangingRole, setIsChangingRole] = useState(false);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const [isHelpPrivacyOpen, setIsHelpPrivacyOpen] = useState(false);
  const [helpPrivacyTab, setHelpPrivacyTab] = useState<"help" | "privacy">("help");

  // 🔴 The ONLY client-side gate is for UI display convenience (hiding the
  // dropdown from people who obviously can't use it). The REAL enforcement
  // lives entirely in the backend's ROLE_CHANGE_ALLOWLIST — this constant
  // must be kept in sync with account.py's ROLE_CHANGE_ALLOWLIST by hand,
  // and even if this check is bypassed the backend will still reject the
  // request for any other email.
  const ROLE_CHANGE_ALLOWED_EMAILS = new Set(["yousufaltashfin@gmail.com"]);
  const canChangeRole = ROLE_CHANGE_ALLOWED_EMAILS.has(userData.email);

  const startEditingProfile = () => {
    setProfileDraft({ full_name: userData.name, email: userData.email });
    setIsEditingProfile(true);
  };

  const handleSaveProfile = async () => {
    setIsSavingProfile(true);
    try {
      const res = await fetchAPI("/auth/profile", {
        method: "PATCH",
        body: JSON.stringify({
          full_name: profileDraft.full_name !== userData.name ? profileDraft.full_name : undefined,
          email: profileDraft.email !== userData.email ? profileDraft.email : undefined,
        }),
      });
      if (res?.status === "success") {
        setUserData(prev => ({ ...prev, name: profileDraft.full_name, email: profileDraft.email }));
        setIsEditingProfile(false);
      }
    } catch (err) {
      console.error("Profile save failed:", err);
      alert("Failed to update profile. Please try again.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleRoleChange = async (newRole: string) => {
    setIsChangingRole(true);
    try {
      const res = await fetchAPI("/auth/role", { method: "PATCH", body: JSON.stringify({ role: newRole }) });
      if (res?.status === "success") {
        setUserData(prev => ({ ...prev, role: newRole }));
      } else {
        alert(res?.detail || "Role change failed.");
      }
    } catch (err: any) {
      console.error("Role change failed:", err);
      alert("You are not authorized to change roles, or the request failed.");
    } finally {
      setIsChangingRole(false);
    }
  };

  const handleDeleteAccount = async () => {
    const confirmText = window.prompt('This permanently deletes your account and all data. Type "DELETE" to confirm:');
    if (confirmText !== "DELETE") return;

    setIsDeletingAccount(true);
    try {
      await fetchAPI("/auth/account", { method: "DELETE" });
      await supabase.auth.signOut();
      router.push("/auth/login");
    } catch (err) {
      console.error("Account deletion failed:", err);
      alert("Failed to delete account. Please try again or contact support.");
      setIsDeletingAccount(false);
    }
  };

  const [projects, setProjects] = useState<Project[]>([]);
  const [chats, setChats] = useState<ChatItem[]>([]);
  const [isWorkspacesLoading, setIsWorkspacesLoading] = useState(true);
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [moveSubmenuChatId, setMoveSubmenuChatId] = useState<string | null>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (!(e.target as HTMLElement).closest('.workspace-menu-trigger')) {
        setOpenMenuId(null);
        setMoveSubmenuChatId(null);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const chatsByProject = (projectId: string) => chats.filter(c => c.project_id === projectId);
  const recentChats = [...chats]
    .filter(c => !c.project_id)
    .sort((a, b) => new Date(b.updated_at || 0).getTime() - new Date(a.updated_at || 0).getTime())
    .slice(0, 8);

  const toggleProjectExpand = (id: string) => {
    setExpandedProjects(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleNewProject = async () => {
    const name = window.prompt("Name your project:", "New Project");
    if (!name || !name.trim()) return;
    try {
      const res = await fetchAPI("/chat/projects", { method: "POST", body: JSON.stringify({ name: name.trim() }) });
      if (res?.id) {
        setProjects(prev => [{ id: res.id, name: name.trim(), chat_count: 0 }, ...prev]);
        setExpandedProjects(prev => new Set(prev).add(res.id));
      }
    } catch (err) { console.error("Failed to create project:", err); }
  };

  const handleNewChatInProject = async (projectId: string | null) => {
    try {
      const res = await fetchAPI("/chat/workspaces", { method: "POST", body: JSON.stringify({ project_id: projectId }) });
      if (res?.id) router.push(`/dashboard/workspaces/${res.id}`);
    } catch (err) { console.error("Failed to create chat:", err); }
  };

  const handleRenameProject = async (e: React.MouseEvent, project: Project) => {
    e.preventDefault(); e.stopPropagation(); setOpenMenuId(null);
    const newName = window.prompt("Rename project:", project.name);
    if (!newName || !newName.trim() || newName === project.name) return;
    setProjects(prev => prev.map(p => p.id === project.id ? { ...p, name: newName } : p));
    try {
      await fetchAPI(`/chat/projects/${project.id}`, { method: "PATCH", body: JSON.stringify({ name: newName }) });
    } catch (err) { console.error("Rename project failed:", err); }
  };

  const handleDeleteProject = async (e: React.MouseEvent, project: Project) => {
    e.preventDefault(); e.stopPropagation(); setOpenMenuId(null);
    if (!confirm(`Delete project "${project.name}"? Chats inside will move to Recents, not be deleted.`)) return;
    const snapProjects = projects, snapChats = chats;
    setProjects(prev => prev.filter(p => p.id !== project.id));
    setChats(prev => prev.map(c => c.project_id === project.id ? { ...c, project_id: null } : c));
    try {
      await fetchAPI(`/chat/projects/${project.id}`, { method: "DELETE" });
    } catch (err) {
      console.error("Delete project failed:", err);
      setProjects(snapProjects); setChats(snapChats);
    }
  };

  const handleRenameChat = async (e: React.MouseEvent, chat: ChatItem) => {
    e.preventDefault(); e.stopPropagation(); setOpenMenuId(null);
    const newTitle = window.prompt("Rename chat:", chat.title);
    if (!newTitle || !newTitle.trim() || newTitle === chat.title) return;
    setChats(prev => prev.map(c => c.id === chat.id ? { ...c, title: newTitle } : c));
    try {
      await fetchAPI(`/chat/workspaces/${chat.id}`, { method: "PATCH", body: JSON.stringify({ title: newTitle }) });
    } catch (err) { console.error("Rename chat failed:", err); }
  };

  const handleToggleStar = async (e: React.MouseEvent, chat: ChatItem) => {
    e.preventDefault(); e.stopPropagation(); setOpenMenuId(null);
    const next = !chat.is_starred;
    setChats(prev => prev.map(c => c.id === chat.id ? { ...c, is_starred: next } : c));
    try {
      await fetchAPI(`/chat/workspaces/${chat.id}`, { method: "PATCH", body: JSON.stringify({ is_starred: next }) });
    } catch (err) { console.error("Star toggle failed:", err); }
  };

  const handleShareChat = (e: React.MouseEvent, chat: ChatItem) => {
    e.preventDefault(); e.stopPropagation(); setOpenMenuId(null);
    navigator.clipboard.writeText(`${window.location.origin}/dashboard/workspaces/${chat.id}`);
    alert("Link copied! Note: the recipient needs their own account with access.");
  };

  const handleMoveChatToProject = async (e: React.MouseEvent, chat: ChatItem, projectId: string | null) => {
    e.preventDefault(); e.stopPropagation();
    setChats(prev => prev.map(c => c.id === chat.id ? { ...c, project_id: projectId } : c));
    try {
      const body = projectId ? { project_id: projectId } : { clear_project: true };
      await fetchAPI(`/chat/workspaces/${chat.id}`, { method: "PATCH", body: JSON.stringify(body) });
    } catch (err) { console.error("Move chat failed:", err); }
  };

  const handleDeleteChat = async (e: React.MouseEvent, chat: ChatItem) => {
    e.preventDefault(); e.stopPropagation(); setOpenMenuId(null);
    if (!confirm(`Delete "${chat.title}"? This cannot be undone.`)) return;
    const snapshot = chats;
    setChats(prev => prev.filter(c => c.id !== chat.id));
    try {
      await fetchAPI(`/chat/workspaces/${chat.id}`, { method: "DELETE" });
      if (pathname === `/dashboard/workspaces/${chat.id}`) router.push("/dashboard");
    } catch (err) {
      console.error("Delete failed:", err);
      setChats(snapshot);
    }
  };

  const renderChatItem = (chat: ChatItem) => (
    <div key={chat.id} className="relative workspace-menu-trigger group">
      <Link
        href={`/dashboard/workspaces/${chat.id}`}
        className={`flex items-center gap-3 pl-4 pr-9 py-2.5 rounded-lg text-[13px] font-medium transition-colors ${pathname === `/dashboard/workspaces/${chat.id}` ? 'bg-indigo-500/10 text-indigo-400' : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'}`}
      >
        {chat.is_starred ? <Star className="w-4 h-4 shrink-0 fill-amber-400 text-amber-400" /> : <MessageSquare className="w-4 h-4 shrink-0" />}
        <span className="truncate">{chat.title || "Untitled Chat"}</span>
      </Link>

      <button
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); setMoveSubmenuChatId(null); setOpenMenuId(openMenuId === chat.id ? null : chat.id); }}
        className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-gray-500 hover:text-white hover:bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <MoreHorizontal className="w-4 h-4" />
      </button>

      {openMenuId === chat.id && moveSubmenuChatId !== chat.id && (
        <div className="absolute right-0 top-full mt-1 w-48 bg-[#212121] border border-white/10 rounded-xl shadow-2xl z-50 py-1.5 overflow-hidden">
          <button onClick={(e) => handleRenameChat(e, chat)} className="w-full flex items-center gap-3 px-3.5 py-2 text-[13px] text-gray-300 hover:bg-white/5 hover:text-white transition-colors"><Pencil className="w-3.5 h-3.5" /> Rename</button>
          <button onClick={(e) => handleToggleStar(e, chat)} className="w-full flex items-center gap-3 px-3.5 py-2 text-[13px] text-gray-300 hover:bg-white/5 hover:text-white transition-colors"><Star className={`w-3.5 h-3.5 ${chat.is_starred ? "fill-amber-400 text-amber-400" : ""}`} /> {chat.is_starred ? "Unstar" : "Star"}</button>
          <button onClick={(e) => handleShareChat(e, chat)} className="w-full flex items-center gap-3 px-3.5 py-2 text-[13px] text-gray-300 hover:bg-white/5 hover:text-white transition-colors"><Share className="w-3.5 h-3.5" /> Share</button>
          <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); setMoveSubmenuChatId(chat.id); }} className="w-full flex items-center gap-3 px-3.5 py-2 text-[13px] text-gray-300 hover:bg-white/5 hover:text-white transition-colors"><Move className="w-3.5 h-3.5" /> Move to...</button>
          <div className="h-px bg-white/5 my-1" />
          <button onClick={(e) => handleDeleteChat(e, chat)} className="w-full flex items-center gap-3 px-3.5 py-2 text-[13px] text-red-400 hover:bg-red-500/10 transition-colors"><Trash2 className="w-3.5 h-3.5" /> Delete</button>
        </div>
      )}

      {moveSubmenuChatId === chat.id && (
        <div className="absolute right-0 top-full mt-1 w-52 bg-[#212121] border border-white/10 rounded-xl shadow-2xl z-50 py-1.5 overflow-hidden max-h-64 overflow-y-auto">
          <button onClick={(e) => { setMoveSubmenuChatId(null); setOpenMenuId(null); handleMoveChatToProject(e, chat, null); }} className="w-full flex items-center gap-3 px-3.5 py-2 text-[13px] text-gray-300 hover:bg-white/5 hover:text-white transition-colors">
            <Clock className="w-3.5 h-3.5" /> Recents {!chat.project_id && "✓"}
          </button>
          <div className="h-px bg-white/5 my-1" />
          {projects.map(p => (
            <button key={p.id} onClick={(e) => { setMoveSubmenuChatId(null); setOpenMenuId(null); handleMoveChatToProject(e, chat, p.id); }} className="w-full flex items-center gap-3 px-3.5 py-2 text-[13px] text-gray-300 hover:bg-white/5 hover:text-white transition-colors">
              <Folder className="w-3.5 h-3.5" /> <span className="truncate">{p.name}</span> {chat.project_id === p.id && "✓"}
            </button>
          ))}
        </div>
      )}
    </div>
  );

  const renderProjectItem = (project: Project) => {
    const isExpanded = expandedProjects.has(project.id);
    const projectChats = chatsByProject(project.id);

    return (
      <div key={project.id} className="mb-0.5">
        <div className="relative workspace-menu-trigger group flex items-center">
          <button onClick={() => toggleProjectExpand(project.id)} className="flex items-center gap-2 flex-1 min-w-0 px-4 py-2.5 rounded-lg text-[13px] font-medium text-gray-300 hover:bg-white/5 hover:text-white transition-colors">
            {isExpanded ? <ChevronDown className="w-3.5 h-3.5 shrink-0 text-gray-500" /> : <ChevronRight className="w-3.5 h-3.5 shrink-0 text-gray-500" />}
            <Folder className="w-4 h-4 shrink-0 text-indigo-400" />
            <span className="truncate flex-1 text-left">{project.name}</span>
            <span className="text-[10px] text-gray-600 font-normal">{projectChats.length}</span>
          </button>
          <button onClick={(e) => { e.stopPropagation(); setOpenMenuId(openMenuId === `proj:${project.id}` ? null : `proj:${project.id}`); }} className="absolute right-1.5 p-1.5 rounded-md text-gray-500 hover:text-white hover:bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity">
            <MoreHorizontal className="w-4 h-4" />
          </button>

          {openMenuId === `proj:${project.id}` && (
            <div className="absolute right-0 top-full mt-1 w-48 bg-[#212121] border border-white/10 rounded-xl shadow-2xl z-50 py-1.5 overflow-hidden">
              <button onClick={(e) => handleRenameProject(e, project)} className="w-full flex items-center gap-3 px-3.5 py-2 text-[13px] text-gray-300 hover:bg-white/5 hover:text-white transition-colors"><Pencil className="w-3.5 h-3.5" /> Rename</button>
              <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpenMenuId(null); handleNewChatInProject(project.id); }} className="w-full flex items-center gap-3 px-3.5 py-2 text-[13px] text-gray-300 hover:bg-white/5 hover:text-white transition-colors"><Plus className="w-3.5 h-3.5" /> New Chat Here</button>
              <div className="h-px bg-white/5 my-1" />
              <button onClick={(e) => handleDeleteProject(e, project)} className="w-full flex items-center gap-3 px-3.5 py-2 text-[13px] text-red-400 hover:bg-red-500/10 transition-colors"><Trash2 className="w-3.5 h-3.5" /> Delete Project</button>
            </div>
          )}
        </div>

        {isExpanded && (
          <div className="ml-2 border-l border-white/5 pl-1 space-y-1 mt-0.5">
            {projectChats.length > 0 ? projectChats.map(chat => renderChatItem(chat)) : (
              <p className="px-5 py-1.5 text-[11px] text-gray-600 italic">No chats yet.</p>
            )}
            <button onClick={() => handleNewChatInProject(project.id)} className="w-full flex items-center gap-2 px-4 py-1.5 text-[12px] text-gray-500 hover:text-gray-300 transition-colors">
              <Plus className="w-3 h-3" /> New chat
            </button>
          </div>
        )}
      </div>
    );
  };

  useEffect(() => {
    async function loadUser() {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        setUserData({
          name: session.user.user_metadata?.full_name || "Scholar",
          email: session.user.email || "",
          tier: session.user.user_metadata?.tier || "free",
          role: session.user.user_metadata?.role || "student",
          credits: session.user.user_metadata?.credits || 0,
          createdAt: session.user.created_at,
          avatarUrl: session.user.user_metadata?.avatar_url || ""
        });

        const joinDate = new Date(session.user.created_at);
        const trialEndDate = new Date(joinDate.getTime() + 30 * 24 * 60 * 60 * 1000);
        const today = new Date();
        const daysLeft = Math.ceil((trialEndDate.getTime() - today.getTime()) / (1000 * 3600 * 24));
        setDaysLeftInTrial(daysLeft > 0 ? daysLeft : 0);

        if (
          session.user.user_metadata?.role === 'admin' ||
          session.user.user_metadata?.tier === 'pro_scholar' ||
          daysLeft > 0
        ) {
          setHasPremiumAccess(true);
        } else {
          setHasPremiumAccess(false);
        }
      }
    }
    loadUser();
  }, []);

  useEffect(() => {
    async function loadSidebarData() {
      if (userData.role === 'guest' || !userData.email) {
        setIsWorkspacesLoading(false);
        setProjects([]); setChats([]);
        return;
      }

      setIsWorkspacesLoading(true);
      try {
        const [projRes, chatRes] = await Promise.all([
          fetchAPI("/chat/projects"),
          fetchAPI("/chat/workspaces"),
        ]);
        if (projRes?.data) setProjects(projRes.data);
        if (chatRes?.data) setChats(chatRes.data);
      } catch (error) {
        console.error("Failed to load sidebar data:", error);
      } finally {
        setIsWorkspacesLoading(false);
      }
    }
    loadSidebarData();
  }, [userData.email, userData.role]);

  useEffect(() => {
    if (settingsTab === "performance") {
      async function loadPerformanceData() {
        try {
          const res = await fetchAPI("/logger/mapping");
          if (res.data) {
            setMappingData(res.data);
            setAiEvaluation(res.ai_evaluation);
          }
        } catch (e) { console.error(e); }
      }
      loadPerformanceData();
    }
  }, [settingsTab]);

  // 🔴 NEW: Billing tab's "142 Queries / 12 PDFs Analyzed" was hardcoded —
  // now pulled live from the /chat/stats endpoint.
  // 🔴 Safely restricted to non-guests
  useEffect(() => {
    const role = userData?.role?.toLowerCase() || "";
    if (settingsTab === "billing" && isSettingsOpen && role !== "guest") {
      async function loadStats() {
        try {
          const res = await fetchAPI("/chat/stats");
          if (res) setUserStats({ queries: res.queries || 0, documents_analyzed: res.documents_analyzed || 0 });
        } catch (e) { console.error("Failed to load stats:", e); }
      }
      loadStats();
    }
  }, [settingsTab, isSettingsOpen, userData?.role]);

  // 🔴 NEW: real handlers for the AI Memory tab, replacing the two alert()-only stubs
  const handleClearCache = () => {
    setIsClearingCache(true);
    try {
      // Client-side cache only — safe to clear directly, no confirmation needed
      sessionStorage.clear();
      setTimeout(() => setIsClearingCache(false), 600);
    } catch (e) {
      console.error("Cache clear failed:", e);
      setIsClearingCache(false);
    }
  };

  const handleWipeAllHistory = async () => {
    if (!confirm("Delete ALL chats and projects permanently? This cannot be undone.")) return;
    setIsWipingData(true);
    try {
      await fetchAPI("/chat/history/all", { method: "DELETE" });
      setProjects([]);
      setChats([]);
      router.push("/dashboard");
    } catch (e) {
      console.error("Wipe failed:", e);
      alert("Failed to wipe data. Please try again.");
    } finally {
      setIsWipingData(false);
    }
  };

  const [isSupportOpen, setIsSupportOpen] = useState(false);
  const [supportMsg, setSupportMsg] = useState("");
  const [supportChat, setSupportChat] = useState<{role: string, content: string}[]>([{ role: 'bot', content: 'Hi there! Need help navigating the GSTU Ecosystem?' }]);
  const [isSupportLoading, setIsSupportLoading] = useState(false);

  const handleSupportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if(!supportMsg.trim()) return;
    
    const newChat = [...supportChat, { role: 'user', content: supportMsg }];
    setSupportChat(newChat);
    setSupportMsg("");
    setIsSupportLoading(true);

    try {
      const res = await fetchAPI("/chat/ecosystem-support", {
        method: "POST",
        body: JSON.stringify({ message: supportMsg })
      });
      setSupportChat([...newChat, { role: 'bot', content: res.reply }]);
    } catch (err) {
      setSupportChat([...newChat, { role: 'bot', content: "Connection error. Please try again." }]);
    } finally {
      setIsSupportLoading(false);
    }
  };

  // STRICT ROUTE GUARD
  useEffect(() => {
    if (!userData.role) return; // now correctly waits for the real role to load

    if (userData.role === 'guest') {
      const isAllowed = pathname === '/dashboard' || pathname.startsWith('/dashboard/workspaces');
      if (!isAllowed) {
        alert("🔒 Clearance Level: Guest. You cannot access premium modules. Redirecting...");
        router.push('/dashboard');
        return;
      }
    }

    if (pathname === '/dashboard/faculty' && userData.role === 'student') {
      alert("🔒 Clearance Level: Faculty. Students cannot access this node.");
      router.push('/dashboard');
      return;
    }
  }, [pathname, userData.role, router]);

  const handleLogout = async () => {
    setIsLoading(true);
    await supabase.auth.signOut();
    router.push("/auth/login");
  };

  const [userRole, setUserRole] = useState("guest");
  const [showVerificationModal, setShowVerificationModal] = useState(false);
  const [showGuestLockModal, setShowGuestLockModal] = useState(false);

  useEffect(() => {
    // Load User Role from Session
    const session = localStorage.getItem('supabase_session');
    if (session) {
      const parsed = JSON.parse(session);
      const role = parsed.user?.user_metadata?.role?.toLowerCase() || "guest";
      const dept = parsed.user?.user_metadata?.department;
      
      setUserRole(role);

      // 🔴 ACADEMIC VERIFICATION TRIGGER
      // If student signed up but hasn't verified department info
      if (role === "student" && !dept) {
        setShowVerificationModal(true);
      }
    }
  }, []);

  // 🔴 GUEST GATEKEEPER ROUTING LOGIC
  const handleNavigation = (targetPath: string, restrictedRoles: string[] = []) => {
    if (userRole === "guest" && restrictedRoles.includes("guest")) {
      setShowGuestLockModal(true);
      return;
    }
    
    // Faculty Approval Lock
    if (userRole === "faculty_pending" && targetPath.includes("/admin")) {
      alert("Your faculty account is pending verification by the University Admin.");
      return;
    }

    router.push(targetPath);
  };

  return (
    <div className="flex h-screen text-gray-200 font-sans relative overflow-hidden bg-[url('/background_pic.png')] bg-cover bg-center bg-no-repeat" style={{ backgroundColor: 'rgba(15, 17, 21, 0.92)', backgroundBlendMode: 'overlay' }}>
      {/* 🔴 GUEST LOCK MODAL */}
      {showGuestLockModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-[#171717] border border-rose-500/30 p-8 rounded-3xl max-w-md w-full text-center shadow-2xl">
            <div className="w-16 h-16 bg-rose-500/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-rose-500/20">
              <Lock className="w-8 h-8 text-rose-500" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Security Clearance Required</h2>
            <p className="text-sm text-gray-400 mb-6">
              Guest viewing is limited to public UI browsing and 20 daily AI chats. Accessing academic nodes requires a verified GSTU account.
            </p>
            <div className="flex gap-4 justify-center">
              <button onClick={() => setShowGuestLockModal(false)} className="px-5 py-2.5 rounded-xl text-sm font-bold text-gray-400 hover:text-white transition-colors">Cancel</button>
              <button onClick={() => router.push('/auth/login')} className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-bold transition-colors">Login / Sign Up</button>
            </div>
          </div>
        </div>
      )}

      {/* 🔴 ACADEMIC VERIFICATION MODAL (For new students) */}
      {showVerificationModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-md animate-in fade-in">
          <div className="bg-[#1e1e1e] border border-emerald-500/30 p-8 rounded-3xl max-w-lg w-full shadow-2xl">
             <div className="flex items-center gap-3 mb-6">
               <ShieldAlert className="w-6 h-6 text-emerald-400" />
               <h2 className="text-xl font-bold text-white">Verify Academic Information</h2>
             </div>
             <p className="text-sm text-gray-400 mb-6">To access the AI Ecosystem, you must verify your departmental identity to prevent misuse.</p>
             
             {/* Verification Form (Will wire backend logic later) */}
             <div className="space-y-4">
               <input type="text" placeholder="Student ID (e.g. 2021...)" className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl p-3 text-white focus:border-emerald-500 outline-none" />
               <select className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl p-3 text-gray-300 focus:border-emerald-500 outline-none">
                 <option>International Relations (IR)</option>
                 <option>Computer Science (CSE)</option>
               </select>
               <button onClick={() => setShowVerificationModal(false)} className="w-full bg-emerald-600 text-white font-bold py-3 rounded-xl">Submit Verification</button>
             </div>
          </div>
        </div>
      )}

      <aside className={`${isSidebarOpen ? "w-64 border-r border-white/5" : "w-0 border-none"} transition-all duration-300 ease-in-out bg-[#171717] h-screen flex flex-col shrink-0 z-30 overflow-hidden`}>
        <div className="flex flex-col h-full w-64">
          <div className="shrink-0 p-4 border-b border-white/5 bg-[#171717] z-20">
            <div className="flex items-center justify-between min-w-[14rem]">
              <div className="h-20 flex px-3 border-b border-white/5 shrink-0">
                <Link href="/dashboard" className="flex items-center gap-3 group">
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

            {/* 2. DYNAMIC SEARCH BAR (Perfectly positioned per screenshot) */}
            <div className="px-3 mb-4 relative z-50">
              <div className="relative group">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500 group-focus-within:text-indigo-400 transition-colors" />
                <input 
                  type="text" 
                  placeholder="Search projects..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-[#0a0a0a] border border-white/5 rounded-lg py-1.5 pl-8 pr-3 text-[12px] text-gray-200 placeholder:text-gray-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-all shadow-inner"
                />
                {isSearching && (
                  <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-indigo-400 animate-spin" />
                )}
              </div>

              {/* SEARCH RESULTS DROPDOWN (Sleeker design) */}
              {searchQuery.trim().length >= 2 && (
                <div className="absolute top-[calc(100%+6px)] left-3 right-3 bg-[#1e1e1e] border border-white/10 rounded-lg shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-1">
                  {searchResults.length > 0 ? (
                    <div className="max-h-60 overflow-y-auto custom-scrollbar">
                      {searchResults.map((result, i) => (
                        <button
                          key={i}
                          onClick={() => {
                            if (result.type === "workspace") router.push(`/dashboard/workspaces/${result.id}`);
                            setSearchQuery(""); 
                          }}
                          className="w-full flex items-center gap-2.5 px-3 py-2.5 hover:bg-white/5 transition-colors border-b border-white/5 last:border-0 text-left"
                        >
                          <MessageSquare className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                          <span className="text-[12px] font-medium text-gray-200 truncate">
                            {result.title}
                          </span>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="p-3 text-center text-[11px] text-gray-500">
                      {!isSearching && "No results found."}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-6 min-w-[16rem] custom-scrollbar">

            {/* 🔴 FIX: text-white-100 / text-white-400 / text-white-600 are not
                real Tailwind classes ("white" has no numeric shade scale) —
                they silently no-op, replaced with real gray shades below. */}

            {/* Main Dashboard Link */}
            <button onClick={() => router.push('/dashboard')} className={`flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors w-full text-left ${pathname === "/dashboard" ? "bg-[#2f2f2f] text-gray-100" : "text-gray-400 hover:bg-[#2f2f2f] hover:text-gray-200"}`}>
              <LayoutDashboard className="w-4 h-4" />
              <span className="font-medium text-[13px]">Dashboard</span>
            </button>

            <div>
              <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2 ml-3">Apps & Tools</h3>
              <div className="space-y-1">
                {/* 🔴 Replaced <Link> with <button> to enforce Security Modal */}
                <button onClick={() => handleNavigation('/dashboard/scholar-hub', ['guest'])} className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-colors ${pathname.includes("scholar-hub") ? 'bg-white/10 text-white' : "text-gray-400 hover:text-gray-200 hover:bg-white/5"}`}>
                  <Brain className="w-4 h-4 text-blue-400" /> Scholar Hub {userData.role === 'guest' && <Lock className="w-3 h-3 ml-auto opacity-50" />}
                </button>
                
                <button onClick={() => handleNavigation('/dashboard/study-hub', ['guest'])} className={`w-full flex items-center gap-2.5 px-3 py-2.5 text-[13px] font-medium transition-colors rounded-lg ${pathname.includes("study-hub") ? "bg-white/10 text-white" : "text-gray-400 hover:text-gray-200 hover:bg-white/5"}`}>
                  <Gamepad2 className="w-4 h-4 text-rose-400" /> Interactive Study Hub {userData.role === 'guest' && <Lock className="w-3 h-3 ml-auto opacity-50" />}
                </button>
                
                <button onClick={() => handleNavigation('/dashboard/department', ['guest'])} className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-colors ${pathname.includes("department") ? "bg-white/10 text-white" : "text-gray-400 hover:text-gray-200 hover:bg-white/5"}`}>
                  <Building2 className="w-4 h-4 text-blue-400" /> Department Hub {userData.role === 'guest' && <Lock className="w-3 h-3 ml-auto opacity-50" />}
                </button>
                
                <button onClick={() => handleNavigation('/dashboard/copilot', ['guest'])} className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-colors ${pathname.includes("copilot") ? 'bg-white/10 text-white' : "text-gray-400 hover:text-gray-200 hover:bg-white/5"}`}>
                  <Sparkles className="w-4 h-4 text-amber-400" /> Academic Copilot {userData.role === 'guest' && <Lock className="w-3 h-3 ml-auto opacity-50" />}
                </button>
                
                {/* 🔴 ACADEMIC CLEARANCE: Only visible to Admins and Faculty */}
                {(userData.role === 'admin' || userData.role === 'faculty') && (
                  <button onClick={() => handleNavigation('/dashboard/admin')} className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-colors ${pathname.includes("admin") ? 'bg-white/10 text-white' : "text-gray-400 hover:text-gray-200 hover:bg-white/5"}`}>
                    <ShieldCheck className="w-4 h-4 text-emerald-400" /> Faculty Node
                  </button>
                )}
              </div>
            </div>

            {/* Your Workspaces = Project Folders */}
            <div className="mb-6">
              <div className="flex items-center justify-between px-4 mb-2">
                <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Your Workspaces</p>
                <button onClick={handleNewProject} title="New Project" className="text-gray-500 hover:text-white hover:bg-white/10 p-1 rounded-md transition-colors">
                  <FolderPlus className="w-4 h-4" />
                </button>
              </div>
              <div className="space-y-0.5">
                {isWorkspacesLoading ? (
                  <div className="px-4 py-3 text-sm text-gray-500 flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> Syncing...
                  </div>
                ) : projects.length > 0 ? (
                  projects.map(renderProjectItem)
                ) : (
                  <p className="px-5 py-2 text-xs text-gray-600 italic">No projects yet — click the folder icon to start one.</p>
                )}
              </div>
            </div>

            {/* Recents = ungrouped chats */}
            <div className="mb-8">
              <div className="flex items-center justify-between px-4 mb-2">
                <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Recents</p>
                <button onClick={() => handleNewChatInProject(null)} title="New Chat" className="text-gray-500 hover:text-white hover:bg-white/10 p-1 rounded-md transition-colors">
                  <Plus className="w-4 h-4" />
                </button>
              </div>
              <div className="space-y-1">
                {!isWorkspacesLoading && recentChats.length > 0 ? recentChats.map(chat => renderChatItem(chat)) : !isWorkspacesLoading ? (
                  <p className="px-5 py-2 text-xs text-gray-600 italic">No recent chats.</p>
                ) : null}
              </div>
            </div>
          </nav>

          <div className="shrink-0 p-3 border-t border-white/5 bg-[#171717] z-20 relative">
            <input
              id="avatar-upload-input"
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleAvatarUpload}
            />
            {isProfileMenuOpen && (
              <div className="absolute bottom-[110%] left-3 w-56 bg-[#212121] border border-white/10 rounded-xl shadow-2xl z-50 py-1.5 overflow-hidden animate-in fade-in slide-in-from-bottom-2">
                <div className="px-4 py-3 border-b border-white/5 mb-1">
                  <p className="text-sm font-bold text-white truncate">{userData.name}</p>
                  <p className="text-[11px] text-gray-400 truncate">{userData.email}</p>
                </div>
                <button
                  onClick={() => document.getElementById('avatar-upload-input')?.click()}
                  disabled={isUploadingAvatar}
                  className="w-full flex items-center gap-2.5 px-3 py-2.5 text-[13px] font-medium text-gray-300 hover:bg-white/5 hover:text-white transition-colors disabled:opacity-50"
                >
                  {isUploadingAvatar ? <Loader2 className="w-4 h-4 animate-spin" /> : <User className="w-4 h-4" />}
                  {isUploadingAvatar ? "Uploading..." : "Change Avatar"}
                </button>
                <button onClick={handleLogout} className="w-full flex items-center gap-2.5 px-3 py-2.5 text-[13px] font-medium text-red-400 hover:bg-red-500/10 transition-colors">
                  <LogOut className="w-4 h-4" /> Sign Out
                </button>
              </div>
            )}

            <div className="flex items-center justify-between p-1.5 hover:bg-white/5 rounded-xl transition-colors group">
              <div onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)} className="flex items-center gap-3 cursor-pointer flex-1 min-w-0">
                {userData.avatarUrl ? (
                  <img src={userData.avatarUrl} alt={userData.name} className="w-8 h-8 rounded-full object-cover shrink-0 shadow-inner" />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-xs shadow-inner shrink-0">
                    {userData.name.charAt(0).toUpperCase()}
                  </div>
                )}
                <div className="flex flex-col min-w-0 pr-2">
                  <span className="text-[13px] font-bold text-gray-200 leading-tight truncate">{userData.name.split(' ')[0]}</span>
                  <span className={`text-[9px] font-bold uppercase tracking-wider ${userData.tier === 'pro_scholar' ? 'text-indigo-400' : 'text-gray-500'}`}>
                    {userData.tier === 'pro_scholar' ? 'PRO SCHOLAR' : 'FREE PLAN'}
                  </span>
                </div>
              </div>

              <button onClick={() => { setIsSettingsOpen(true); setIsProfileMenuOpen(false); }} className="p-2 text-gray-500 hover:text-white hover:bg-white/10 rounded-lg transition-all focus:outline-none shrink-0">
                <Settings className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </aside>

      <main className="flex-1 min-w-0 relative flex flex-col h-screen bg-[#212121]">
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

        {isSettingsOpen && (
          <div className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-[#171717] w-full max-w-5xl h-[85vh] rounded-2xl shadow-2xl flex overflow-hidden border border-white/10 animate-in fade-in zoom-in-95 font-sans">
              <div className="w-64 bg-[#121212] border-r border-white/5 flex flex-col shrink-0">
                <div className="p-6 pb-4">
                  <h2 className="text-xl font-bold text-white">Settings</h2>
                </div>

                <div className="flex-1 px-3 space-y-1">
                  <button onClick={() => setSettingsTab("general")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[14px] font-medium transition-all ${settingsTab === "general" ? "bg-white/10 text-white" : "text-gray-400 hover:bg-white/5 hover:text-gray-200"}`}>
                    <Monitor className="w-4 h-4" /> General
                  </button>
                  
                  {/* 🔴 ABSOLUTE GUEST LOCK: Checks multiple possible states of user role */}
                  {['admin', 'faculty', 'student', 'pro_scholar'].includes(userData?.role?.toLowerCase() || '') && (
                    <>
                      <button onClick={() => setSettingsTab("billing")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[14px] font-medium transition-all ${settingsTab === "billing" ? "bg-indigo-500/10 text-indigo-400" : "text-gray-400 hover:bg-white/5 hover:text-gray-200"}`}>
                        <CreditCard className="w-4 h-4" /> Billing & Pro
                      </button>
                      <button onClick={() => setSettingsTab("rewards")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[14px] font-medium transition-all ${settingsTab === "rewards" ? "bg-amber-500/10 text-amber-400" : "text-gray-400 hover:bg-white/5 hover:text-gray-200"}`}>
                        <Gift className="w-4 h-4" /> Earn Rewards
                      </button>
                      <button onClick={() => setSettingsTab("memory")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[14px] font-medium transition-all ${settingsTab === "memory" ? "bg-emerald-500/10 text-emerald-400" : "text-gray-400 hover:bg-white/5 hover:text-gray-200"}`}>
                        <Brain className="w-4 h-4" /> AI Memory
                      </button>
                      <button onClick={() => setSettingsTab("performance")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[14px] font-medium transition-all ${settingsTab === "performance" ? "bg-emerald-500/10 text-emerald-400" : "text-gray-400 hover:bg-white/5 hover:text-gray-200"}`}>
                        <Activity className="w-4 h-4" /> Performance
                      </button>
                    </>
                  )}
                </div>
              </div>

              <div className="flex-1 bg-[#171717] flex flex-col">
                <div className="flex justify-end p-4 shrink-0">
                  <button onClick={() => setIsSettingsOpen(false)} className="p-2 text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-colors"><X className="w-5 h-5" /></button>
                </div>

                <div className="flex-1 overflow-y-auto px-10 pb-12 custom-scrollbar">
                  {settingsTab === "billing" && (
                    <div className="max-w-3xl mx-auto animate-in fade-in">
                      <h3 className="text-2xl font-bold text-white mb-8">Subscription & Billing</h3>

                      <div className="bg-gradient-to-r from-indigo-500/20 via-purple-500/10 to-transparent border border-indigo-500/30 rounded-3xl p-8 mb-10 flex items-center justify-between relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/20 rounded-full blur-3xl"></div>
                        <div className="relative z-10">
                          <h4 className="text-xl font-bold text-white mb-1">Your Lifetime Impact</h4>
                          <p className="text-sm text-indigo-200/70">Track your academic progress through GSTU OS.</p>
                        </div>
                        <div className="flex gap-8 relative z-10">
                          <div className="text-center">
                            <div className="text-4xl font-black text-white mb-1">{userStats.queries}</div>
                            <div className="text-[11px] font-bold text-indigo-300 uppercase tracking-wider">Queries</div>
                          </div>
                          <div className="w-px h-14 bg-indigo-500/30"></div>
                          <div className="text-center">
                            <div className="text-4xl font-black text-white mb-1">{userStats.documents_analyzed}</div>
                            <div className="text-[11px] font-bold text-indigo-300 uppercase tracking-wider">PDFs Analyzed</div>
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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

                        <div className="bg-gradient-to-b from-[#1e1e1e] to-[#121212] border border-indigo-500/50 rounded-3xl p-8 shadow-[0_0_30px_rgba(99,102,241,0.15)] relative">
                          <div className="absolute top-0 right-0 bg-indigo-500 text-white text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-bl-xl">Recommended</div>
                          <h3 className="text-xl font-bold text-indigo-400 mb-2 flex items-center gap-2"><Zap className="w-5 h-5" /> GSTU Pro Scholar</h3>
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
                                      if (!el.value) return alert("Enter TrxID!");
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

                  {settingsTab === "general" && (
                    <div className="max-w-2xl animate-in fade-in">
                      <h3 className="text-2xl font-bold text-white mb-8">General Settings</h3>
                      <div className="space-y-6">

                        {/* Profile */}
                        <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl">
                          <div className="flex justify-between items-center mb-4">
                            <div>
                              <h4 className="font-bold text-white">Profile</h4>
                              <p className="text-sm text-gray-400">Your name and email on this account.</p>
                            </div>
                            {!isEditingProfile && (
                              <button onClick={startEditingProfile} className="text-xs font-bold text-indigo-400 hover:text-indigo-300 transition-colors">
                                Edit
                              </button>
                            )}
                          </div>

                          {!isEditingProfile ? (
                            <div className="space-y-3">
                              <div className="flex justify-between items-center py-2 border-b border-white/5">
                                <span className="text-sm text-gray-500">Name</span>
                                <span className="text-sm text-gray-200 font-medium">{userData.name}</span>
                              </div>
                              <div className="flex justify-between items-center py-2">
                                <span className="text-sm text-gray-500">Email</span>
                                <span className="text-sm text-gray-200 font-medium">{userData.email}</span>
                              </div>
                            </div>
                          ) : (
                            <div className="space-y-3">
                              <div>
                                <label className="block text-[10px] text-gray-500 uppercase mb-1">Name</label>
                                <input
                                  type="text"
                                  value={profileDraft.full_name}
                                  onChange={(e) => setProfileDraft(prev => ({ ...prev, full_name: e.target.value }))}
                                  className="w-full bg-[#0a0a0a] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                />
                              </div>
                              <div>
                                <label className="block text-[10px] text-gray-500 uppercase mb-1">Email</label>
                                <input
                                  type="email"
                                  value={profileDraft.email}
                                  onChange={(e) => setProfileDraft(prev => ({ ...prev, email: e.target.value }))}
                                  className="w-full bg-[#0a0a0a] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                />
                                <p className="text-[11px] text-gray-500 mt-1">Changing your email may require re-verification.</p>
                              </div>
                              <div className="flex gap-2 pt-1">
                                <button
                                  onClick={handleSaveProfile}
                                  disabled={isSavingProfile}
                                  className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold py-2 rounded-lg transition-colors disabled:opacity-50"
                                >
                                  {isSavingProfile ? "Saving..." : "Save Changes"}
                                </button>
                                <button
                                  onClick={() => setIsEditingProfile(false)}
                                  className="px-4 bg-white/5 hover:bg-white/10 text-gray-300 text-sm font-bold py-2 rounded-lg transition-colors"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Theme */}
                        <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl flex justify-between items-center">
                          <div>
                            <h4 className="font-bold text-white">App Theme</h4>
                            <p className="text-sm text-gray-400">Select your preferred interface color.</p>
                          </div>
                          <select
                            value={theme}
                            onChange={(e) => handleThemeChange(e.target.value)}
                            className="bg-[#121212] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none text-sm"
                          >
                            <option value="dark">Dark Mode (Default)</option>
                            <option value="light">Light Mode</option>
                            <option value="system">System</option>
                          </select>
                        </div>

                        {/* Account Role — visible to everyone, but only editable
                            for emails in the hardcoded allowlist. The dropdown
                            being disabled is a UX convenience only; the real
                            enforcement is server-side in account.py. */}
                        <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl flex justify-between items-center">
                          <div>
                            <h4 className="font-bold text-white">Account Role (RBAC)</h4>
                            <p className="text-sm text-gray-400">
                              {canChangeRole
                                ? "You're authorized to change this account's role."
                                : "Your registered ecosystem role. Contact an administrator to change it."}
                            </p>
                          </div>
                          <select
                            disabled={!canChangeRole || isChangingRole}
                            value={userData.role}
                            onChange={(e) => handleRoleChange(e.target.value)}
                            className="bg-[#121212] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none text-sm disabled:opacity-50 capitalize"
                          >
                            <option value="student">Student Mode</option>
                            <option value="faculty">Faculty / Admin Node</option>
                            <option value="admin">Super Admin</option>
                          </select>
                        </div>

                        {/* Privacy & Help */}
                        <button
                          onClick={() => { setHelpPrivacyTab("help"); setIsHelpPrivacyOpen(true); }}
                          className="w-full bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl flex justify-between items-center hover:bg-white/5 transition-colors text-left"
                        >
                          <div>
                            <h4 className="font-bold text-white">Help Center & Privacy Policy</h4>
                            <p className="text-sm text-gray-400">Usage guides, support contact, and data protection details.</p>
                          </div>
                          <ArrowRight className="w-4 h-4 text-gray-500" />
                        </button>

                        {/* Danger Zone */}
                        <div className="bg-[#1e1e1e] border border-rose-500/20 p-6 rounded-2xl">
                          <h4 className="font-bold text-rose-400 mb-1">Danger Zone</h4>
                          <p className="text-sm text-gray-400 mb-4">Permanently delete your account and all associated data. This cannot be undone.</p>
                          <button
                            onClick={handleDeleteAccount}
                            disabled={isDeletingAccount}
                            className="bg-rose-600 hover:bg-rose-700 text-white text-sm font-bold px-5 py-2.5 rounded-lg transition-colors disabled:opacity-50"
                          >
                            {isDeletingAccount ? "Deleting..." : "Disable / Delete Account"}
                          </button>
                        </div>

                      </div>
                    </div>
                  )}

                  {/* Help & Privacy Modal — ChatGPT/Claude-style overlay */}
                  {isHelpPrivacyOpen && (
                    <div className="fixed inset-0 z-[110] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
                      <div className="bg-[#171717] w-full max-w-2xl max-h-[80vh] rounded-2xl shadow-2xl border border-white/10 flex flex-col overflow-hidden animate-in fade-in zoom-in-95">
                        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 shrink-0">
                          <h3 className="text-lg font-bold text-white">Help Center & Privacy Policy</h3>
                          <button onClick={() => setIsHelpPrivacyOpen(false)} className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors">
                            <X className="w-4 h-4" />
                          </button>
                        </div>

                        <div className="flex gap-1 px-6 pt-4 shrink-0">
                          <button
                            onClick={() => setHelpPrivacyTab("help")}
                            className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${helpPrivacyTab === "help" ? "bg-white/10 text-white" : "text-gray-500 hover:text-gray-300"}`}
                          >
                            🆘 Help Center
                          </button>
                          <button
                            onClick={() => setHelpPrivacyTab("privacy")}
                            className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${helpPrivacyTab === "privacy" ? "bg-white/10 text-white" : "text-gray-500 hover:text-gray-300"}`}
                          >
                            🔐 Privacy Policy
                          </button>
                        </div>

                        <div className="flex-1 overflow-y-auto px-6 py-5 custom-scrollbar">
                          {helpPrivacyTab === "help" ? (
                            <div className="space-y-3">
                              <h4 className="text-base font-bold text-white mb-3">How to use GSTU AI?</h4>
                              {[
                                { q: "1. How do I switch AI engines?", a: "Click the dropdown menu at the top of the chat interface to switch between Fast Engine (Llama), Web Search (Gemini), and Offline Mode." },
                                { q: "2. How does the offline mode work?", a: "You must run the local GPT4All server on port 4891. Your data never leaves your device." },
                                { q: "3. Need further support?", a: "Contact the admin at: yousufaltashfin@gmail.com" },
                              ].map((item, i) => (
                                <details key={i} className="group bg-[#1e1e1e] border border-white/5 rounded-xl overflow-hidden">
                                  <summary className="px-4 py-3 text-sm font-medium text-gray-200 cursor-pointer list-none flex items-center justify-between hover:bg-white/5 transition-colors">
                                    {item.q}
                                    <span className="text-gray-500 group-open:rotate-180 transition-transform">▾</span>
                                  </summary>
                                  <p className="px-4 pb-4 text-sm text-gray-400 leading-relaxed">{item.a}</p>
                                </details>
                              ))}
                            </div>
                          ) : (
                            <div className="prose prose-invert prose-sm max-w-none">
                              <h4 className="text-base font-bold text-white mb-1">GSTU IR AI — Data Protection Agreement</h4>
                              <ul className="space-y-3 text-sm text-gray-300 leading-relaxed list-none pl-0 mt-4">
                                <li><strong className="text-white">1. Encrypted in Transit and at Rest (TLS/SSL and AES-256):</strong> All chat queries and vector embeddings are secured.</li>
                                <li><strong className="text-white">2. Zero Data Selling:</strong> We do not sell your academic prompts or personal data to third parties.</li>
                                <li><strong className="text-white">3. Institutional Data:</strong> Uploaded PDFs are stored securely and are not exposed to third parties unless specifically processed by a cloud AI model you selected.</li>
                                <li><strong className="text-white">4. Supabase Auth:</strong> Authentication is managed securely via Supabase's OAuth 2.0 protocols.</li>
                              </ul>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {settingsTab === "rewards" && (
                    <div className="max-w-2xl animate-in fade-in">
                      <h3 className="text-2xl font-bold text-white mb-8 flex items-center gap-3"><Gift className="w-6 h-6 text-rose-500" /> Earn Free Credits</h3>
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

                  {settingsTab === "memory" && (
                    <div className="max-w-2xl animate-in fade-in">
                      <h3 className="text-2xl font-bold text-white mb-8 flex items-center gap-3"><Brain className="w-6 h-6 text-emerald-500" /> AI Memory Management</h3>
                      <div className="space-y-6">
                        <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl flex justify-between items-center">
                          <div>
                            <h4 className="font-bold text-white mb-1">Clear AI Cache</h4>
                            <p className="text-sm text-gray-400">Wipes local browser cache to speed up the dashboard.</p>
                          </div>
                          <button
                            onClick={handleClearCache}
                            disabled={isClearingCache}
                            className="bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 px-5 py-2.5 rounded-lg text-sm font-bold transition-colors disabled:opacity-50"
                          >
                            {isClearingCache ? "Clearing..." : "Clear Cache"}
                          </button>
                        </div>

                        <div className="bg-[#1e1e1e] border border-rose-500/20 p-6 rounded-2xl flex justify-between items-center">
                          <div>
                            <h4 className="font-bold text-white mb-1">Delete Chat History</h4>
                            <p className="text-sm text-gray-400">Permanently erases all your projects and conversations from the database.</p>
                          </div>
                          <button
                            onClick={handleWipeAllHistory}
                            disabled={isWipingData}
                            className="bg-rose-600 hover:bg-rose-700 text-white px-5 py-2.5 rounded-lg text-sm font-bold transition-colors shadow-lg disabled:opacity-50"
                          >
                            {isWipingData ? "Wiping..." : "Wipe Data"}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {settingsTab === "performance" && (
                    <div className="space-y-6 animate-in fade-in slide-in-from-right-4">
                      <div className="bg-indigo-500/10 border border-indigo-500/20 p-5 rounded-2xl flex items-start gap-4">
                        <Brain className="w-6 h-6 text-indigo-400 shrink-0 mt-0.5" />
                        <div>
                          <h4 className="text-sm font-bold text-indigo-300 uppercase tracking-wider mb-1">AI Performance Evaluation</h4>
                          <p className="text-indigo-100 text-[14px] leading-relaxed font-medium">{aiEvaluation || "Loading insights..."}</p>
                        </div>
                      </div>

                      <div className="bg-[#171717] border border-white/5 p-6 rounded-2xl shadow-inner">
                        <h4 className="text-[13px] font-bold text-gray-400 uppercase tracking-wider mb-6 flex items-center justify-between">
                          <span>Study vs Sleep Analysis</span>
                          <span className="text-[10px] bg-white/5 px-2 py-1 rounded">Last 7 Days</span>
                        </h4>

                        {mappingData.length > 0 ? (
                          <div className="flex items-end justify-between gap-2 h-40 border-b border-white/10 pb-2">
                            {mappingData.map((log: any, i: number) => {
                              const studyHeight = Math.min(((log.study_minutes / 60) / 12) * 100, 100);
                              const sleepHeight = Math.min((log.sleep_hours / 12) * 100, 100);
                              const dateLabel = new Date(log.created_at).toLocaleDateString('en-US', { weekday: 'short' });

                              return (
                                <div key={i} className="flex-1 flex flex-col items-center justify-end gap-2 group relative">
                                  <div className="w-full flex justify-center gap-1 items-end h-full relative">
                                    <div className="absolute bottom-full mb-2 hidden group-hover:block bg-[#2a2a2a] text-[11px] p-2.5 rounded-lg whitespace-nowrap z-10 border border-white/10 shadow-xl">
                                      <div className="text-indigo-400">Study: {(log.study_minutes / 60).toFixed(1)}h</div>
                                      <div className="text-purple-400">Sleep: {log.sleep_hours}h</div>
                                      <div className="text-amber-400 mt-1 pt-1 border-t border-white/5">Mood: {log.mood}</div>
                                    </div>
                                    <div style={{ height: `${studyHeight}%` }} className="w-2.5 md:w-5 bg-indigo-500 rounded-t-sm transition-all duration-500"></div>
                                    <div style={{ height: `${sleepHeight}%` }} className="w-2.5 md:w-5 bg-purple-500/40 rounded-t-sm transition-all duration-500"></div>
                                  </div>
                                  <span className="text-[9px] font-bold text-gray-500 uppercase mt-1">{dateLabel}</span>
                                </div>
                              )
                            })}
                          </div>
                        ) : (
                          <div className="h-40 flex items-center justify-center text-gray-600 text-sm italic">No data logged yet.</div>
                        )}

                        <div className="flex gap-4 mt-4 justify-center">
                          <div className="flex items-center gap-1.5 text-[10px] font-bold text-gray-400 uppercase"><div className="w-2 h-2 bg-indigo-500 rounded-full"></div> Study</div>
                          <div className="flex items-center gap-1.5 text-[10px] font-bold text-gray-400 uppercase"><div className="w-2 h-2 bg-purple-500/40 rounded-full"></div> Sleep</div>
                        </div>
                      </div>

                      <div className="bg-[#171717] border border-white/5 p-6 rounded-2xl shadow-inner">
                        <h4 className="text-[13px] font-bold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2"><Target className="w-4 h-4 text-emerald-400" /> Manual Data Sync</h4>
                        <div className="grid grid-cols-3 gap-3 mb-4">
                          <div>
                            <label className="block text-[10px] text-gray-500 uppercase mb-1">Study (Hrs)</label>
                            <input type="number" min="0" value={logData.study_hours} onChange={e => setLogData({ ...logData, study_hours: e.target.value })} className="w-full bg-[#0a0a0a] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:border-indigo-500" placeholder="e.g. 4" />
                          </div>
                          <div>
                            <label className="block text-[10px] text-gray-500 uppercase mb-1">Sleep (Hrs)</label>
                            <input type="number" min="0" value={logData.sleep_hours} onChange={e => setLogData({ ...logData, sleep_hours: e.target.value })} className="w-full bg-[#0a0a0a] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:border-purple-500" placeholder="e.g. 7" />
                          </div>
                          <div>
                            <label className="block text-[10px] text-gray-500 uppercase mb-1">Mood</label>
                            <select value={logData.mood} onChange={e => setLogData({ ...logData, mood: e.target.value })} className="w-full bg-[#0a0a0a] border border-white/10 rounded-lg px-2 py-2 text-white text-sm focus:border-amber-500">
                              <option>Focused</option>
                              <option>Tired</option>
                              <option>Burned out</option>
                            </select>
                          </div>
                        </div>
                        <button
                          onClick={async () => {
                            setIsLogging(true);
                            await fetchAPI("/logger/daily-log", { method: "POST", body: JSON.stringify({ study_hours: parseInt(logData.study_hours), sleep_hours: parseInt(logData.sleep_hours), mood: logData.mood }) });
                            const res = await fetchAPI("/logger/mapping");
                            if (res.data) { setMappingData(res.data); setAiEvaluation(res.ai_evaluation); }
                            setIsLogging(false); setLogData({ study_hours: "", sleep_hours: "", mood: "Focused" });
                          }}
                          disabled={!logData.study_hours || !logData.sleep_hours || isLogging}
                          className="w-full bg-white/10 hover:bg-emerald-600 text-white font-bold py-3 rounded-xl transition-all disabled:opacity-50 text-sm"
                        >
                          {isLogging ? "Syncing..." : "Sync Daily Log to Database"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
        {/* 🔴 FLOATING CUSTOMER SUPPORT WIDGET */}
        <div className="fixed bottom-6 right-6 z-[100] flex flex-col items-end">
          {isSupportOpen && (
            <div className="bg-[#171717] border border-white/10 rounded-2xl shadow-2xl w-80 mb-4 overflow-hidden animate-in slide-in-from-bottom-4">
              <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-4 flex justify-between items-center">
                <div>
                  <h4 className="text-white font-bold text-sm">GSTU Support</h4>
                  <p className="text-indigo-100 text-[10px]">AI Assistant Online</p>
                </div>
                <button onClick={() => setIsSupportOpen(false)} className="text-white/70 hover:text-white transition-colors"><X className="w-4 h-4" /></button>
              </div>
              
              <div className="h-64 overflow-y-auto p-4 space-y-3 bg-[#0a0a0a] custom-scrollbar">
                {supportChat.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${msg.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-[#212121] text-gray-200 border border-white/5'}`}>
                      {msg.content}
                    </div>
                  </div>
                ))}
                {isSupportLoading && <div className="text-xs text-gray-500 animate-pulse">Typing...</div>}
              </div>
              
              <form onSubmit={handleSupportSubmit} className="p-3 bg-[#171717] border-t border-white/5 flex gap-2">
                <input 
                  type="text" 
                  value={supportMsg} 
                  onChange={e => setSupportMsg(e.target.value)} 
                  placeholder="Ask a question..." 
                  className="flex-1 bg-[#0a0a0a] border border-white/10 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-indigo-500"
                />
                <button disabled={isSupportLoading} type="submit" className="bg-indigo-600 hover:bg-indigo-700 text-white p-2 rounded-lg transition-colors shrink-0">
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>
          )}
          
          <button onClick={() => setIsSupportOpen(!isSupportOpen)} className="w-14 h-14 bg-indigo-600 hover:bg-indigo-700 rounded-full flex items-center justify-center shadow-lg shadow-indigo-600/30 transition-transform hover:scale-105">
            {isSupportOpen ? <X className="w-6 h-6 text-white" /> : <MessageCircle className="w-6 h-6 text-white" />}
          </button>
        </div>
      </main>
    </div>
  );
}