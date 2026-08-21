import React from 'react';

interface ErrorBannerProps {
  message: string | null;
  onDismiss?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, onDismiss }) => {
  if (!message) return null;

  return (
    <div className="mb-4 p-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-lg flex items-center justify-between text-red-800 dark:text-red-200 shadow-sm">
      <div className="flex items-center space-x-2">
        <svg className="w-5 h-5 text-red-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span className="text-sm font-medium">{message}</span>
      </div>
      {onDismiss && (
        <button 
          onClick={onDismiss} 
          className="text-red-500 hover:text-red-700 dark:hover:text-red-300 font-bold px-2 py-1 text-sm"
          aria-label="Dismiss error"
        >
          &times;
        </button>
      )}
    </div>
  );
};
