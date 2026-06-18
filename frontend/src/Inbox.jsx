import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Bell, Check, X, Inbox as InboxIcon } from 'lucide-react';

export default function Inbox({ user, onClose }) {
  const [invites, setInvites] = useState([]);
  const [loading, setLoading] = useState(true);

  const apiUrl = '';

  useEffect(() => {
    fetchInvites();
  }, []);

  const fetchInvites = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/users/${user.user_id}/invites`);
      const data = await res.json();
      if (res.ok) {
        setInvites(data);
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleAction = async (inviteId, action) => {
    try {
      await fetch(`${apiUrl}/api/users/${user.user_id}/invites/${inviteId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      });
      fetchInvites();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-xl overflow-hidden text-slate-900 dark:text-white"
      >
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center bg-slate-100 dark:bg-slate-800">
          <h2 className="text-xl font-bold flex items-center"><InboxIcon className="mr-2"/> Inbox</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"><X /></button>
        </div>
        
        <div className="p-4 max-h-[60vh] overflow-y-auto">
          {loading ? (
            <p className="text-center text-slate-500 py-4">Loading invites...</p>
          ) : invites.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <Bell className="mx-auto h-12 w-12 text-slate-300 dark:text-slate-700 mb-3" />
              <p>No new invites.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {invites.map(invite => (
                <div key={invite.id} className="bg-slate-50 dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                  <p className="font-semibold text-slate-800 dark:text-slate-200">{invite.admin_name} invited you to join:</p>
                  <p className="text-lg text-blue-600 dark:text-blue-400 font-bold my-2">{invite.group_name}</p>
                  
                  <div className="flex gap-2 mt-4">
                    <button 
                      onClick={() => handleAction(invite.id, 'accept')}
                      className="flex-1 bg-blue-500 hover:bg-blue-600 text-white py-2 rounded-lg font-medium flex justify-center items-center transition-colors"
                    >
                      <Check size={18} className="mr-1" /> Accept
                    </button>
                    <button 
                      onClick={() => handleAction(invite.id, 'decline')}
                      className="flex-1 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-800 dark:text-slate-200 py-2 rounded-lg font-medium flex justify-center items-center transition-colors"
                    >
                      <X size={18} className="mr-1" /> Decline
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
