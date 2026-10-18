import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en";
import hi from "./locales/hi";

/** Add tl, id (Bahasa), uk, zh by dropping a file in ./locales and listing it here. */
export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
] as const;

if (!i18n.isInitialized) {
  void i18n.use(initReactI18next).init({
    resources: { en: { translation: en }, hi: { translation: hi } },
    lng: "en",
    fallbackLng: "en",
    interpolation: { escapeValue: false },
  });
}

export default i18n;
