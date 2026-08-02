"use client";

export default function DashboardHomePage() {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">System Overview</h1>
        <p className="text-gray-400 mt-1">Welcome back to your Student Operating System.</p>
      </div>

      {/* Grid for Widgets (Tasks, Routine, Progress) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-4">
        
        {/* Today's Tasks Widget */}
        <div className="bg-white/5 border border-white/10 rounded-3xl p-6 backdrop-blur-xl">
          <h3 className="text-lg font-semibold text-white mb-4">Today's Focus</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-3 p-3 rounded-xl bg-black/40 border border-white/5">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              <p className="text-sm text-gray-300">Read Political Geography Chapter 4</p>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-xl bg-black/40 border border-white/5">
              <div className="w-3 h-3 rounded-full bg-emerald-500" />
              <p className="text-sm text-gray-300">Test FastAPI Sync Endpoint</p>
            </div>
          </div>
        </div>

        {/* Academic Progress Widget */}
        <div className="bg-white/5 border border-white/10 rounded-3xl p-6 backdrop-blur-xl">
          <h3 className="text-lg font-semibold text-white mb-4">Academic Progress</h3>
          <div className="flex items-end gap-2 mb-2">
            <span className="text-4xl font-bold text-white">2.88</span>
            <span className="text-sm text-gray-400 mb-1">/ 4.00 CGPA</span>
          </div>
          <div className="w-full bg-black/40 rounded-full h-2 mt-4 border border-white/5">
            <div className="bg-linear-to-r from-blue-500 to-indigo-500 h-2 rounded-full w-[72%]"></div>
          </div>
          <p className="text-xs text-indigo-400 mt-2 font-medium">Target: 3.50+ (Tracking On)</p>
        </div>
        
      </div>
    </div>
  );
}