import React from 'react';
import { ChevronDown, Settings, BarChart2, LogOut, Trash2, User, Inbox as InboxIcon, Shield, BookOpen } from 'lucide-react';
import { useTranslation } from '../i18n';
import Credits from './Credits';

// Language-specific annotation labels emitted by the backend dictionary
// (see ANNOTATION_INSTRUCTIONS in ai_client.py + computed Japanese pitch):
// pitch accent, tone, stress, gender. Displayed above the reading in the notebook.
export const ANNOTATION_LABEL_KEYS = {
  pitch: 'pitchLabel',
  tone: 'toneLabel',
  stress: 'stressLabel',
  gender: 'genderLabel',
};

// Japanese pitch-accent type -> i18n key, so the type name shows in the user's
// interface language (a beginner may not read 頭高/平板/中高/尾高). Both the
// romaji tokens the backend emits and the legacy kanji forms are recognized.
const PITCH_TYPE_KEYS = {
  heiban: 'pitchHeiban', atamadaka: 'pitchAtamadaka', nakadaka: 'pitchNakadaka', odaka: 'pitchOdaka',
  '平板': 'pitchHeiban', '頭高': 'pitchAtamadaka', '中高': 'pitchNakadaka', '尾高': 'pitchOdaka',
};

// Render an annotation value for display. For Japanese pitch, localize the
// accent-type name while keeping the universal [n] drop-position number.
export const formatAnnotation = (label, value, t) => {
  if (!value) return value;
  if (label === 'pitch') {
    const m = value.match(/^(\S+)\s*(\[\d+\])?/);
    if (m && PITCH_TYPE_KEYS[m[1]]) {
      const name = t(PITCH_TYPE_KEYS[m[1]]);
      return m[2] ? `${name} ${m[2]}` : name;
    }
  }
  return value;
};

const isNA = (v) => !v || /^n\/?\s*a\.?$/i.test(v.trim());

export const parseDefinition = (text) => {
  const empty = { definition: '', reading: null, annotation: null, annotationLabel: null };
  if (!text) return empty;

  let reading = null;
  let annotation = null;
  let annotationLabel = null;
  const rest = [];

  for (const raw of text.replace(/\r/g, '').split('\n')) {
    const line = raw.trim();
    if (!line) continue;
    // Only leading lines (before any definition text) are treated as metadata.
    if (rest.length === 0) {
      const rd = line.match(/^Reading:\s*(.+)$/i);
      if (rd && reading === null) {
        reading = isNA(rd[1]) ? null : rd[1].trim();
        continue;
      }
      const meta = line.match(/^([A-Za-z]+):\s*(.+)$/);
      if (meta && annotation === null && ANNOTATION_LABEL_KEYS[meta[1].toLowerCase()]) {
        if (!isNA(meta[2])) {
          annotationLabel = meta[1].toLowerCase();
          annotation = meta[2].trim();
        }
        continue;
      }
    }
    rest.push(line);
  }

  let definition = rest.join('\n').trim();

  // Backward compatibility: older entries stored the reading inline
  // ("definition. Reading: xxx") rather than on a leading line.
  if (reading === null) {
    const parts = text.split(/Reading:\s*/i);
    if (parts.length > 1) {
      if (!parts[0].trim()) {
        const sub = parts[1].split('\n');
        reading = sub[0].trim() || null;
        definition = sub.slice(1).join('\n').trim();
      } else {
        definition = parts[0].trim().replace(/\.$/, '');
        reading = parts[1].trim() || null;
      }
    }
  }

  if (!definition) definition = text.trim();
  return { definition, reading, annotation, annotationLabel };
};

export const SCENARIOS = [
  { id: 'Restaurant', nameKey: 'scenarioRestaurant', descKey: 'scenarioRestaurantDesc', icon: '🍽️' },
  { id: 'Classroom', nameKey: 'scenarioClassroom', descKey: 'scenarioClassroomDesc', icon: '🏫' },
  { id: 'Shopping', nameKey: 'scenarioShopping', descKey: 'scenarioShoppingDesc', icon: '🛍️' },
  { id: 'Directions', nameKey: 'scenarioDirections', descKey: 'scenarioDirectionsDesc', icon: '🗺️' },
  { id: 'Convenience Store', nameKey: 'scenarioConvenience', descKey: 'scenarioConvenienceDesc', icon: '🏪' }
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
  const { t } = useTranslation();
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
            <p className="text-[10px] text-slate-600 dark:text-slate-400">{user.is_admin ? t('admin') : t('polyglotStudent')}</p>
          </div>
        </div>
        <div className="relative shrink-0 flex items-center gap-1">
          {user.is_admin && (
            <button 
              onClick={() => onAdminClick?.()}
              title={t('adminDashboard')}
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
                onClick={() => { setShowInbox(true); setShowDropdown(false); }}
                className="w-full px-4 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-700 hover:text-black dark:hover:text-white flex items-center gap-2 transition-colors"
              >
                <InboxIcon size={16} /> {t('inbox')}
              </button>
              <button
                onClick={() => { setShowSettings(true); setShowDropdown(false); }}
                className="w-full px-4 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-700 hover:text-black dark:hover:text-white flex items-center gap-2 transition-colors"
              >
                <Settings size={16} /> {t('appSettings')}
              </button>
              <button
                onClick={() => { setShowAnalytics(true); setShowDropdown(false); }}
                className="w-full px-4 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-700 hover:text-black dark:hover:text-white flex items-center gap-2 transition-colors"
              >
                <BarChart2 size={16} /> {t('analytics')}
              </button>
              <div className="h-px bg-slate-300 dark:bg-slate-700 my-1"></div>
              <button
                onClick={onLogout}
                className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 transition-colors flex items-center gap-2"
              >
                <LogOut size={16} /> {t('signOut')}
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
          {t('notebook')}
        </button>
        <button
          onClick={() => setSidebarTab('scenarios')}
          className={`flex-1 py-2 text-xs font-bold uppercase tracking-wider rounded-lg transition-colors ${
            sidebarTab === 'scenarios' ? 'bg-slate-200 dark:bg-slate-800 text-black dark:text-white shadow-sm border border-slate-300 dark:border-slate-700' : 'text-slate-500 hover:text-slate-700 dark:text-slate-300 dark:hover:text-slate-100 dark:hover:bg-slate-800/50'
          }`}
        >
          {t('scenarios')}
        </button>
      </div>

      {/* Sidebar Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {sidebarTab === 'notebook' ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between px-2">
              <div className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">{t('savedVocabulary')}</div>
            </div>

            <button
              onClick={() => setShowSRSReview(true)}
              className="w-full py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 dark:bg-indigo-900/20 dark:hover:bg-indigo-900/40 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800/50 rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              <BookOpen size={16} /> {t('reviewDueItems')}
            </button>

            {notebook.map((item) => {
              const { definition, reading, annotation, annotationLabel } = parseDefinition(item.definition);
              return (
                <div key={item.id} className="p-4 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-300 dark:border-slate-700 relative group shadow-sm">
                  <button onClick={() => deleteFromNotebook(item.id)} className="absolute top-3 right-3 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <div className="font-bold text-blue-300 text-lg">{item.word}</div>
                  {annotation && (
                    <div className="mt-0.5 inline-flex items-center gap-1 text-xs font-semibold text-amber-600 dark:text-amber-400">
                      <span className="uppercase tracking-wide text-[9px] text-amber-500/70">{t(ANNOTATION_LABEL_KEYS[annotationLabel] || 'annotation')}</span>
                      <span>{formatAnnotation(annotationLabel, annotation, t)}</span>
                    </div>
                  )}
                  {reading && <div className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">{reading}</div>}
                  <div className="text-sm text-slate-700 dark:text-slate-300 mt-2 leading-relaxed">{definition}</div>
                </div>
              );
            })}
            {notebook.length === 0 && (
              <div className="text-slate-500 text-sm text-center py-8">{t('notebookEmpty')}</div>
            )}

            <Credits />
          </div>
        ) : (
          <div className="space-y-3">
            <div className="text-xs font-semibold text-slate-600 dark:text-slate-400 px-2 mb-1 uppercase tracking-wide">{t('scenariosHeader')}</div>
            {SCENARIOS.map((s) => (
              <button
                key={s.id}
                onClick={() => {
                  const lastMsg = messages[messages.length - 1];
                  if (lastMsg && lastMsg.type === 'scenario' && lastMsg.status === 'active') {
                    alert(t('finishScenarioAlert'));
                    return;
                  }
                  triggerScenario(s.id);
                }}
                className="w-full text-left p-4 bg-slate-200 dark:bg-slate-800/60 hover:bg-slate-300 dark:hover:bg-slate-700/80 border border-slate-300 dark:border-slate-700/50 hover:border-slate-400 dark:hover:border-slate-600 rounded-xl transition-all shadow-sm group relative overflow-hidden"
              >
                <div className="flex items-center gap-3">
                  <div className="text-2xl group-hover:scale-110 transition-transform">{s.icon}</div>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-slate-800 dark:text-slate-200 group-hover:text-blue-300 transition-colors text-sm truncate">{t(s.nameKey)}</div>
                  </div>
                </div>
                <div className="grid grid-rows-[0fr] group-hover:grid-rows-[1fr] transition-[grid-template-rows] duration-300">
                  <div className="overflow-hidden">
                    <div className="text-xs text-slate-600 dark:text-slate-400 mt-2 leading-relaxed">{t(s.descKey)}</div>
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
