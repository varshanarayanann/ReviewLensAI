import { MESSAGES } from '../messages'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const MIN_PASSWORD_LENGTH = 8

export function validateEmail(email: string): string | undefined {
  if (!email.trim()) return MESSAGES.emailRequired
  if (!EMAIL_PATTERN.test(email.trim())) return MESSAGES.emailInvalid
  return undefined
}

export function validateNewPassword(password: string): string | undefined {
  if (!password) return MESSAGES.passwordRequired
  if (password.length < MIN_PASSWORD_LENGTH) return MESSAGES.passwordTooShort
  return undefined
}
