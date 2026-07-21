import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { X, Clock, AlertTriangle, MessageCircle, Ear, Activity, Volume2, Wind, Target, TrendingUp, TrendingDown } from 'lucide-react';
import { useTranslation } from './i18n';

function TrendBadge({ trend }) {
  const { t } = useTranslation();
  if (trend === null || trend === undefined) return null;
  const isPositive = trend > 0;
  const isNeutral = trend === 0;
  if (isNeutral) return <span className="text-xs text-slate-400 ml-2">→ {t('noChange')}</span>;
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-medium ml-2 px-1.5 py-0.5 rounded-full ${isPositive ? 'bg-green-500/15 text-green-400' : 'bg-red-500/15 text-red-400'}`}>
      {isPositive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
      {isPositive ? '+' : ''}{trend}
    </span>
  );
}

function SubStat({ label, value, Icon, iconClass, trend }) {
  const v = value ?? 0;
  const barColor = v >= 80 ? 'bg-green-500' : v >= 55 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="bg-white/60 dark:bg-slate-900/40 rounded-xl p-4 border border-slate-300/60 dark:border-slate-700/40">
      <div className="flex items-center gap-2 mb-2 text-slate-600 dark:text-slate-300">
        <Icon size={16} className={iconClass} />
        <span className="text-sm font-medium">{label}</span>
        {trend !== undefined && <TrendBadge trend={trend} />}
      </div>
      <div className="flex items-baseline gap-1 mb-2">
        <span className="text-2xl font-bold text-black dark:text-white">{v}</span>
        <span className="text-xs text-slate-500">/100</span>
      </div>
      <div className="h-2 rounded-full bg-slate-300/50 dark:bg-slate-700/50 overflow-hidden">
        <div className={`h-full ${barColor}`} style={{ width: `${Math.max(0, Math.min(100, v))}%` }}></div>
      </div>
    </div>
  );
}

export default function AnalyticsDashboard({ user, onClose }) {
  const { t } = useTranslation();
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
            <h2 className="text-2xl font-bold text-black dark:text-white tracking-tight">{t('analyticsOverview')}</h2>
            <p className="text-slate-600 dark:text-slate-400 mt-1">{t('analyticsSubtitle')}</p>
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
            <div className="flex justify-center py-20 text-slate-500 animate-pulse">{t('loadingAnalytics')}</div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

                <div className="bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-300 dark:border-slate-700/50">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-blue-500/20 text-blue-400 flex items-center justify-center">
                      <Clock size={24} />
                    </div>
                    <div>
                      <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">{t('totalSpeakingTime')}</p>
                      <p className="text-2xl font-bold text-black dark:text-white">{stats.total_speaking_time_minutes} {t('minutesShort')}</p>
                    </div>
                  </div>
                </div>

                <div className="bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-300 dark:border-slate-700/50">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-red-500/20 text-red-400 flex items-center justify-center">
                      <AlertTriangle size={24} />
                    </div>
                    <div>
                      <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">{t('mistakesCorrected')}</p>
                      <p className="text-2xl font-bold text-black dark:text-white">{stats.total_mistakes}</p>
                    </div>
                  </div>
                </div>

                <div className="bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-300 dark:border-slate-700/50">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center">
                      <Ear size={24} />
                    </div>
                    <div>
                      <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">{t('listeningComprehension')}</p>
                      <p className="text-2xl font-bold text-black dark:text-white">{stats.avg_listening_score}/100</p>
                    </div>
                  </div>
                </div>

              </div>

              {/* Fluency (parent) with its three sub-stats nested underneath */}
              <div className="mt-6 bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-300 dark:border-slate-700/50">
                <div className="flex items-center justify-between flex-wrap gap-2 mb-5">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center">
                      <Activity size={24} />
                    </div>
                    <div>
                      <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">{t('fluency')}</p>
                      <p className="text-3xl font-bold text-black dark:text-white">
                        {stats.avg_fluency_score}<span className="text-lg text-slate-500">/100</span>
                        <TrendBadge trend={stats.fluency_trend} />
                      </p>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">{t('fluencySubtitle')}</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <SubStat label={t('confidence')} value={stats.fluency_sub?.confidence} Icon={Volume2} iconClass="text-pink-400" />
                  <SubStat label={t('flow')} value={stats.fluency_sub?.flow} Icon={Wind} iconClass="text-cyan-400" />
                  <SubStat label={t('grammarStat')} value={stats.fluency_sub?.grammar} Icon={MessageCircle} iconClass="text-emerald-400" trend={stats.grammar_trend} />
                </div>
              </div>
            </>
          )}

          {stats && stats.weak_points && (
            <div className="mt-8">
              <div className="flex items-center gap-2 mb-4 text-slate-700 dark:text-slate-300">
                <Target size={18} />
                <h3 className="text-lg font-bold">{t('weakPointsTitle')}</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  { key: 'grammar', label: t('grammarStat'), color: 'emerald' },
                  { key: 'flow', label: t('weakFlowLabel'), color: 'cyan' },
                  { key: 'confidence', label: t('weakConfidenceLabel'), color: 'pink' },
                ].map(({ key, label }) => {
                  const items = stats.weak_points[key] || [];
                  return (
                    <div key={key} className="bg-slate-200 dark:bg-slate-800/50 rounded-2xl p-5 border border-slate-300 dark:border-slate-700/50">
                      <p className="text-slate-600 dark:text-slate-400 text-sm font-semibold mb-3">{label}</p>
                      {items.length === 0 ? (
                        <p className="text-slate-400 dark:text-slate-500 text-sm">{t('noDataYet')}</p>
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
