import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import Backend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';

export const SUPPORTED_LNGS = [
  'en', 'zh-TW', 'zh-CN', 'ja', 'ko', 'fr', 'es', 'nl', 'it', 'vi', 'th', 'ru',
] as const;

export type SupportedLocale = (typeof SUPPORTED_LNGS)[number];

i18n
  .use(Backend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    supportedLngs: [...SUPPORTED_LNGS],
    ns: ['common', 'ask', 'ingest', 'graph', 'wiki', 'connectors', 'agents', 'courses', 'status', 'auth', 'audit'],
    defaultNS: 'common',
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },
    interpolation: {
      escapeValue: false,
    },
  });

i18n.on('languageChanged', (lng) => {
  document.documentElement.setAttribute('lang', lng);
});

export default i18n;
