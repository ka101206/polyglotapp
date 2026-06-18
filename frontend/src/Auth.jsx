import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { LogIn, UserPlus } from 'lucide-react';

export default function Auth({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const endpoint = isLogin ? '/auth/login' : '/auth/register';
    const apiUrl = '';

    try {
      const response = await fetch(`${apiUrl}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, is_admin: isAdmin }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed');
      }

      const gradients = [
        "from-blue-500 to-indigo-500",
        "from-purple-500 to-pink-500",
        "from-emerald-400 to-cyan-500",
        "from-orange-400 to-rose-500",
        "from-teal-400 to-blue-500",
        "from-rose-400 to-orange-500",
        "from-cyan-500 to-blue-500"
      ];
      data.gradientClass = gradients[Math.floor(Math.random() * gradients.length)];

      onLogin(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center p-4">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md w-full bg-slate-200 dark:bg-slate-800/50 backdrop-blur-xl border border-slate-300 dark:border-slate-700/50 p-8 rounded-3xl shadow-2xl"
      >
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-500/20 text-blue-400 mb-4">
            {isLogin ? <LogIn size={32} /> : <UserPlus size={32} />}
          </div>
          <h2 className="text-3xl font-bold text-black dark:text-white tracking-tight">
            {isLogin ? 'Welcome back' : 'Create account'}
          </h2>
          <p className="text-slate-600 dark:text-slate-400 mt-2">
            {isLogin ? 'Enter your details to access your dashboard' : 'Sign up to start mastering languages'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Username</label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-3 text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              placeholder="Enter your username"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-3 text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              placeholder="••••••••"
            />
          </div>

          {!isLogin && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="flex items-center space-x-3 mt-4">
              <input
                type="checkbox"
                id="isAdminCheckbox"
                checked={isAdmin}
                onChange={(e) => setIsAdmin(e.target.checked)}
                className="h-5 w-5 rounded border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50"
              />
              <label htmlFor="isAdminCheckbox" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Register as Admin (B2B Dashboard)
              </label>
            </motion.div>
          )}

          {error && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-red-400 text-sm text-center">
              {error}
            </motion.div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-400 hover:to-indigo-500 text-black dark:text-white font-semibold py-3 px-4 rounded-xl shadow-lg shadow-blue-500/30 transform transition-all hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Processing...' : (isLogin ? 'Sign In' : 'Sign Up')}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => {
              setIsLogin(!isLogin);
              setError('');
            }}
            className="text-slate-600 dark:text-slate-400 hover:text-black dark:text-white text-sm transition-colors"
          >
            {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
