const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// Types
export interface Location {
  country: string
  city?: string
  latitude?: number
  longitude?: number
}

export interface Device {
  fingerprint: string
  type: string
  browser?: string
  os?: string
}

export interface Transaction {
  transaction_id: string
  user_id: string
  amount: number
  currency: string
  merchant_id: string
  merchant_category: string
  location: Location
  device: Device
  timestamp: string
}

export interface FeatureContribution {
  feature_name: string
  display_name: string
  value: number | string
  impact: number
  impact_percentage: number
  direction: 'increases_risk' | 'decreases_risk'
}

export interface RiskFactor {
  title: string
  description: string
  impact: number
  icon: string
}

export interface TechnicalExplanation {
  model_version: string
  base_risk: number
  shap_values: Record<string, number>
  feature_values: Record<string, number | string>
  confidence_interval: [number, number]
}

export interface BusinessExplanation {
  summary: string
  top_factors: RiskFactor[]
  comparison_to_baseline: string
}

export interface UserExplanation {
  headline: string
  reasons: string[]
  what_this_means: string
  next_steps: string
}

export interface FullExplanation {
  technical: TechnicalExplanation
  business: BusinessExplanation
  user: UserExplanation
}

export interface RiskAssessment {
  transaction_id: string
  risk_score: number
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  confidence: number
  recommended_action: 'approve' | 'review' | 'block'
  processing_time_ms: number
  top_factors: FeatureContribution[]
  explanation?: FullExplanation
}

export interface TransactionListItem {
  transaction_id: string
  user_id: string
  amount: number
  currency: string
  merchant_id: string
  merchant_category: string
  location_country: string
  timestamp: string
  risk_score: number
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  recommended_action: 'approve' | 'review' | 'block'
}

export interface TransactionListResponse {
  transactions: TransactionListItem[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface DashboardStats {
  total_transactions_today: number
  total_amount_today: number
  fraud_detected_today: number
  fraud_amount_blocked: number
  average_risk_score: number
  false_positive_rate: number
  transactions_by_risk_level: Record<string, number>
}

// API Functions
async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

// Dashboard
export async function getDashboardStats(): Promise<DashboardStats> {
  return fetchAPI<DashboardStats>('/dashboard/stats')
}

// Transactions
export async function getTransactions(params?: {
  page?: number
  page_size?: number
  risk_level?: string
  min_score?: number
  max_score?: number
}): Promise<TransactionListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.page_size) searchParams.set('page_size', params.page_size.toString())
  if (params?.risk_level) searchParams.set('risk_level', params.risk_level)
  if (params?.min_score) searchParams.set('min_score', params.min_score.toString())
  if (params?.max_score) searchParams.set('max_score', params.max_score.toString())
  
  const query = searchParams.toString()
  return fetchAPI<TransactionListResponse>(`/transactions${query ? `?${query}` : ''}`)
}

export async function getTransactionDetail(transactionId: string): Promise<RiskAssessment> {
  return fetchAPI<RiskAssessment>(`/transactions/${transactionId}?include_explanation=true`)
}

export async function getTransactionExplanation(transactionId: string): Promise<FullExplanation> {
  return fetchAPI<FullExplanation>(`/explain/${transactionId}`)
}

// Scoring
export async function scoreTransaction(transaction: Omit<Transaction, 'transaction_id'>): Promise<RiskAssessment> {
  return fetchAPI<RiskAssessment>('/score', {
    method: 'POST',
    body: JSON.stringify(transaction),
  })
}

// Demo
export async function generateDemoData(count: number = 100): Promise<{ generated: number; samples: any[] }> {
  return fetchAPI<{ generated: number; samples: any[] }>(`/demo/generate?count=${count}`, {
    method: 'POST',
  })
}
