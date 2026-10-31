import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import './styles/tokens.css'
import './index.css'
import App from './App.tsx'
import { ConfigError, loadConfig } from './lib/config'
import { createSupabaseClient } from './lib/supabase'

const root = createRoot(document.getElementById('root')!)

try {
  const config = loadConfig()
  const supabase = createSupabaseClient(config)
  root.render(
    <StrictMode>
      <BrowserRouter>
        <App config={config} authClient={supabase.auth} />
      </BrowserRouter>
    </StrictMode>,
  )
} catch (error) {
  if (!(error instanceof ConfigError)) throw error
  console.error(error.message)
  root.render(
    <main className="app">
      <h1>ReviewLens AI</h1>
      <p role="alert" className="status status--unreachable">
        Configuration error: {error.message}
      </p>
    </main>,
  )
}
