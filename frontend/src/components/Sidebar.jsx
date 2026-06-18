import React from 'react';
import { ChevronDown, Settings, BarChart2, LogOut, Trash2, User, Inbox as InboxIcon, Shield, BookOpen } from 'lucide-react';

export const parseDefinition = (text) => {
  if (!text) return { definition: "", reading: null };
  // Check if it starts with "Reading:"
  const match = text.match(/^Reading:\s*([^\n]+)\n([\s\S]+)$/i);
  if (match) {
    return {
      definition: match[2].trim(),
      reading: match[1].trim()
    };
  }
  const parts = text.split(/Reading:\s*/i);
  if (parts.length > 1) {
    if (!parts[0].trim()) {
      const subparts = parts[1].split('\n');
      const reading = subparts[0].trim();
      const definition = subparts.slice(1).join('\n').trim();
      return { definition, reading };
    }
    return {
      definition: parts[0].trim().replace(/\.$/, ''),
      reading: parts[1].trim()
    };
  }
  return { definition: text, reading: null };
};

export const SCENARIOS = [
  { id: 'Restaurant', name: 'Ordering at a Restaurant', icon: '🍽️', description: 'Order a meal and pay the bill.' },
  { id: 'Classroom', name: 'New Class Introduction', icon: '🏫', description: 'Introduce yourself to a new classmate.' },
  { id: 'Shopping', name: 'Buying Clothes', icon: '🛍️', description: 'Ask for a different size and purchase.' },
  { id: 'Directions', name: 'Asking for Directions', icon: '🗺️', description: 'Ask how to get to the train station.' },
  { id: 'Convenience Store', name: 'Convenience Store', icon: '🏪', description: 'Buy a drink and ask for a bag.' }
];

export default function Sidebar({
  user,
  onLogout,
  showDropdown,
  setShowDropdown,
  setShowSettings,
  setShowAnalytics,
  setShowInbox,
  sidebarTab,
  setSidebarTab,
  notebook,
  deleteFromNotebook,
  messages,
  triggerScenario,
  onAdminClick,
  setShowSRSReview
}) {
  return (
    <div className="w-72 bg-white dark:bg-slate-950 border-l border-slate-200 dark:border-slate-800 flex flex-col z-20">
      {/* User Profile */}
      <div className="p-6 border-b border-slate-200 dark:border-slate-800 shrink-0 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-full bg-gradient-to-tr ${user.gradientClass || 'from-blue-500 to-indigo-500'} flex items-center justify-center text-black dark:text-white shadow-lg shrink-0 overflow-hidden`}>
            <User className="w-6 h-6 mt-1.5 opacity-90" />
          </div>
          <div className="min-w-0">
            <h2 className="font-semibold truncate">{user.nickname || user.username}</h2>
            <p className="text-[10px] text-slate-600 dark:text-slate-400">Polyglot Student</p>
          </div>
        </div>
        <div className="relative shrink-0 flex items-center gap-1">
          {user.is_admin && (
            <button 
              onClick={() => onAdminClick?.()}
              title="Admin Dashboard"
              className="p-2 text-indigo-500 hover:text-indigo-600 dark:hover:text-indigo-400 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
            >
              <Shield className="w-5 h-5" />
            </button>
          )}
          <button onClick={() => setShowDropdown(!showDropdown)} className="p-2 text-slate-600 dark:text-slate-400 hover:text-black dark:hover:text-white rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors">
            <ChevronDown className={`w-5 h-5 transition-transform ${showDropdown ? 'rotate-180' : ''}`} />
          </button>
          {showDropdown && (
            <div className="absolute right-0 top-full mt-2 w-48 bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl shadow-xl overflow-hidden py-1 z-50">
              <button 
                onClick={() => { setShowSettings(true); setShowDropdown(false); }}
                className="w-full px-4 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-700 hover:text-black dark:hover:text-white flex items-center gap-2 transition-colors"
              >
                <Settings size={16} /> App Settings
              </button>
              <button 
                onClick={() => { setShowAnalytics(true); setShowDropdown(false); }}
                className="w-full px-4 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-700 hover:text-black dark:hover:text-white flex items-center gap-2 transition-colors"
              >
                <BarChart2 size={16} /> Analytics
              </button>
              <div className="h-px bg-slate-300 dark:bg-slate-700 my-1"></div>
              <button 
                onClick={onLogout}
                className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 transition-colors flex items-center gap-2"
              >
                <LogOut size={16} /> Sign Out
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Sidebar Tabs */}
      <div className="flex p-2 shrink-0 border-b border-slate-200 dark:border-slate-800/50">
        <button 
          onClick={() => setSidebarTab('notebook')}
          className={`flex-1 py-2 text-xs font-bold uppercase tracking-wider rounded-lg transition-colors ${
            sidebarTab === 'notebook' ? 'bg-slate-200 dark:bg-slate-800 text-black dark:text-white shadow-sm border border-slate-300 dark:border-slate-700' : 'text-slate-500 hover:text-slate-700 dark:text-slate-300 dark:hover:text-slate-100 dark:hover:bg-slate-800/50'
          }`}
        >
          Notebook
        </button>
        <button 
          onClick={() => setSidebarTab('scenarios')}
          className={`flex-1 py-2 text-xs font-bold uppercase tracking-wider rounded-lg transition-colors ${
            sidebarTab === 'scenarios' ? 'bg-slate-200 dark:bg-slate-800 text-black dark:text-white shadow-sm border border-slate-300 dark:border-slate-700' : 'text-slate-500 hover:text-slate-700 dark:text-slate-300 dark:hover:text-slate-100 dark:hover:bg-slate-800/50'
          }`}
        >
          Scenarios
        </button>
      </div>

      {/* Sidebar Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {sidebarTab === 'notebook' ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between px-2">
              <div className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">Saved Vocabulary</div>
            </div>
            
            <button 
              onClick={() => setShowSRSReview(true)}
              className="w-full py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 dark:bg-indigo-900/20 dark:hover:bg-indigo-900/40 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800/50 rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              <BookOpen size={16} /> Review Due Items
            </button>

            {notebook.map((item) => {
              const { definition, reading } = parseDefinition(item.definition);
              return (
                <div key={item.id} className="p-4 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-300 dark:border-slate-700 relative group shadow-sm">
                  <button onClick={() => deleteFromNotebook(item.id)} className="absolute top-3 right-3 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <div className="font-bold text-blue-300 text-lg">{item.word}</div>
                  {reading && <div className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">{reading}</div>}
                  <div className="text-sm text-slate-700 dark:text-slate-300 mt-2 leading-relaxed">{definition}</div>
                </div>
              );
            })}
            {notebook.length === 0 && (
              <div className="text-slate-500 text-sm text-center py-8">Notebook is empty. Highlight words in the chat to save them!</div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <div className="text-xs font-semibold text-slate-600 dark:text-slate-400 px-2 mb-1 uppercase tracking-wide">Scenarios</div>
            {SCENARIOS.map((s) => (
              <button 
                key={s.id}
                onClick={() => {
                  const lastMsg = messages[messages.length - 1];
                  if (lastMsg && lastMsg.type === 'scenario' && lastMsg.status === 'active') {
                    alert("Please finish the current scenario before starting a new one!");
                    return;
                  }
                  triggerScenario(s.id);
                }}
                className="w-full text-left p-4 bg-slate-200 dark:bg-slate-800/60 hover:bg-slate-300 dark:hover:bg-slate-700/80 border border-slate-300 dark:border-slate-700/50 hover:border-slate-400 dark:hover:border-slate-600 rounded-xl transition-all shadow-sm group relative overflow-hidden"
              >
                <div className="flex items-center gap-3">
                  <div className="text-2xl group-hover:scale-110 transition-transform">{s.icon}</div>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-slate-800 dark:text-slate-200 group-hover:text-blue-300 transition-colors text-sm truncate">{s.name}</div>
                  </div>
                </div>
                <div className="grid grid-rows-[0fr] group-hover:grid-rows-[1fr] transition-[grid-template-rows] duration-300">
                  <div className="overflow-hidden">
                    <div className="text-xs text-slate-600 dark:text-slate-400 mt-2 leading-relaxed">{s.description}</div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
