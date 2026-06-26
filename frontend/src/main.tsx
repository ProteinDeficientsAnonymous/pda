import './index.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from './App.tsx';
import { enableMocking } from './mocks/enable';

const rootElement = document.getElementById('root');
if (!rootElement) throw new Error('Root element #root not found');

// Start MSW first (no-op unless mock mode is on) so the worker is intercepting
// before the app fires its boot requests.
void enableMocking().then(() => {
  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
