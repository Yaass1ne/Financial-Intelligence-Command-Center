import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { AlertTriangle, TrendingUp, Bell, CheckCircle } from 'lucide-react'

interface Alert {
  id: string
  type: 'critical' | 'warning' | 'info' | 'success'
  category: string
  title: string
  description: string
  recommendation: string
  impact: string
  timestamp: string
}

export function AlertsDashboard() {
  const [alerts] = useState<Alert[]>([
    {
      id: '1',
      type: 'critical',
      category: 'Budget',
      title: 'Marketing Department 45% Over Budget',
      description: 'Marketing has exceeded budget by $2.5M in Q4 2024',
      recommendation: 'Review marketing spend and implement cost controls. Consider reallocating resources from underutilized departments.',
      impact: 'High - Affects overall FY budget by 8%',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: '2',
      type: 'critical',
      category: 'Contract',
      title: '3 Critical Contracts Expiring This Month',
      description: 'High-value contracts with cloud providers expire in 15 days',
      recommendation: 'Immediate action required: Schedule renewal negotiations with vendors. Consider multi-year deals for better rates.',
      impact: 'Critical - $12M annual value at risk',
      timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: '3',
      type: 'warning',
      category: 'Invoice',
      title: '12 Invoices Overdue >60 Days',
      description: 'Multiple invoices from key vendors are significantly overdue',
      recommendation: 'Prioritize payment of critical vendor invoices to maintain relationships. Review payment approval process.',
      impact: 'Medium - May affect vendor relationships',
      timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: '4',
      type: 'warning',
      category: 'Budget',
      title: 'IT Department Trending Towards Overspend',
      description: 'Current burn rate suggests 15% overspend by year-end',
      recommendation: 'Review IT spending patterns. Consider deferring non-critical projects to Q1 2025.',
      impact: 'Medium - Projected $800K overspend',
      timestamp: new Date(Date.now() - 36 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: '5',
      type: 'info',
      category: 'Optimization',
      title: 'Potential Contract Consolidation Opportunity',
      description: '5 software vendors providing similar services',
      recommendation: 'Consolidate SaaS subscriptions to single vendor for 25% cost savings ($500K annually).',
      impact: 'Low - Optimization opportunity',
      timestamp: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: '6',
      type: 'success',
      category: 'Budget',
      title: 'Operations Department 20% Under Budget',
      description: 'Operations has maintained efficiency while staying under budget',
      recommendation: 'Document cost-saving practices for replication in other departments.',
      impact: 'Positive - $1.2M savings available for reallocation',
      timestamp: new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString(),
    },
  ])

  const criticalCount = alerts.filter(a => a.type === 'critical').length
  const warningCount = alerts.filter(a => a.type === 'warning').length
  const infoCount = alerts.filter(a => a.type === 'info').length

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'critical':
        return <AlertTriangle className="w-5 h-5 text-red-500" />
      case 'warning':
        return <Bell className="w-5 h-5 text-yellow-500" />
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      default:
        return <TrendingUp className="w-5 h-5 text-blue-500" />
    }
  }

  const getAlertStyle = (type: string) => {
    switch (type) {
      case 'critical':
        return 'border-red-500 bg-red-50'
      case 'warning':
        return 'border-yellow-500 bg-yellow-50'
      case 'success':
        return 'border-green-500 bg-green-50'
      default:
        return 'border-blue-500 bg-blue-50'
    }
  }

  const getTimeAgo = (timestamp: string) => {
    const hours = Math.floor((Date.now() - new Date(timestamp).getTime()) / (1000 * 60 * 60))
    if (hours < 1) return 'Just now'
    if (hours === 1) return '1 hour ago'
    if (hours < 24) return `${hours} hours ago`
    const days = Math.floor(hours / 24)
    if (days === 1) return '1 day ago'
    return `${days} days ago`
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Alerts & Recommendations</h2>
        <p className="text-gray-500 mt-1">AI-powered insights and actionable recommendations</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Total Alerts</CardTitle>
            <Bell className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{alerts.length}</div>
            <p className="text-xs text-gray-500 mt-1">Active notifications</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Critical</CardTitle>
            <AlertTriangle className="w-4 h-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{criticalCount}</div>
            <p className="text-xs text-gray-500 mt-1">Immediate action needed</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Warnings</CardTitle>
            <Bell className="w-4 h-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{warningCount}</div>
            <p className="text-xs text-gray-500 mt-1">Review recommended</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Opportunities</CardTitle>
            <TrendingUp className="w-4 h-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{infoCount}</div>
            <p className="text-xs text-gray-500 mt-1">Cost savings identified</p>
          </CardContent>
        </Card>
      </div>

      {/* Alerts List */}
      <div className="space-y-4">
        {alerts.map((alert) => (
          <Card key={alert.id} className={`border-l-4 ${getAlertStyle(alert.type)}`}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3">
                  {getAlertIcon(alert.type)}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <CardTitle className="text-lg">{alert.title}</CardTitle>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        alert.type === 'critical' ? 'bg-red-100 text-red-800' :
                        alert.type === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                        alert.type === 'success' ? 'bg-green-100 text-green-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {alert.category}
                      </span>
                    </div>
                    <CardDescription className="mt-1">
                      {alert.description}
                    </CardDescription>
                  </div>
                </div>
                <span className="text-xs text-gray-500 whitespace-nowrap ml-4">
                  {getTimeAgo(alert.timestamp)}
                </span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <h4 className="font-semibold text-sm text-gray-900 mb-2">💡 Recommendation</h4>
                  <p className="text-sm text-gray-700">{alert.recommendation}</p>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">
                    <span className="font-semibold">Impact:</span> {alert.impact}
                  </span>
                  <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium">
                    Take Action
                  </button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
