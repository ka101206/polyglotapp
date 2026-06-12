import React from 'react';
import { motion } from 'framer-motion';
import { Globe } from 'lucide-react';

const LANGUAGES = [
  { value: 'Japanese', label: '日本語', sub: 'Japanese' },
  { value: 'Korean', label: '한국어', sub: 'Korean' },
  { value: 'Chinese', label: '中文', sub: 'Chinese' },
  { value: 'Spanish', label: 'Español', sub: 'Spanish' },
  { value: 'French', label: 'Français', sub: 'French' },
  { value: 'Italian', label: 'Italiano', sub: 'Italian' },
];

export default function LanguageSelect({ user, onSelect }) {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-lg w-full bg-slate-200 dark:bg-slate-800/50 backdrop-blur-xl border border-slate-300 dark:border-slate-700/50 p-8 rounded-3xl shadow-2xl"
      >
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-500/20 text-blue-400 mb-4">
            <Globe size={32} />
          </div>
          <h2 className="text-3xl font-bold text-black dark:text-white tracking-tight">
            Welcome, {user.nickname || user.username}
          </h2>
          <p className="text-slate-600 dark:text-slate-400 mt-2">What would you like to practice today?</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {LANGUAGES.map((lang, i) => (
            <motion.button
              key={lang.value}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => onSelect(lang.value)}
              className="group flex flex-col items-center gap-2 py-5 px-4 rounded-2xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 text-slate-700 dark:text-slate-300 hover:border-blue-500 hover:bg-blue-500/10 hover:text-blue-300 transition-all duration-200 hover:shadow-lg hover:shadow-blue-500/5"
            >
              <span className="text-xl font-bold">{lang.label}</span>
              <span className="text-xs text-slate-500 group-hover:text-blue-400/70 transition-colors">{lang.sub}</span>
            </motion.button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
