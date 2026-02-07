'use client'

import React from 'react'
import { getRiskColor, getRiskLevel, cn } from '@/lib/utils'

interface RiskGaugeProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  className?: string
}

export function RiskGauge({ score, size = 'md', showLabel = true, className }: RiskGaugeProps) {
  const riskLevel = getRiskLevel(score)
  const color = getRiskColor(score)
  
  // Size configurations
  const sizes = {
    sm: { width: 80, strokeWidth: 6, fontSize: 'text-xl' },
    md: { width: 120, strokeWidth: 8, fontSize: 'text-3xl' },
    lg: { width: 160, strokeWidth: 10, fontSize: 'text-5xl' },
  }
  
  const { width, strokeWidth, fontSize } = sizes[size]
  const radius = (width - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const progress = (score / 100) * circumference
  const dashOffset = circumference - progress

  return (
    <div className={cn('relative inline-flex flex-col items-center', className)}>
      <svg
        width={width}
        height={width}
        className="transform -rotate-90"
      >
        {/* Background circle */}
        <circle
          cx={width / 2}
          cy={width / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-surface-light"
        />
        {/* Progress circle */}
        <circle
          cx={width / 2}
          cy={width / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          className="transition-all duration-500 ease-out"
        />
      </svg>
      
      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span 
          className={cn('font-bold font-mono', fontSize)}
          style={{ color }}
        >
          {score}
        </span>
        {showLabel && (
          <span className="text-xs text-gray-400 uppercase tracking-wider">
            /100
          </span>
        )}
      </div>
      
      {/* Risk level label */}
      {showLabel && (
        <div 
          className="mt-2 text-sm font-medium uppercase tracking-wide"
          style={{ color }}
        >
          {riskLevel} Risk
        </div>
      )}
    </div>
  )
}
