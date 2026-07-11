import './index.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from './App.tsx';
import { enableMocking } from './mocks/enable';

const rootElement = document.getElementById('root');
if (!rootElement) throw new Error('Root element #root not found');

const root = createRoot(rootElement);

// Start MSW (no-op unless mock mode is on) before the app fires boot requests.
// Render even if mock setup fails so the failure is visible, not a blank page.
void enableMocking()
  .catch((err: unknown) => {
    console.error('mock setup failed — rendering app without mocks', err);
  })
  .then(() => {
    root.render(
      <StrictMode>
        <App />
      </StrictMode>,
    );
  });
