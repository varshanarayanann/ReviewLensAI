import { createClient } from '@supabase/supabase-js'
import type { AppConfig } from './config'

export function createSupabaseClient(config: AppConfig) {
  return createClient(config.supabaseUrl, config.supabaseAnonKey, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
  })
}
