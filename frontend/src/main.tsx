import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/tokens.css'
import './index.css'
import App from './App.tsx'
import { ConfigError, loadConfig } from './lib/config'

const root = createRoot(document.getElementById('root')!)

try {
  const config = loadConfig()
  root.render(
    <StrictMode>
      <App config={config} />
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
