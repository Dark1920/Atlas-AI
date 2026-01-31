'use client'

import React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { LucideIcon } from 'lucide-react'

interface StatsCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: LucideIcon
  trend?: {
    value: number
    label: string
  }
  variant?: 'default' | 'success' | 'warning' | 'danger'
  className?: string
}

const variantStyles = {
  default: 'border-border',
  success: 'border-risk-low/50 bg-risk-low/5',
  warning: 'border-risk-high/50 bg-risk-high/5',
  danger: 'border-risk-critical/50 bg-risk-critical/5',
}

const iconVariantStyles = {
  default: 'bg-accent-blue/20 text-accent-blue',
  success: 'bg-risk-low/20 text-risk-low',
  warning: 'bg-risk-high/20 text-risk-high',
  danger: 'bg-risk-critical/20 text-risk-critical',
}

export function StatsCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  variant = 'default',
  className,
}: StatsCardProps) {
  return (
    <Card className={cn(variantStyles[variant], className)}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-gray-400">{title}</p>
            <p className="text-3xl font-bold mt-1 font-mono">{value}</p>
            {subtitle && (
              <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
            )}
            {trend && (
              <div className={cn(
                'text-xs mt-2 flex items-center gap-1',
                trend.value >= 0 ? 'text-risk-low' : 'text-risk-critical'
              )}>
                <span>{trend.value >= 0 ? '↑' : '↓'} {Math.abs(trend.value)}%</span>
                <span className="text-gray-500">{trend.label}</span>
              </div>
            )}
          </div>
          <div className={cn(
            'p-3 rounded-lg',
            iconVariantStyles[variant]
          )}>
            <Icon className="w-6 h-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
