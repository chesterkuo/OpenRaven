import { useTranslation } from 'react-i18next';

const LOCALES = [
  { code: 'en',    label: 'English' },
  { code: 'zh-TW', label: '繁體中文' },
  { code: 'zh-CN', label: '简体中文' },
  { code: 'ja',    label: '日本語' },
  { code: 'ko',    label: '한국어' },
  { code: 'fr',    label: 'Français' },
  { code: 'es',    label: 'Español' },
  { code: 'nl',    label: 'Nederlands' },
  { code: 'it',    label: 'Italiano' },
  { code: 'vi',    label: 'Tiếng Việt' },
  { code: 'th',    label: 'ไทย' },
  { code: 'ru',    label: 'Русский' },
] as const;

export function LanguageSelector() {
  const { i18n } = useTranslation();

  const handleChange = async (lng: string) => {
    await i18n.changeLanguage(lng);
    fetch('/api/auth/locale', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ locale: lng }),
    }).catch(() => {});
  };

  return (
    <select
      value={i18n.language}
      onChange={e => handleChange(e.target.value)}
      aria-label="Language"
      className="text-sm px-2 py-1 cursor-pointer"
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--color-border)',
        color: 'var(--color-text)',
      }}
    >
      {LOCALES.map(l => (
        <option key={l.code} value={l.code}>{l.label}</option>
      ))}
    </select>
  );
}
