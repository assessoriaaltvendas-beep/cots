// =====================================================================
// Configuração do Supabase
// Em Supabase > Project Settings > API, copie:
//   - "Project URL"            -> supabaseUrl
//   - "anon public" (API key)  -> supabaseAnonKey
// A chave "anon" pode ficar pública: quem protege os dados são as regras
// de segurança criadas pelo arquivo supabase/schema.sql.
// NUNCA coloque aqui a chave "service_role".
// =====================================================================
window.APP_CONFIG = {
  supabaseUrl: 'COLE_AQUI_O_PROJECT_URL',
  supabaseAnonKey: 'COLE_AQUI_A_CHAVE_ANON_PUBLIC'
};
