'use client'

import React from 'react'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts'

interface RiskDistributionChartProps {
  data: Record<string, number>
}

const COLORS = {
  low: '#10B981',
  medium: '#FCD34D',
  high: '#F59E0B',
  critical: '#DC2626',
}

export function RiskDistributionChart({ data }: RiskDistributionChartProps) {
  const chartData = Object.entries(data).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value,
    color: COLORS[name as keyof typeof COLORS] || '#6B7280',
  }))

  const total = chartData.reduce((sum, d) => sum + d.value, 0)

  return (
    <ResponsiveContainer width="100%" height={250}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          paddingAngle={2}
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          content={({ active, payload }) => {
            if (active && payload && payload.length) {
              const data = payload[0].payload
              const percentage = ((data.value / total) * 100).toFixed(1)
              return (
                <div className="bg-surface-light border border-border rounded-lg p-3 shadow-lg">
                  <p className="font-medium" style={{ color: data.color }}>
                    {data.name}
                  </p>
                  <p className="text-sm text-gray-400">
                    {data.value} transactions ({percentage}%)
                  </p>
                </div>
              )
            }
            return null
          }}
        />
        <Legend
          verticalAlign="bottom"
          height={36}
          formatter={(value) => (
            <span className="text-gray-400 text-sm">{value}</span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
