'use client'

import { useQuery } from '@tanstack/react-query'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { RiskGauge } from '@/components/RiskGauge'
import { SHAPWaterfall } from '@/components/SHAPWaterfall'
import { ExplanationPanel } from '@/components/ExplanationPanel'
import { getTransactionDetail, type RiskAssessment } from '@/lib/api'
import { formatCurrency, formatDate, cn } from '@/lib/utils'
import {
  ArrowLeft,
  Shield,
  MapPin,
  Smartphone,
  Clock,
  Store,
  User,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Loader2,
} from 'lucide-react'

export default function TransactionDetailPage() {
  const params = useParams()
  const router = useRouter()
  const transactionId = params.id as string

  // Fetch transaction detail
  const { data: assessment, isLoading, error } = useQuery<RiskAssessment>({
    queryKey: ['transaction', transactionId],
    queryFn: () => getTransactionDetail(transactionId),
    enabled: !!transactionId,
  })

  // Mock data for demo
  const mockAssessment: RiskAssessment = {
    transaction_id: transactionId,
    risk_score: 78,
    risk_level: 'high',
    confidence: 0.89,
    recommended_action: 'review',
    processing_time_ms: 42.5,
    top_factors: [
      {
        feature_name: 'amount_zscore',
        display_name: 'Amount Deviation',
        value: 3.5,
        impact: 18.2,
        impact_percentage: 32,
        direction: 'increases_risk',
      },
      {
        feature_name: 'country_risk',
        display_name: 'Country Risk',
        value: 0.7,
        impact: 12.5,
        impact_percentage: 22,
        direction: 'increases_risk',
      },
      {
        feature_name: 'is_new_device',
        display_name: 'New Device',
        value: 1,
        impact: 8.3,
        impact_percentage: 15,
        direction: 'increases_risk',
      },
      {
        feature_name: 'velocity_score',
        display_name: 'Velocity Score',
        value: 0.6,
        impact: 6.1,
        impact_percentage: 11,
        direction: 'increases_risk',
      },
      {
        feature_name: 'is_night',
        display_name: 'Night Transaction',
        value: 1,
        impact: 4.2,
        impact_percentage: 7,
        direction: 'increases_risk',
      },
    ],
    explanation: {
      technical: {
        model_version: '1.0.0',
        base_risk: 15,
        shap_values: {
          amount_zscore: 18.2,
          country_risk: 12.5,
          is_new_device: 8.3,
          velocity_score: 6.1,
          is_night: 4.2,
          merchant_category_risk: 3.1,
          distance_from_last_km: 2.8,
        },
        feature_values: {
          amount: 2450.0,
          amount_zscore: 3.5,
          country_risk: 0.7,
          is_new_device: 1,
          velocity_score: 0.6,
          hour_of_day: 23,
        },
        confidence_interval: [73, 83],
      },
      business: {
        summary: 'High risk transaction with multiple anomalies detected. The transaction amount is significantly higher than user baseline, originated from a high-risk country, and uses a previously unseen device.',
        top_factors: [
          {
            title: 'Amount Deviation',
            description: 'Transaction of $2,450 is 3.5x higher than typical spending of $700',
            impact: 18.2,
            icon: '📊',
          },
          {
            title: 'Country Risk',
            description: 'Transaction from Nigeria, which has elevated fraud risk',
            impact: 12.5,
            icon: '🌍',
          },
          {
            title: 'New Device',
            description: 'First time seeing this device fingerprint',
            impact: 8.3,
            icon: '📱',
          },
          {
            title: 'High Velocity',
            description: '5 transactions in the last hour, unusual for this user',
            impact: 6.1,
            icon: '⚡',
          },
        ],
        comparison_to_baseline: 'Typical transaction for this user: $127.45. This transaction: $2,450.00',
      },
      user: {
        headline: 'We flagged this transaction for your protection',
        reasons: [
          'This purchase is much larger than your typical spending',
          'The transaction location is far from where you normally shop',
          'We don\'t recognize the device used for this purchase',
        ],
        what_this_means: 'This could mean someone is trying to use your account without permission, or you might be making an unusual but legitimate purchase.',
        next_steps: 'Please review this transaction. If you don\'t recognize it, please contact us immediately.',
      },
    },
  }

  const displayData = assessment || mockAssessment

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin mx-auto text-accent-blue mb-4" />
          <p className="text-gray-400">Loading transaction details...</p>
        </div>
      </div>
    )
  }

  const actionButtons = {
    approve: {
      icon: CheckCircle,
      label: 'Approve',
      variant: 'success' as const,
    },
    review: {
      icon: AlertTriangle,
      label: 'Review Required',
      variant: 'warning' as const,
    },
    block: {
      icon: XCircle,
      label: 'Block',
      variant: 'destructive' as const,
    },
  }

  const action = actionButtons[displayData.recommended_action]

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-surface">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
              </Link>
              <div className="border-l border-border pl-4">
                <div className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-accent-blue" />
                  <h1 className="font-semibold">Transaction Detail</h1>
                </div>
                <p className="text-sm text-gray-400 font-mono">{transactionId}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={displayData.risk_level as any}>
                {displayData.risk_level.toUpperCase()}
              </Badge>
              <Button variant={action.variant} size="sm">
                <action.icon className="w-4 h-4 mr-2" />
                {action.label}
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Risk Score and Details */}
          <div className="space-y-6">
            {/* Risk Score Card */}
            <Card className={cn(
              'border-2',
              displayData.risk_level === 'critical' && 'border-risk-critical card-glow-risk-critical',
              displayData.risk_level === 'high' && 'border-risk-high card-glow-risk-high',
              displayData.risk_level === 'medium' && 'border-risk-medium',
              displayData.risk_level === 'low' && 'border-risk-low',
            )}>
              <CardContent className="p-8 flex flex-col items-center">
                <RiskGauge score={displayData.risk_score} size="lg" />
                
                <div className="mt-6 w-full space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Confidence</span>
                    <span className="font-mono">{(displayData.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Processing Time</span>
                    <span className="font-mono">{displayData.processing_time_ms.toFixed(1)}ms</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Recommended</span>
                    <Badge variant={displayData.recommended_action === 'approve' ? 'low' : displayData.recommended_action === 'block' ? 'critical' : 'high'}>
                      {displayData.recommended_action}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Transaction Details */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Transaction Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-surface-light">
                    <Store className="w-5 h-5 text-gray-400" />
                  </div>
                  <div>
                    <div className="text-sm text-gray-400">Merchant</div>
                    <div className="font-medium">Electronics Store</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-surface-light">
                    <MapPin className="w-5 h-5 text-gray-400" />
                  </div>
                  <div>
                    <div className="text-sm text-gray-400">Location</div>
                    <div className="font-medium">Lagos, Nigeria</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-surface-light">
                    <Smartphone className="w-5 h-5 text-gray-400" />
                  </div>
                  <div>
                    <div className="text-sm text-gray-400">Device</div>
                    <div className="font-medium">Mobile (iOS)</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-surface-light">
                    <Clock className="w-5 h-5 text-gray-400" />
                  </div>
                  <div>
                    <div className="text-sm text-gray-400">Timestamp</div>
                    <div className="font-medium">{formatDate(new Date())}</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-surface-light">
                    <User className="w-5 h-5 text-gray-400" />
                  </div>
                  <div>
                    <div className="text-sm text-gray-400">User ID</div>
                    <div className="font-medium font-mono">user_abc123</div>
                  </div>
                </div>

                <div className="pt-4 border-t border-border">
                  <div className="text-sm text-gray-400 mb-1">Amount</div>
                  <div className="text-3xl font-bold font-mono">
                    {formatCurrency(2450.00)}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Action Buttons */}
            <Card>
              <CardContent className="p-4 space-y-2">
                <Button variant="success" className="w-full">
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Approve Transaction
                </Button>
                <Button variant="warning" className="w-full">
                  <AlertTriangle className="w-4 h-4 mr-2" />
                  Flag for Review
                </Button>
                <Button variant="destructive" className="w-full">
                  <XCircle className="w-4 h-4 mr-2" />
                  Block Transaction
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Explanations */}
          <div className="lg:col-span-2 space-y-6">
            {/* SHAP Waterfall */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Feature Impact Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <SHAPWaterfall
                  contributions={displayData.top_factors}
                  baseRisk={15}
                  finalScore={displayData.risk_score}
                />
              </CardContent>
            </Card>

            {/* Explanation Panel */}
            {displayData.explanation && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Explanation</CardTitle>
                </CardHeader>
                <CardContent>
                  <ExplanationPanel
                    explanation={displayData.explanation}
                    riskScore={displayData.risk_score}
                  />
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
