export interface User {
  id: string;
  anonymous_id: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  session_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  agent_id?: string | null; // <--- NOVO
  agents?: { name: string } | null; // <--- NOVO (para o Join no Sidebar)
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  type: 'text' | 'voice';
  audio_url?: string;
  image_url?: string;
  created_at: string;
  sender_user_id?: string | null;
  sender?: {
    first_name: string | null;
    last_name: string | null;
    avatar_url: string | null;
  } | null;
  /**
   * SPEC-096 — o que o TURNO sabe sobre esta mensagem, gravado junto com ela.
   *
   * `client_request_id` é o que faz uma retentativa continuar sendo a MESMA
   * pergunta (R3) e o que dá ao Realtime um jeito de deduplicar sem comparar
   * texto (E10 — duas perguntas iguais são duas perguntas).
   *
   * `turn.artifacts` é o que faz o cartão da peça sobreviver ao reload: sem
   * ele, a entrega só existiria enquanto o stream estivesse aberto.
   */
  payload?: {
    client_request_id?: string;
    turn?: {
      submitted_at?: string;
      status?: 'interrupted' | 'failed' | 'complete';
      code?: string;
      stopped_by?: string;
      artifacts?: {
        artifact_id: string;
        title: string;
        kind_human: string;
        href: string;
      }[];
    };
    [chave: string]: unknown;
  } | null;
}

export interface N8NTextRequest {
  chatInput: string;
  sessionId: string;
}

export interface N8NVoiceRequest {
  audioData: string;
  sessionId: string;
}

export interface N8NResponse {
  output: string;
}

export interface UserV2 {
  id: string;
  email: string;
  password_hash: string | null;
  first_name: string;
  last_name: string;
  cpf: string;
  phone: string;
  birth_date: string;
  plan_id: string | null;
  plan_status: 'active' | 'past_due' | 'canceled' | 'suspended';
  subscription_amount: number | null;
  billing_cycle: 'monthly' | 'yearly' | null;
  subscription_started_at: string | null;
  subscription_renews_at: string | null;
  subscription_canceled_at: string | null;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  credits_used_this_month: number;
  credits_limit: number | null;
  storage_used_mb: number;
  storage_limit_mb: number | null;
  usage_reset_date: string | null;
  last_login_at: string | null;
  last_login_ip: string | null;
  failed_login_attempts: number;
  account_locked_until: string | null;
  terms_accepted_at: string;
  privacy_policy_accepted_at: string;
  marketing_consent: boolean;
  data_deletion_requested_at: string | null;
  google_id: string | null;
  github_id: string | null;
  oauth_provider: 'email' | 'google' | 'github';
  company_id: string | null;
  status: 'pending' | 'active' | 'suspended';
  role: 'admin_company' | 'member';
  is_owner: boolean;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface PlanFeatures {
  file_types: string[];
  custom_prompt: boolean;
  llm_choice: boolean;
  support_level: 'basic' | 'priority';
  rag_enabled: boolean;
  features_list: string[];
}

export interface Plan {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  monthly_price: number;
  yearly_price: number;
  credits_limit: number;
  storage_limit_mb: number;
  max_users: number | null;
  features: PlanFeatures;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface PaymentHistory {
  id: string;
  user_id: string;
  amount: number;
  currency: string;
  status: 'succeeded' | 'failed' | 'pending' | 'refunded';
  payment_method: 'credit_card' | 'pix' | 'boleto' | 'stripe' | null;
  stripe_payment_intent_id: string | null;
  stripe_invoice_id: string | null;
  description: string | null;
  metadata: Record<string, any>;
  paid_at: string | null;
  created_at: string;
}

export interface PasswordResetToken {
  id: string;
  user_id: string;
  token: string;
  expires_at: string;
  used_at: string | null;
  created_at: string;
}

export interface Company {
  id: string;
  company_name: string;
  legal_name: string | null;
  cnpj: string | null;
  webhook_url: string;
  n8n_instance_url: string | null;
  use_langchain: boolean;
  max_users: number;
  status: 'active' | 'trial' | 'suspended' | 'cancelled';
  primary_contact_name: string | null;
  primary_contact_email: string | null;
  primary_contact_phone: string | null;
  notes: string | null;
  // Address fields
  cep: string | null;
  street: string | null;
  number: string | null;
  complement: string | null;
  neighborhood: string | null;
  city: string | null;
  state: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminUser {
  id: string;
  email: string;
  password_hash: string;
  name: string;
  created_at: string;
  updated_at?: string;
  companyId?: string | null;
  role?: 'company_admin';
}
