import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, Settings, Clock, ChevronLeft, Plus, Search, CheckCircle, BarChart2, Trash2, BookOpen } from 'lucide-react';
import AnalyticsDashboard from './AnalyticsDashboard';

export default function AdminDashboard({ user, onBack }) {
  const [groups, setGroups] = useState([]);
  const [activeGroupId, setActiveGroupId] = useState(null);
  const [newGroupName, setNewGroupName] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showUserAnalytics, setShowUserAnalytics] = useState(false);
  const [showUserNotebook, setShowUserNotebook] = useState(false);
  const [userNotebook, setUserNotebook] = useState([]);
  
  const [newUsername, setNewUsername] = useState('');
  const [settingsForm, setSettingsForm] = useState({
    force_low_token_mode: false,
    forced_language: '',
    forced_difficulty: '',
    forced_reading_mode: ''
  });

  const apiUrl = '';

  const createGroup = async () => {
    if (!newGroupName.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/admin/groups`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newGroupName, admin_id: user.user_id })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setNewGroupName('');
      fetchMyGroups();
      setActiveGroupId(data.id);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const fetchMyGroups = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/admin/my-groups?admin_id=${user.user_id}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setGroups(data.groups || []);
      if (data.groups && data.groups.length > 0) {
        setActiveGroupId(prev => prev || data.groups[0].group.id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const deleteGroup = async (idToDelete) => {
    if (!window.confirm("Are you sure you want to delete this group? Users will not be deleted, but they will be removed from this group.")) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/admin/groups/${idToDelete}?admin_id=${user.user_id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete group');
      if (activeGroupId === idToDelete) setActiveGroupId(null);
      fetchMyGroups();
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchMyGroups();
    const interval = setInterval(fetchMyGroups, 5000);
    return () => clearInterval(interval);
  }, [user.user_id]);

  const addUserToGroup = async () => {
    if (!newUsername || !activeGroupId) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/admin/groups/${activeGroupId}/invite?admin_id=${user.user_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: newUsername.trim() })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setSuccess(data.message || 'Invite sent to user!');
      setTimeout(() => setSuccess(''), 3000);
      setNewUsername('');
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const loadNotebook = async (targetUserId) => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/notebook?user_id=${targetUserId}&requester_id=${user.user_id}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setUserNotebook(data);
      setShowUserNotebook(true);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const loadSessions = async (targetUserId) => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/admin/sessions/${targetUserId}?admin_id=${user.user_id}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setSessions(data);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const updateSettings = async () => {
    if (!selectedUser) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/admin/users/${selectedUser.id}/settings?admin_id=${user.user_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          force_low_token_mode: settingsForm.force_low_token_mode,
          forced_language: settingsForm.forced_language || null,
          forced_difficulty: settingsForm.forced_difficulty || null,
          forced_reading_mode: settingsForm.forced_reading_mode || null
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setSuccess('Settings updated successfully');
      setTimeout(() => setSuccess(''), 3000);
      fetchMyGroups();
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const openUserSettings = (u) => {
    setSelectedUser(u);
    setSettingsForm({
      force_low_token_mode: u.force_low_token_mode || false,
      forced_language: u.forced_language || '',
      forced_difficulty: u.forced_difficulty || '',
      forced_reading_mode: u.forced_reading_mode || ''
    });
    loadSessions(u.id);
  };

  const activeGroupData = groups.find(g => g.group.id === activeGroupId);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 p-6 font-sans">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-indigo-600">
            Admin Dashboard
          </h1>
          <button onClick={onBack} className="flex items-center text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 bg-slate-200 dark:bg-slate-800 px-4 py-2 rounded-full font-medium transition-colors">
            Close Dashboard
          </button>
        </div>

        {error && <div className="bg-red-100 text-red-600 p-3 rounded-lg">{error}</div>}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Left Column: Group Management */}
          <div className="space-y-6">
            <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
              <h2 className="text-xl font-semibold mb-4 flex items-center"><Users className="mr-2" /> Group Management</h2>
              
              <div className="space-y-4">
                {groups.length > 0 && (
                  <div className="space-y-2">
                    {groups.map((g) => (
                      <div 
                        key={g.group.id} 
                        onClick={() => setActiveGroupId(g.group.id)}
                        className={`p-4 rounded-lg border cursor-pointer flex items-center justify-between transition-colors ${activeGroupId === g.group.id ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-700' : 'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'}`}
                      >
                        <div>
                          <div className="text-lg font-bold text-blue-800 dark:text-blue-200">{g.group.name}</div>
                          <div className="text-xs text-slate-500">{g.users.length} users</div>
                        </div>
                        <button onClick={(e) => { e.stopPropagation(); deleteGroup(g.group.id); }} className="text-red-500 hover:text-red-700 p-2">
                          <Trash2 size={18} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
                  <label className="block text-sm mb-1 text-slate-500">Create New Group</label>
                  <div className="flex flex-col xl:flex-row gap-2">
                    <input 
                      type="text" value={newGroupName} onChange={e => setNewGroupName(e.target.value)}
                      placeholder="Group Name"
                      className="flex-1 min-w-0 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2"
                    />
                    <button onClick={createGroup} disabled={loading} className="xl:w-auto flex items-center justify-center bg-blue-500 hover:bg-blue-600 text-white p-2 rounded-lg transition-colors"><Plus size={20}/></button>
                  </div>
                </div>
              </div>
            </div>

            {activeGroupData && (
              <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                <h2 className="text-lg font-semibold mb-3">Invite User to {activeGroupData.group.name}</h2>
                <div className="flex flex-col xl:flex-row gap-2">
                  <input 
                    type="text" value={newUsername} onChange={e => setNewUsername(e.target.value)}
                    placeholder="Username"
                    className="flex-1 min-w-0 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2"
                  />
                  <button onClick={addUserToGroup} disabled={loading} className="xl:w-auto whitespace-nowrap flex-shrink-0 bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg transition-colors">Invite</button>
                </div>
                {success && success.includes('Invite') && <div className="text-green-500 text-sm mt-2">{success}</div>}
              </div>
            )}
          </div>

          {/* Middle Column: User List */}
          <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
            <h2 className="text-xl font-semibold mb-4">Users in Group</h2>
            {!activeGroupData ? (
              <div className="text-slate-400 text-sm italic">Select a group to see users.</div>
            ) : activeGroupData.users.length === 0 ? (
              <div className="text-slate-400 text-sm italic">No users in this group.</div>
            ) : (
              <div className="space-y-3">
                {activeGroupData.users.map(u => (
                  <div 
                    key={u.id} 
                    onClick={() => openUserSettings(u)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all ${selectedUser?.id === u.id ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700' : 'bg-slate-50 dark:bg-slate-900/50 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'}`}
                  >
                    <div className="font-semibold">{u.username} <span className="text-xs font-normal text-slate-500">(ID: {u.id})</span></div>
                    <div className="text-xs text-slate-500 mt-1">
                      Time Spoken: {Math.round(u.total_speaking_time / 60)} min
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right Column: User Settings & Sessions */}
          <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-y-auto max-h-[80vh]">
            <h2 className="text-xl font-semibold mb-4 flex items-center"><Settings className="mr-2" /> Settings & History</h2>
            {!selectedUser ? (
              <div className="text-slate-400 text-sm italic">Select a user to view their details.</div>
            ) : (
              <div className="space-y-6">
                
                {/* Overrides */}
                <div className="space-y-3">
                  <h3 className="font-medium border-b border-slate-200 dark:border-slate-700 pb-2">Forced Settings</h3>
                  
                  <label className="flex items-center space-x-3">
                    <input 
                      type="checkbox" 
                      checked={settingsForm.force_low_token_mode} 
                      onChange={e => setSettingsForm({...settingsForm, force_low_token_mode: e.target.checked})}
                      className="form-checkbox rounded text-blue-500"
                    />
                    <span className="text-sm">Force Low Token Mode</span>
                  </label>
                  
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Force Language</label>
                    <select 
                      value={settingsForm.forced_language} onChange={e => setSettingsForm({...settingsForm, forced_language: e.target.value})}
                      className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm"
                    >
                      <option value="">No Override</option>
                      <option value="Japanese">Japanese</option>
                      <option value="Korean">Korean</option>
                      <option value="Chinese">Chinese</option>
                      <option value="Spanish">Spanish</option>
                      <option value="French">French</option>
                      <option value="Italian">Italian</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Force Difficulty</label>
                    <select 
                      value={settingsForm.forced_difficulty} onChange={e => setSettingsForm({...settingsForm, forced_difficulty: e.target.value})}
                      className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm"
                    >
                      <option value="">No Override</option>
                      <option value="Beginner">Beginner</option>
                      <option value="Intermediate">Intermediate</option>
                      <option value="Advanced">Advanced</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Force Reading Mode</label>
                    <select 
                      value={settingsForm.forced_reading_mode} onChange={e => setSettingsForm({...settingsForm, forced_reading_mode: e.target.value})}
                      className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm"
                    >
                      <option value="">No Override</option>
                      <option value="なし">なし (None)</option>
                      <option value="ふりがな">ふりがな (Furigana)</option>
                      <option value="かなのみ">かなのみ (Kana Only)</option>
                    </select>
                    <p className="text-xs text-slate-400 mt-1">Applies only to Japanese currently.</p>
                  </div>
                  
                  <div className="flex flex-wrap items-center gap-3 mt-4">
                    <button onClick={updateSettings} disabled={loading} className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium">Save Settings</button>
                    <button onClick={() => setShowUserAnalytics(true)} className="bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center"><BarChart2 size={16} className="mr-2"/> View Analytics</button>
                    <button onClick={() => loadNotebook(selectedUser.id)} className="bg-indigo-500 hover:bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center"><BookOpen size={16} className="mr-2"/> View Notebook</button>
                    {success && <span className="text-green-500 flex items-center text-sm"><CheckCircle size={16} className="mr-1"/> Saved</span>}
                  </div>
                </div>

                {/* Sessions */}
                <div className="space-y-3 pt-4 border-t border-slate-200 dark:border-slate-700">
                  <h3 className="font-medium flex items-center"><Clock size={18} className="mr-2"/> Session History</h3>
                  {sessions.length === 0 ? (
                    <div className="text-slate-400 text-xs italic">No sessions recorded yet.</div>
                  ) : (
                    <div className="space-y-3">
                      {sessions.map(s => (
                        <div key={s.id} className="bg-slate-50 dark:bg-slate-900/50 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
                          <div className="text-xs text-slate-500 mb-2">{new Date(s.start_time).toLocaleString()}</div>
                          <div className="text-sm italic text-slate-700 dark:text-slate-300">
                            {s.summary || 'No summary generated (session may have been aborted or too short).'}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

              </div>
            )}
          </div>

        </div>
      </div>
      {showUserAnalytics && selectedUser && (
        <AnalyticsDashboard user={{ user_id: selectedUser.id }} onClose={() => setShowUserAnalytics(false)} />
      )}
      {showUserNotebook && selectedUser && (
        <div className="fixed inset-0 z-[60] bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-700">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-900/50">
              <h2 className="text-xl font-bold flex items-center gap-2"><BookOpen className="text-indigo-500"/> {selectedUser.username}&apos;s Notebook</h2>
              <button onClick={() => setShowUserNotebook(false)} className="text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 p-2 font-bold text-lg">&times;</button>
            </div>
            <div className="p-4 flex-1 overflow-y-auto space-y-4">
              {userNotebook.length === 0 ? (
                <div className="text-center text-slate-500 py-8">Notebook is empty.</div>
              ) : (
                userNotebook.map(item => {
                  return (
                    <div key={item.id} className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700">
                      <div className="font-bold text-blue-500 dark:text-blue-400 text-lg">{item.word}</div>
                      <div className="text-sm text-slate-700 dark:text-slate-300 mt-2 whitespace-pre-wrap">{item.definition}</div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
