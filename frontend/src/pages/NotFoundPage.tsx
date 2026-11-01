import { Link } from 'react-router'

export default function NotFoundPage() {
  return (
    <main className="app-main">
      <h1>Page not found</h1>
      <p className="muted">The page you're looking for doesn't exist. Check the address, or go back to the start.</p>
      <p>
        <Link to="/">Go to ReviewLens AI</Link>
      </p>
    </main>
  )
}
