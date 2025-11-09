// Allow importing plain CSS files as side-effects in TypeScript
// This prevents TS2882: Cannot find module or type declarations for side-effect import
declare module '*.css';
declare module '*.module.css';
declare module '*.scss';
declare module '*.module.scss';

// Optional: image and font modules (helpful for next/image imports in TS)
declare module '*.svg';
declare module '*.png';
declare module '*.jpg';
declare module '*.jpeg';
declare module '*.webp';

export {};
