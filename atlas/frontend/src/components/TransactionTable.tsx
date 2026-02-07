'use client'

import React from 'react'
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { 
  formatCurrency, 
  formatDate, 
  getRiskLevel,
  cn 
} from '@/lib/utils'
import { 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  ChevronRight,
  MapPin,
  Clock
} from 'lucide-react'

interface TransactionListItem {
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

interface TransactionTableProps {
  transactions: TransactionListItem[]
  isLoading?: boolean
}

const actionIcons = {
  approve: <CheckCircle className="w-4 h-4 text-risk-low" />,
  review: <AlertTriangle className="w-4 h-4 text-risk-high" />,
  block: <XCircle className="w-4 h-4 text-risk-critical" />,
}

const riskBadgeVariant: Record<string, 'low' | 'medium' | 'high' | 'critical'> = {
  low: 'low',
  medium: 'medium',
  high: 'high',
  critical: 'critical',
}

export function TransactionTable({ transactions, isLoading }: TransactionTableProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-16 bg-surface-light animate-pulse rounded-lg" />
        ))}
      </div>
    )
  }

  if (transactions.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p>No transactions found</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border text-left text-sm text-gray-400">
            <th className="pb-3 pl-4 font-medium">Transaction</th>
            <th className="pb-3 font-medium">Amount</th>
            <th className="pb-3 font-medium">Location</th>
            <th className="pb-3 font-medium">Risk Score</th>
            <th className="pb-3 font-medium">Action</th>
            <th className="pb-3 pr-4 font-medium"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/50">
          {transactions.map((txn) => (
            <tr 
              key={txn.transaction_id}
              className="hover:bg-surface-light/50 transition-colors"
            >
              <td className="py-4 pl-4">
                <div>
                  <div className="font-medium text-sm">
                    {txn.merchant_category}
                  </div>
                  <div className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                    <Clock className="w-3 h-3" />
                    {formatDate(txn.timestamp)}
                  </div>
                </div>
              </td>
              <td className="py-4">
                <span className="font-mono font-medium">
                  {formatCurrency(txn.amount, txn.currency)}
                </span>
              </td>
              <td className="py-4">
                <div className="flex items-center gap-1 text-sm text-gray-400">
                  <MapPin className="w-3 h-3" />
                  {txn.location_country}
                </div>
              </td>
              <td className="py-4">
                <div className="flex items-center gap-2">
                  <span className={cn(
                    'font-mono font-bold text-lg',
                    txn.risk_level === 'critical' && 'text-risk-critical',
                    txn.risk_level === 'high' && 'text-risk-high',
                    txn.risk_level === 'medium' && 'text-risk-medium',
                    txn.risk_level === 'low' && 'text-risk-low',
                  )}>
                    {txn.risk_score}
                  </span>
                  <Badge variant={riskBadgeVariant[txn.risk_level]}>
                    {txn.risk_level}
                  </Badge>
                </div>
              </td>
              <td className="py-4">
                <div className="flex items-center gap-2">
                  {actionIcons[txn.recommended_action]}
                  <span className="text-sm capitalize">
                    {txn.recommended_action}
                  </span>
                </div>
              </td>
              <td className="py-4 pr-4">
                <Link 
                  href={`/transactions/${txn.transaction_id}`}
                  className="p-2 rounded-lg hover:bg-surface-light transition-colors inline-flex"
                >
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
