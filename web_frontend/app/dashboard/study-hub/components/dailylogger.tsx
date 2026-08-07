'use client';
import { useState } from 'react';
import toast from 'react-hot-toast';
import { createClient } from '../../../utils/supabase/client';

export default function DailyLogger() {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    study_hours: '',
    topics_learned: '',
    notes: ''
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.study_hours || !formData.topics_learned) {
      toast.error("Please fill in hours and topics!");
      return;
    }

    setLoading(true);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        toast.error("Please log in to save your study log.");
        setLoading(false);
        return;
      }

      // 🔴 FIX #1: was `${process.env.NEXT_PUBLIC_API_URL}/api/academic/daily-log`
      // — that route doesn't exist anywhere in the backend. The real, working
      // endpoint is /api/v1/logger/daily-log (same one your Settings modal's
      // full logger already uses successfully).
      //
      // 🔴 FIX #2: was sending `user_id` in the request body. The backend
      // derives the authenticated user's id from the verified JWT via
      // get_current_user() — it never reads a client-supplied user_id field.
      // Sending it in the body did nothing (harmless but dead code) and,
      // more importantly, the request had NO Authorization header at all, so
      // get_current_user() would have rejected every request with a 401
      // before this even reached the database logic.
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/logger/daily-log`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          study_hours: parseFloat(formData.study_hours),
          topics_learned: formData.topics_learned,
          notes: formData.notes || undefined,
        }),
      });

      const data = await res.json();

      if (res.ok) {
        toast.success(data.message || "Study log saved successfully! 🔥 Streak updated.");
        setFormData({ study_hours: '', topics_learned: '', notes: '' });
      } else {
        toast.error(data.detail || "Failed to save log. Try again.");
      }
    } catch (error) {
      console.error("Daily log submit failed:", error);
      toast.error("Network error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 mt-8">
      <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
        📅 Daily Study Logger
      </h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="number"
            step="0.5"
            placeholder="Study Hours (e.g. 2.5)"
            className="p-3 rounded-lg border dark:bg-gray-900 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 outline-none"
            value={formData.study_hours}
            onChange={(e) => setFormData({ ...formData, study_hours: e.target.value })}
          />
          <input
            type="text"
            placeholder="Topics (e.g. IR Theories, RAG Models)"
            className="p-3 rounded-lg border dark:bg-gray-900 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 outline-none"
            value={formData.topics_learned}
            onChange={(e) => setFormData({ ...formData, topics_learned: e.target.value })}
          />
        </div>
        <textarea
          placeholder="Personal Notes or Key Takeaways (Optional)"
          className="p-3 rounded-lg border dark:bg-gray-900 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 outline-none h-24"
          value={formData.notes}
          onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-linear-to-r from-blue-600 to-indigo-600 text-white py-3 rounded-lg font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {loading ? 'Saving to Vault...' : "Log Today's Progress 🚀"}
        </button>
      </form>
    </div>
  );
}