'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { StatsCard } from '@/components/StatsCard'
import { TransactionTable } from '@/components/TransactionTable'
import { RiskDistributionChart } from '@/components/RiskDistributionChart'
import { 
  getDashboardStats, 
  getTransactions, 
  generateDemoData,
  type DashboardStats,
  type TransactionListResponse 
} from '@/lib/api'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { 
  Activity,
  Shield,
  AlertTriangle,
  DollarSign,
  RefreshCw,
  Plus,
  TrendingUp
} from 'lucide-react'

export default function DashboardPage() {
  const queryClient = useQueryClient()

  // Fetch dashboard stats
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Fetch recent transactions
  const { data: transactions, isLoading: txnLoading } = useQuery<TransactionListResponse>({
    queryKey: ['transactions', { page: 1, page_size: 10 }],
    queryFn: () => getTransactions({ page: 1, page_size: 10 }),
    refetchInterval: 15000, // Refresh every 15 seconds
  })

  // Generate demo data mutation
  const generateMutation = useMutation({
    mutationFn: () => generateDemoData(50),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
  })

  // Mock data for when API is not available
  const mockStats: DashboardStats = {
    total_transactions_today: 1247,
    total_amount_today: 156892.45,
    fraud_detected_today: 23,
    fraud_amount_blocked: 45230.00,
    average_risk_score: 28.5,
    false_positive_rate: 0.018,
    transactions_by_risk_level: {
      low: 1089,
      medium: 112,
      high: 38,
      critical: 8,
    },
  }

  const displayStats = stats || mockStats
  const displayTransactions = transactions?.transactions || []

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-surface">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield className="w-8 h-8 text-accent-blue" />
              <div>
                <h1 className="text-xl font-bold">Atlas</h1>
                <p className="text-sm text-gray-400">Fraud Detection Dashboard</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
                  queryClient.invalidateQueries({ queryKey: ['transactions'] })
                }}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh
              </Button>
              <Button
                size="sm"
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending}
              >
                <Plus className="w-4 h-4 mr-2" />
                {generateMutation.isPending ? 'Generating...' : 'Generate Demo Data'}
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatsCard
            title="Transactions Today"
            value={formatNumber(displayStats.total_transactions_today)}
            subtitle={formatCurrency(displayStats.total_amount_today)}
            icon={Activity}
            trend={{ value: 12, label: 'vs yesterday' }}
          />
          <StatsCard
            title="Fraud Detected"
            value={displayStats.fraud_detected_today}
            subtitle={`${((displayStats.fraud_detected_today / displayStats.total_transactions_today) * 100).toFixed(2)}% of total`}
            icon={AlertTriangle}
            variant="danger"
          />
          <StatsCard
            title="Amount Blocked"
            value={formatCurrency(displayStats.fraud_amount_blocked)}
            subtitle="Potential losses prevented"
            icon={DollarSign}
            variant="success"
          />
          <StatsCard
            title="Avg Risk Score"
            value={displayStats.average_risk_score.toFixed(1)}
            subtitle={`FP Rate: ${(displayStats.false_positive_rate * 100).toFixed(2)}%`}
            icon={TrendingUp}
          />
        </div>

        {/* Charts and Transaction List */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Risk Distribution */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Risk Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <RiskDistributionChart data={displayStats.transactions_by_risk_level} />
              
              {/* Quick Stats */}
              <div className="grid grid-cols-2 gap-3 mt-4">
                <div className="bg-surface-light rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-risk-low">
                    {displayStats.transactions_by_risk_level.low || 0}
                  </div>
                  <div className="text-xs text-gray-400">Low Risk</div>
                </div>
                <div className="bg-surface-light rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-risk-critical">
                    {displayStats.transactions_by_risk_level.critical || 0}
                  </div>
                  <div className="text-xs text-gray-400">Critical</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recent Transactions */}
          <Card className="lg:col-span-2">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Recent Transactions</CardTitle>
              <Badge variant="secondary">
                Live
                <span className="ml-1 w-2 h-2 rounded-full bg-risk-low animate-pulse inline-block" />
              </Badge>
            </CardHeader>
            <CardContent>
              {statsError ? (
                <div className="text-center py-8">
                  <AlertTriangle className="w-12 h-12 mx-auto text-risk-high mb-4" />
                  <p className="text-gray-400 mb-4">Unable to connect to API</p>
                  <p className="text-sm text-gray-500 mb-4">
                    Make sure the backend is running at http://localhost:8000
                  </p>
                  <Button
                    variant="outline"
                    onClick={() => generateMutation.mutate()}
                  >
                    Generate Demo Data
                  </Button>
                </div>
              ) : (
                <TransactionTable 
                  transactions={displayTransactions}
                  isLoading={txnLoading}
                />
              )}
            </CardContent>
          </Card>
        </div>

        {/* Model Performance Section */}
        <div className="mt-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">System Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-surface-light rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-risk-low" />
                    <span className="text-sm text-gray-400">Model Status</span>
                  </div>
                  <div className="font-medium">Healthy</div>
                </div>
                <div className="bg-surface-light rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-risk-low" />
                    <span className="text-sm text-gray-400">Avg Latency</span>
                  </div>
                  <div className="font-medium font-mono">45ms</div>
                </div>
                <div className="bg-surface-light rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-risk-low" />
                    <span className="text-sm text-gray-400">Model Version</span>
                  </div>
                  <div className="font-medium font-mono">v1.0.0</div>
                </div>
                <div className="bg-surface-light rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-risk-low" />
                    <span className="text-sm text-gray-400">ROC-AUC</span>
                  </div>
                  <div className="font-medium font-mono">0.95</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-surface mt-auto">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between text-sm text-gray-400">
            <span>Atlas v1.0.0 - Explainable AI Fraud Detection</span>
            <span>Last updated: {new Date().toLocaleTimeString()}</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
