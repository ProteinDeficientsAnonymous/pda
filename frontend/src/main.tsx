import './index.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from './App.tsx';
import { enableMocking } from './mocks/enable';

const rootElement = document.getElementById('root');
if (!rootElement) throw new Error('Root element #root not found');

// Start MSW (no-op unless mock mode is on) before the app fires boot requests.
void enableMocking().then(() => {
  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
