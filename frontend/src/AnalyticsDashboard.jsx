import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { X, Clock, AlertTriangle, MessageCircle, Ear, Activity, Volume2, Wind, Target, TrendingUp, TrendingDown } from 'lucide-react';

function TrendBadge({ trend }) {
  if (trend === null || trend === undefined) return null;
  const isPositive = trend > 0;
  const isNeutral = trend === 0;
  if (isNeutral) return <span className="text-xs text-slate-400 ml-2">→ No change</span>;
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-medium ml-2 px-1.5 py-0.5 rounded-full ${isPositive ? 'bg-green-500/15 text-green-400' : 'bg-red-500/15 text-red-400'}`}>
      {isPositive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
      {isPositive ? '+' : ''}{trend}
    </span>
  );
}

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

              <div className="bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-300 dark:border-slate-700/50 md:col-span-2 lg:col-span-1">
                <div className="flex items-center gap-4 mb-3">
                  <div className="w-12 h-12 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center">
                    <Activity size={24} />
                  </div>
                  <div>
                    <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">Fluency</p>
                    <p className="text-2xl font-bold text-black dark:text-white">
                      {stats.avg_fluency_score}/100
                      <TrendBadge trend={stats.fluency_trend} />
                    </p>
                  </div>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Avg of Confidence {stats.fluency_sub?.confidence ?? 0} · Flow {stats.fluency_sub?.flow ?? 0} · Grammar {stats.fluency_sub?.grammar ?? 0}
                </p>
              </div>

              <div className="bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-300 dark:border-slate-700/50">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                    <MessageCircle size={24} />
                  </div>
                  <div>
                    <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">Grammar Score</p>
                    <p className="text-2xl font-bold text-black dark:text-white">
                      {stats.avg_grammar_score}/100
                      <TrendBadge trend={stats.grammar_trend} />
                    </p>
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

              <div className="bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-300 dark:border-slate-700/50">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-xl bg-pink-500/20 text-pink-400 flex items-center justify-center">
                    <Volume2 size={24} />
                  </div>
                  <div>
                    <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">Confidence <span className="text-[10px] opacity-60">(sub of Fluency)</span></p>
                    <p className="text-2xl font-bold text-black dark:text-white">{stats.avg_confidence_score}/100</p>
                  </div>
                </div>
              </div>

              <div className="bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-300 dark:border-slate-700/50">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center">
                    <Wind size={24} />
                  </div>
                  <div>
                    <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">Flow <span className="text-[10px] opacity-60">(sub of Fluency)</span></p>
                    <p className="text-2xl font-bold text-black dark:text-white">{stats.avg_flow_score}/100</p>
                  </div>
                </div>
              </div>

            </div>
          )}

          {stats && stats.weak_points && (
            <div className="mt-8">
              <div className="flex items-center gap-2 mb-4 text-slate-700 dark:text-slate-300">
                <Target size={18} />
                <h3 className="text-lg font-bold">Weak Points to Work On</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  { key: 'grammar', label: 'Grammar', color: 'emerald' },
                  { key: 'flow', label: 'Flow (choppy words)', color: 'cyan' },
                  { key: 'confidence', label: 'Confidence (weak sounds)', color: 'pink' },
                ].map(({ key, label }) => {
                  const items = stats.weak_points[key] || [];
                  return (
                    <div key={key} className="bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-5 border border-slate-300 dark:border-slate-700/50">
                      <p className="text-slate-600 dark:text-slate-400 text-sm font-semibold mb-3">{label}</p>
                      {items.length === 0 ? (
                        <p className="text-slate-400 dark:text-slate-500 text-sm">No data yet</p>
                      ) : (
                        <ul className="space-y-2">
                          {items.map((it, i) => (
                            <li key={i} className="flex items-center justify-between text-sm">
                              <span className="text-black dark:text-white font-medium truncate mr-2">{it.key}</span>
                              <span className="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">×{it.count}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
