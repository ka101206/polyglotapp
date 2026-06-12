const fs = require('fs');
const path = require('path');

const replacements = {
  'bg-slate-900': 'bg-slate-50 dark:bg-slate-900',
  'bg-slate-950': 'bg-white dark:bg-slate-950',
  'bg-slate-800': 'bg-slate-200 dark:bg-slate-800',
  'bg-slate-700': 'bg-slate-300 dark:bg-slate-700',
  'bg-slate-600': 'bg-slate-400 dark:bg-slate-600',
  'text-slate-100': 'text-slate-900 dark:text-slate-100',
  'text-slate-200': 'text-slate-800 dark:text-slate-200',
  'text-slate-300': 'text-slate-700 dark:text-slate-300',
  'text-slate-400': 'text-slate-600 dark:text-slate-400',
  'text-white': 'text-black dark:text-white',
  'border-slate-800': 'border-slate-200 dark:border-slate-800',
  'border-slate-700': 'border-slate-300 dark:border-slate-700',
  'border-slate-600': 'border-slate-400 dark:border-slate-600',
};

function processDir(dir) {
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const fullPath = path.join(dir, file);
    if (fs.statSync(fullPath).isDirectory()) {
      processDir(fullPath);
    } else if (fullPath.endsWith('.jsx')) {
      let content = fs.readFileSync(fullPath, 'utf8');
      for (const [oldClass, newClass] of Object.entries(replacements)) {
        // use regex to match whole words
        const regex = new RegExp(`\\b${oldClass}\\b`, 'g');
        content = content.replace(regex, newClass);
      }
      fs.writeFileSync(fullPath, content);
      console.log(`Updated ${fullPath}`);
    }
  }
}

processDir('src');
