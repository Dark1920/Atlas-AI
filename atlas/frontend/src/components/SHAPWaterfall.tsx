'use client'

import React from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts'
import { cn } from '@/lib/utils'

interface FeatureContribution {
  feature_name: string
  display_name: string
  value: number | string
  impact: number
  impact_percentage: number
  direction: 'increases_risk' | 'decreases_risk'
}

interface SHAPWaterfallProps {
  contributions: FeatureContribution[]
  baseRisk?: number
  finalScore: number
  className?: string
}

export function SHAPWaterfall({ 
  contributions, 
  baseRisk = 15, 
  finalScore,
  className 
}: SHAPWaterfallProps) {
  // Sort by absolute impact
  const sortedContributions = [...contributions]
    .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))
    .slice(0, 7)

  // Prepare data for chart
  const data = sortedContributions.map((c) => ({
    name: c.display_name,
    impact: c.impact,
    value: c.value,
    percentage: c.impact_percentage,
  }))

  return (
    <div className={cn('w-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-gray-400">Base Risk:</span>
          <span className="font-mono font-medium">{baseRisk}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-400">Final Score:</span>
          <span className="font-mono font-bold text-lg">{finalScore}</span>
        </div>
      </div>

      {/* Bar Chart */}
      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
        >
          <XAxis 
            type="number" 
            domain={['dataMin - 5', 'dataMax + 5']}
            tickFormatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(0)}`}
            stroke="#6B7280"
            fontSize={12}
          />
          <YAxis 
            type="category" 
            dataKey="name" 
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
            width={100}
            stroke="#6B7280"
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload
                return (
                  <div className="bg-surface-light border border-border rounded-lg p-3 shadow-lg">
                    <p className="font-medium text-white">{data.name}</p>
                    <p className="text-sm text-gray-400">
                      Value: <span className="text-white font-mono">{data.value}</span>
                    </p>
                    <p className="text-sm text-gray-400">
                      Impact: <span className={data.impact > 0 ? 'text-risk-high' : 'text-risk-low'}>
                        {data.impact > 0 ? '+' : ''}{data.impact.toFixed(1)} ({data.percentage.toFixed(0)}%)
                      </span>
                    </p>
                  </div>
                )
              }
              return null
            }}
          />
          <ReferenceLine x={0} stroke="#4B5563" />
          <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.impact > 0 ? '#F59E0B' : '#10B981'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 mt-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm bg-risk-high" />
          <span className="text-gray-400">Increases Risk</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm bg-risk-low" />
          <span className="text-gray-400">Decreases Risk</span>
        </div>
      </div>

      {/* Feature List */}
      <div className="mt-6 space-y-2">
        {sortedContributions.map((c, i) => (
          <div 
            key={i}
            className="flex items-center justify-between p-2 rounded-lg bg-surface-light/50"
          >
            <div className="flex-1">
              <span className="text-sm font-medium">{c.display_name}</span>
              <span className="text-xs text-gray-500 ml-2">
                = {typeof c.value === 'number' ? c.value.toFixed(2) : c.value}
              </span>
            </div>
            <div className={cn(
              'font-mono text-sm font-medium px-2 py-0.5 rounded',
              c.impact > 0 ? 'bg-risk-high/20 text-risk-high' : 'bg-risk-low/20 text-risk-low'
            )}>
              {c.impact > 0 ? '+' : ''}{c.impact.toFixed(1)}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
