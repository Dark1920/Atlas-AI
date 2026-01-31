import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

export function getRiskColor(score: number): string {
  if (score >= 80) return '#DC2626' // critical
  if (score >= 60) return '#F59E0B' // high
  if (score >= 40) return '#FCD34D' // medium
  return '#10B981' // low
}

export function getRiskLevel(score: number): RiskLevel {
  if (score >= 80) return 'critical'
  if (score >= 60) return 'high'
  if (score >= 40) return 'medium'
  return 'low'
}

export function getRiskTextClass(level: RiskLevel): string {
  const classes: Record<RiskLevel, string> = {
    critical: 'text-risk-critical',
    high: 'text-risk-high',
    medium: 'text-risk-medium',
    low: 'text-risk-low',
  }
  return classes[level]
}

export function getRiskBgClass(level: RiskLevel): string {
  const classes: Record<RiskLevel, string> = {
    critical: 'bg-risk-critical',
    high: 'bg-risk-high',
    medium: 'bg-risk-medium',
    low: 'bg-risk-low',
  }
  return classes[level]
}

export function getRiskBorderClass(level: RiskLevel): string {
  const classes: Record<RiskLevel, string> = {
    critical: 'border-risk-critical',
    high: 'border-risk-high',
    medium: 'border-risk-medium',
    low: 'border-risk-low',
  }
  return classes[level]
}

export function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(amount)
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date))
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num)
}

export function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`
}
