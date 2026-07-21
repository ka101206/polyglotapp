import React, { useState, useEffect } from 'react';
import { BookOpen, X, Check, ArrowRight } from 'lucide-react';
import { parseDefinition, ANNOTATION_LABEL_KEYS, formatAnnotation } from './Sidebar';
import { useTranslation } from '../i18n';

export default function SRSReviewModal({ user, onClose }) {
  const { t } = useTranslation();
  const [reviewItems, setReviewItems] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReviews = async () => {
      try {
        const res = await fetch(`/api/notebook/review?user_id=${user.user_id}`);
        const data = await res.json();
        setReviewItems(data);
      } catch (err) {
        console.error("Error fetching review items", err);
      } finally {
        setLoading(false);
      }
    };
    fetchReviews();
  }, [user.user_id]);

  const submitReview = async (quality) => {
    const item = reviewItems[currentIndex];
    try {
      await fetch(`/api/notebook/review/${item.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quality })
      });
    } catch (err) {
      console.error("Error submitting review", err);
    }
    
    if (currentIndex < reviewItems.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setShowAnswer(false);
    } else {
      setReviewItems([]);
    }
  };

  if (loading) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
          <h2 className="text-xl font-bold text-black dark:text-white flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-indigo-400" />
            {t('srsTitle')}
          </h2>
          <button onClick={onClose} className="text-slate-600 dark:text-slate-400 hover:text-black dark:text-white transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>
        
        <div className="p-8 flex flex-col items-center">
          {reviewItems.length === 0 ? (
            <div className="text-center space-y-4 py-8">
              <div className="w-16 h-16 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center mx-auto">
                <Check className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-bold">{t('allCaughtUp')}</h3>
              <p className="text-slate-500 dark:text-slate-400">{t('noMoreReviews')}</p>
              <button
                onClick={onClose}
                className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg mt-4 transition-colors"
              >
                {t('returnToChat')}
              </button>
            </div>
          ) : (
            <div className="w-full max-w-sm flex flex-col items-center">
              <div className="text-sm font-medium text-slate-500 mb-6 uppercase tracking-wider">
                {t('reviewingProgress', { current: currentIndex + 1, total: reviewItems.length })}
              </div>
              
              <div className="w-full bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-8 rounded-2xl shadow-sm text-center mb-8">
                <div className="text-3xl font-bold text-indigo-500 dark:text-indigo-400 mb-4">{reviewItems[currentIndex].word}</div>
                
                {showAnswer ? (
                  <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <div className="h-px w-full bg-slate-200 dark:bg-slate-800 my-4"></div>
                    {(() => {
                      const { definition, reading, annotation, annotationLabel } = parseDefinition(reviewItems[currentIndex].definition);
                      return (
                        <>
                          {annotation && (
                            <div className="mb-2 inline-flex items-center gap-1.5 text-xs font-semibold text-amber-600 dark:text-amber-400">
                              <span className="uppercase tracking-wide text-[9px] text-amber-500/70">{t(ANNOTATION_LABEL_KEYS[annotationLabel] || 'annotation')}</span>
                              <span>{formatAnnotation(annotationLabel, annotation, t)}</span>
                            </div>
                          )}
                          <div className="text-lg text-slate-700 dark:text-slate-300">{definition}</div>
                          {reading && (
                            <div className="text-sm text-slate-500 mt-2 font-medium">{reading}</div>
                          )}
                        </>
                      );
                    })()}
                  </div>
                ) : (
                  <button 
                    onClick={() => setShowAnswer(true)}
                    className="w-full py-3 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300 font-medium rounded-xl border border-indigo-200 dark:border-indigo-800/50 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition-colors"
                  >
                    {t('showAnswer')}
                  </button>
                )}
              </div>
              
              {showAnswer && (
                <div className="w-full space-y-3 animate-in fade-in slide-in-from-bottom-4 duration-500">
                  <p className="text-sm text-slate-500 font-medium text-center mb-2">{t('howWellKnow')}</p>
                  <div className="flex gap-2">
                    <button onClick={() => submitReview(1)} className="flex-1 py-3 text-sm font-medium bg-red-100 hover:bg-red-200 text-red-700 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50 rounded-xl transition-colors">
                      {t('ratingForgot')}
                    </button>
                    <button onClick={() => submitReview(3)} className="flex-1 py-3 text-sm font-medium bg-amber-100 hover:bg-amber-200 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 dark:hover:bg-amber-900/50 rounded-xl transition-colors">
                      {t('ratingHard')}
                    </button>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => submitReview(4)} className="flex-1 py-3 text-sm font-medium bg-green-100 hover:bg-green-200 text-green-700 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-900/50 rounded-xl transition-colors">
                      {t('ratingGood')}
                    </button>
                    <button onClick={() => submitReview(5)} className="flex-1 py-3 text-sm font-medium bg-blue-100 hover:bg-blue-200 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 dark:hover:bg-blue-900/50 rounded-xl transition-colors">
                      {t('ratingEasy')}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
