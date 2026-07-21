import React from 'react';
import { useTranslation } from '../i18n';

// TTS model attribution. Each entry follows the crediting requirements of the
// respective project/voice provider:
//  - Style-Bert-VITS2 (AGPL-3.0). The female JP voice is the Koharune Ami model,
//    derived from Amitaro's voice materials, whose terms REQUIRE a visible
//    credit with the studio name and a link to https://amitaro.net/. The male
//    JP voice (JVNV) is CC BY-SA 4.0 and must credit the JVNV corpus.
//  - CosyVoice 2 (Apache-2.0, FunAudioLLM).
//  - MeloTTS (MIT, MyShell.ai).
//  - Chatterbox (MIT, Resemble AI). Its output is watermarked (Perth); we
//    disclose that here.
//  - Microsoft Edge TTS for English and as the universal fallback.
const CREDITS = [
  {
    langs: 'Japanese (female)',
    parts: [
      { text: 'Style-Bert-VITS2', href: 'https://github.com/litagin02/Style-Bert-VITS2' },
      { text: ' — 小春音アミ / ' },
      { text: 'あみたろの声素材工房', href: 'https://amitaro.net/' },
      { text: ' (https://amitaro.net/)' },
    ],
  },
  {
    langs: 'Japanese (male)',
    parts: [
      { text: 'Style-Bert-VITS2', href: 'https://github.com/litagin02/Style-Bert-VITS2' },
      { text: ' — JVNV corpus (CC BY-SA 4.0)' },
    ],
  },
  {
    langs: 'Chinese · Korean',
    parts: [
      { text: 'CosyVoice 2', href: 'https://github.com/FunAudioLLM/CosyVoice' },
      { text: ' by FunAudioLLM (Apache-2.0)' },
    ],
  },
  {
    langs: 'Spanish · French',
    parts: [
      { text: 'MeloTTS', href: 'https://github.com/myshell-ai/MeloTTS' },
      { text: ' by MyShell.ai (MIT)' },
    ],
  },
  {
    langs: 'Italian',
    parts: [
      { text: 'Chatterbox', href: 'https://github.com/resemble-ai/chatterbox' },
      { text: ' by Resemble AI (MIT) — output is Perth-watermarked' },
    ],
  },
  {
    langs: 'English · fallback',
    parts: [
      { text: 'Microsoft Edge TTS', href: 'https://github.com/rany2/edge-tts' },
    ],
  },
];

export default function Credits() {
  const { t } = useTranslation();
  return (
    <div className="pt-4 mt-4 border-t border-slate-200 dark:border-slate-800 px-2 space-y-2">
      <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">
        {t('voicesPoweredBy')}
      </div>
      <ul className="space-y-1.5">
        {CREDITS.map((c) => (
          <li key={c.langs} className="text-[10px] text-slate-400 dark:text-slate-500 leading-relaxed">
            <span className="font-medium text-slate-500 dark:text-slate-400">{c.langs}:</span>{' '}
            {c.parts.map((p, i) =>
              p.href ? (
                <a
                  key={i}
                  href={p.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline decoration-dotted hover:text-blue-500 transition-colors"
                >
                  {p.text}
                </a>
              ) : (
                <span key={i}>{p.text}</span>
              )
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
