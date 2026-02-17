import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { Lightbulb, TrendingDown, Shield, TrendingUp, CheckCircle, RefreshCw } from 'lucide-react'

const API_BASE = 'http://localhost:8080'

async function fetchAPI(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, options)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

// ============================================
// Types
// ============================================

interface Recommendation {
  id: string
  category: 'cost_reduction' | 'risk_mitigation' | 'revenue_optimization'
  title: string
  description: string
  priority_score: number
  expected_impact_eur: number
  confidence: number
  supporting_evidence: string[]
  created_at: string
  acknowledged: boolean
}

type CategoryFilter = 'all' | 'cost_reduction' | 'risk_mitigation' | 'revenue_optimization'

// ============================================
// Component
// ============================================

export function RecommendationsDashboard() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState<CategoryFilter>('all')
  const [acknowledging, setAcknowledging] = useState<string | null>(null)

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await fetchAPI('/api/recommendations?limit=50')
      setRecommendations(data.recommendations ?? [])
    } catch {
      setRecommendations([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

  const handleAcknowledge = async (id: string) => {
    setAcknowledging(id)
    try {
      await fetchAPI(`/api/recommendations/${id}/acknowledge`, { method: 'POST' })
      setRecommendations(prev =>
        prev.map(r => r.id === id ? { ...r, acknowledged: true } : r)
      )
    } catch {
      // silent fail
    } finally {
      setAcknowledging(null)
    }
  }

  const filtered = recommendations.filter(r => {
    if (activeFilter === 'all') return true
    return r.category === activeFilter
  })

  const costCount = recommendations.filter(r => r.category === 'cost_reduction').length
  const riskCount = recommendations.filter(r => r.category === 'risk_mitigation').length
  const revenueCount = recommendations.filter(r => r.category === 'revenue_optimization').length
  const highPriority = recommendations.filter(r => r.priority_score > 70).length

  // Chart data: score distribution buckets
  const scoreBuckets = [
    { range: '0–25', count: recommendations.filter(r => r.priority_score <= 25).length },
    { range: '26–50', count: recommendations.filter(r => r.priority_score > 25 && r.priority_score <= 50).length },
    { range: '51–75', count: recommendations.filter(r => r.priority_score > 50 && r.priority_score <= 75).length },
    { range: '76–100', count: recommendations.filter(r => r.priority_score > 75).length },
  ]

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'cost_reduction': return <TrendingDown className="w-4 h-4 text-red-500" />
      case 'risk_mitigation': return <Shield className="w-4 h-4 text-yellow-500" />
      case 'revenue_optimization': return <TrendingUp className="w-4 h-4 text-green-500" />
      default: return <Lightbulb className="w-4 h-4 text-blue-500" />
    }
  }

  const getCategoryStyle = (category: string) => {
    switch (category) {
      case 'cost_reduction': return 'bg-red-100 text-red-800'
      case 'risk_mitigation': return 'bg-yellow-100 text-yellow-800'
      case 'revenue_optimization': return 'bg-green-100 text-green-800'
      default: return 'bg-blue-100 text-blue-800'
    }
  }

  const getPriorityColor = (score: number) => {
    if (score > 70) return 'text-red-600'
    if (score > 40) return 'text-yellow-600'
    return 'text-green-600'
  }

  const categories: { key: CategoryFilter; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'cost_reduction', label: 'Cost Reduction' },
    { key: 'risk_mitigation', label: 'Risk Mitigation' },
    { key: 'revenue_optimization', label: 'Revenue Optimization' },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading recommendations...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Recommendations</h2>
          <p className="text-gray-500 mt-1">AI-scored actionable insights ranked by priority</p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Total</CardTitle>
            <Lightbulb className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{recommendations.length}</div>
            <p className="text-xs text-gray-500 mt-1">Recommendations</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">High Priority</CardTitle>
            <Lightbulb className="w-4 h-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{highPriority}</div>
            <p className="text-xs text-gray-500 mt-1">Score &gt; 70</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Cost Reduction</CardTitle>
            <TrendingDown className="w-4 h-4 text-red-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{costCount}</div>
            <p className="text-xs text-gray-500 mt-1">Opportunities</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Risk Items</CardTitle>
            <Shield className="w-4 h-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{riskCount}</div>
            <p className="text-xs text-gray-500 mt-1">To mitigate</p>
          </CardContent>
        </Card>
      </div>

      {/* Score Distribution Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Priority Score Distribution</CardTitle>
          <CardDescription>Count of recommendations by score range</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={scoreBuckets}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="range" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#6366f1" name="Recommendations" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Filter Tabs */}
      <div className="flex gap-2 flex-wrap">
        {categories.map((cat) => (
          <button
            key={cat.key}
            onClick={() => setActiveFilter(cat.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeFilter === cat.key
                ? 'bg-primary-600 text-white'
                : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {cat.label}
            {cat.key !== 'all' && (
              <span className="ml-1.5 text-xs opacity-75">
                ({cat.key === 'cost_reduction' ? costCount
                  : cat.key === 'risk_mitigation' ? riskCount
                  : revenueCount})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Recommendations List */}
      {filtered.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-gray-500">
            <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
            No recommendations in this category.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filtered.map((rec) => (
            <Card
              key={rec.id}
              className={rec.acknowledged ? 'opacity-60' : ''}
            >
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    {getCategoryIcon(rec.category)}
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <CardTitle className="text-base">{rec.title}</CardTitle>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getCategoryStyle(rec.category)}`}>
                          {rec.category.replace(/_/g, ' ')}
                        </span>
                        {rec.acknowledged && (
                          <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                            Done
                          </span>
                        )}
                      </div>
                      <CardDescription className="mt-1">{rec.description}</CardDescription>
                    </div>
                  </div>
                  <div className="flex flex-col items-center min-w-[70px]">
                    <span className={`text-2xl font-bold ${getPriorityColor(rec.priority_score)}`}>
                      {rec.priority_score.toFixed(0)}
                    </span>
                    <span className="text-xs text-gray-500">/ 100</span>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {/* Evidence */}
                  {rec.supporting_evidence && rec.supporting_evidence.length > 0 && (
                    <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                      <p className="text-xs font-semibold text-gray-600 mb-1">Supporting Evidence</p>
                      <ul className="space-y-0.5">
                        {rec.supporting_evidence.map((e, i) => (
                          <li key={i} className="text-xs text-gray-700">• {e}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Footer */}
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-gray-500 space-x-4">
                      {rec.expected_impact_eur > 0 && (
                        <span>
                          Expected impact: <span className="font-medium text-gray-700">
                            {rec.expected_impact_eur.toLocaleString()} EUR
                          </span>
                        </span>
                      )}
                      <span>
                        Confidence: <span className="font-medium text-gray-700">
                          {(rec.confidence * 100).toFixed(0)}%
                        </span>
                      </span>
                    </div>
                    {!rec.acknowledged && (
                      <button
                        onClick={() => handleAcknowledge(rec.id)}
                        disabled={acknowledging === rec.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        {acknowledging === rec.id ? 'Marking...' : 'Mark Done'}
                      </button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
