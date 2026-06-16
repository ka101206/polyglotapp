import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { X, Clock, AlertTriangle, MessageCircle, Ear, Activity } from 'lucide-react';

export default function AnalyticsDashboard({ user, onClose }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const apiUrl = '';
        const res = await fetch(`${apiUrl}/api/analytics/${user.user_id}`);
        const data = await res.json();
        setStats(data);
      } catch (err) {
        console.error("Failed to load analytics:", err);
      }
    };
    fetchStats();
  }, [user.user_id]);

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-white dark:bg-slate-950/80 backdrop-blur-sm p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-4xl bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
      >
        <div className="px-8 py-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-200 dark:bg-slate-800/30">
          <div>
            <h2 className="text-2xl font-bold text-black dark:text-white tracking-tight">Analytics Overview</h2>
            <p className="text-slate-600 dark:text-slate-400 mt-1">Track your language learning progress</p>
          </div>
          <button 
            onClick={onClose}
            className="p-2 rounded-full hover:bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-black dark:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        <div className="p-8 overflow-y-auto">
          {!stats ? (
            <div className="flex justify-center py-20 text-slate-500 animate-pulse">Loading analytics...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              
              <div className="bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-300 dark:border-slate-700/50">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-xl bg-blue-500/20 text-blue-400 flex items-center justify-center">
                    <Clock size={24} />
                  </div>
                  <div>
                    <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">Total Speaking Time</p>
                    <p className="text-2xl font-bold text-black dark:text-white">{stats.total_speaking_time_minutes} min</p>
                  </div>
                </div>
              </div>

              <div className="bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-300 dark:border-slate-700/50">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-xl bg-red-500/20 text-red-400 flex items-center justify-center">
                    <AlertTriangle size={24} />
                  </div>
                  <div>
                    <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">Mistakes Corrected</p>
                    <p className="text-2xl font-bold text-black dark:text-white">{stats.total_mistakes}</p>
                  </div>
                </div>
              </div>

              <div className="bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-300 dark:border-slate-700/50">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center">
                    <Activity size={24} />
                  </div>
                  <div>
                    <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">Avg Fluency Score</p>
                    <p className="text-2xl font-bold text-black dark:text-white">{stats.avg_fluency_score}/100</p>
                  </div>
                </div>
              </div>

              <div className="bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-300 dark:border-slate-700/50">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                    <MessageCircle size={24} />
                  </div>
                  <div>
                    <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">Grammar Score</p>
                    <p className="text-2xl font-bold text-black dark:text-white">{stats.avg_grammar_score}/100</p>
                  </div>
                </div>
              </div>

              <div className="bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-300 dark:border-slate-700/50">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center">
                    <Ear size={24} />
                  </div>
                  <div>
                    <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">Listening Comprehension</p>
                    <p className="text-2xl font-bold text-black dark:text-white">{stats.avg_listening_score}/100</p>
                  </div>
                </div>
              </div>

            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
