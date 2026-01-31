'use client'

import React from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { 
  Code2, 
  Briefcase, 
  User, 
  AlertTriangle,
  CheckCircle,
  ArrowRight 
} from 'lucide-react'

interface TechnicalExplanation {
  model_version: string
  base_risk: number
  shap_values: Record<string, number>
  feature_values: Record<string, number | string>
  confidence_interval: [number, number]
}

interface RiskFactor {
  title: string
  description: string
  impact: number
  icon: string
}

interface BusinessExplanation {
  summary: string
  top_factors: RiskFactor[]
  comparison_to_baseline: string
}

interface UserExplanation {
  headline: string
  reasons: string[]
  what_this_means: string
  next_steps: string
}

interface FullExplanation {
  technical: TechnicalExplanation
  business: BusinessExplanation
  user: UserExplanation
}

interface ExplanationPanelProps {
  explanation: FullExplanation
  riskScore: number
  className?: string
}

export function ExplanationPanel({ explanation, riskScore, className }: ExplanationPanelProps) {
  return (
    <div className={cn('w-full', className)}>
      <Tabs defaultValue="business" className="w-full">
        <TabsList className="w-full">
          <TabsTrigger value="user" className="flex-1 gap-2">
            <User className="w-4 h-4" />
            Simple
          </TabsTrigger>
          <TabsTrigger value="business" className="flex-1 gap-2">
            <Briefcase className="w-4 h-4" />
            Analyst
          </TabsTrigger>
          <TabsTrigger value="technical" className="flex-1 gap-2">
            <Code2 className="w-4 h-4" />
            Technical
          </TabsTrigger>
        </TabsList>

        {/* User-Friendly Explanation */}
        <TabsContent value="user" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {riskScore >= 60 ? (
                  <AlertTriangle className="w-5 h-5 text-risk-high" />
                ) : (
                  <CheckCircle className="w-5 h-5 text-risk-low" />
                )}
                {explanation.user.headline}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-2">What we noticed:</h4>
                <ul className="space-y-2">
                  {explanation.user.reasons.map((reason, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-accent-blue mt-1">•</span>
                      <span>{reason}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="border-t border-border pt-4">
                <h4 className="text-sm font-medium text-gray-400 mb-2">What this means:</h4>
                <p className="text-gray-300">{explanation.user.what_this_means}</p>
              </div>

              <div className="bg-surface-light rounded-lg p-4">
                <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                  <ArrowRight className="w-4 h-4 text-accent-blue" />
                  Next Steps
                </h4>
                <p className="text-gray-300">{explanation.user.next_steps}</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Business/Analyst Explanation */}
        <TabsContent value="business" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Risk Analysis</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-surface-light rounded-lg p-4">
                <p className="text-gray-300">{explanation.business.summary}</p>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-3">Top Risk Factors:</h4>
                <div className="space-y-3">
                  {explanation.business.top_factors.map((factor, i) => (
                    <div 
                      key={i}
                      className={cn(
                        'p-4 rounded-lg border',
                        factor.impact > 0 
                          ? 'border-risk-high/30 bg-risk-high/5' 
                          : 'border-risk-low/30 bg-risk-low/5'
                      )}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-2">
                          <span className="text-xl">{factor.icon}</span>
                          <div>
                            <h5 className="font-medium">{factor.title}</h5>
                            <p className="text-sm text-gray-400 mt-1">
                              {factor.description}
                            </p>
                          </div>
                        </div>
                        <Badge variant={factor.impact > 0 ? 'high' : 'low'}>
                          {factor.impact > 0 ? '+' : ''}{factor.impact.toFixed(1)}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="border-t border-border pt-4">
                <h4 className="text-sm font-medium text-gray-400 mb-2">Baseline Comparison:</h4>
                <p className="text-gray-300">{explanation.business.comparison_to_baseline}</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Technical Explanation */}
        <TabsContent value="technical" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Technical Details</span>
                <Badge variant="secondary">
                  Model {explanation.technical.model_version}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-surface-light rounded-lg p-3">
                  <div className="text-xs text-gray-400">Base Risk</div>
                  <div className="font-mono text-lg">{explanation.technical.base_risk}</div>
                </div>
                <div className="bg-surface-light rounded-lg p-3">
                  <div className="text-xs text-gray-400">Confidence Interval</div>
                  <div className="font-mono text-lg">
                    {explanation.technical.confidence_interval[0]} - {explanation.technical.confidence_interval[1]}
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-3">SHAP Values:</h4>
                <div className="bg-surface-light rounded-lg p-4 overflow-x-auto">
                  <pre className="text-xs font-mono text-gray-300">
                    {JSON.stringify(explanation.technical.shap_values, null, 2)}
                  </pre>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-3">Feature Values:</h4>
                <div className="bg-surface-light rounded-lg p-4 overflow-x-auto">
                  <pre className="text-xs font-mono text-gray-300">
                    {JSON.stringify(explanation.technical.feature_values, null, 2)}
                  </pre>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
