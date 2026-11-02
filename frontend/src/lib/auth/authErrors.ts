import { isAuthError, isAuthRetryableFetchError, isAuthWeakPasswordError } from '@supabase/supabase-js'
import { MESSAGES } from '../messages'

const RATE_LIMIT_CODES = new Set(['over_request_rate_limit', 'over_email_send_rate_limit'])

export function authErrorMessage(error: unknown): string {
  if (isAuthRetryableFetchError(error)) return MESSAGES.offline
  if (isAuthWeakPasswordError(error)) return MESSAGES.passwordTooShort
  if (!isAuthError(error)) return MESSAGES.unexpected

  if (error.status === 429 || (error.code && RATE_LIMIT_CODES.has(error.code))) {
    return MESSAGES.tooManyAttempts
  }
  switch (error.code) {
    case 'invalid_credentials':
      return MESSAGES.invalidCredentials
    case 'email_not_confirmed':
      return MESSAGES.emailNotConfirmed
    case 'user_already_exists':
    case 'email_exists':
      return MESSAGES.emailExists
    case 'weak_password':
      return MESSAGES.passwordTooShort
    default:
      return MESSAGES.unexpected
  }
}
