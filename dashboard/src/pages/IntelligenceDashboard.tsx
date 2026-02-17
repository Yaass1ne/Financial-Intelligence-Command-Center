import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { Brain, Zap, Shield, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react'

const API_BASE = 'http://localhost:8080'

async function fetchAPI(path: string) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

// ============================================
// Types
// ============================================

interface WeakSignal {
  id: string
  score: number
  signals: Array<{ type: string; subject: string; detail: string; weight: number }>
  detected_at: string
  acknowledged: boolean
}

interface Decision {
  id: string
  source: string
  severity: 'critical' | 'warning' | 'info'
  title: string
  description: string
  recommended_action: string
  financial_impact_eur: number
  priority_score: number
}

interface Pattern {
  id: string
  type: string
  subject: string
  description: string
  confidence: number
  evidence_count: number
  last_updated: string
}

// ============================================
// Component
// ============================================

export function IntelligenceDashboard() {
  const [weakSignals, setWeakSignals] = useState<WeakSignal[]>([])
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [patterns, setPatterns] = useState<Pattern[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const loadData = async () => {
    try {
      const [wsData, fusionData, memoryData] = await Promise.allSettled([
        fetchAPI('/api/intelligence/weak-signals'),
        fetchAPI('/api/fusion/decisions'),
        fetchAPI('/api/memory/patterns'),
      ])

      if (wsData.status === 'fulfilled') setWeakSignals(wsData.value.weak_signals ?? [])
      if (fusionData.status === 'fulfilled') setDecisions(fusionData.value.decisions ?? [])
      if (memoryData.status === 'fulfilled') setPatterns(memoryData.value.patterns ?? [])
    } catch {
      // continue with empty state
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => { loadData() }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetch(`${API_BASE}/api/memory/refresh`, { method: 'POST' })
    setTimeout(loadData, 1500)
  }

  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case 'critical': return 'border-red-500 bg-red-50 text-red-800'
      case 'warning': return 'border-yellow-500 bg-yellow-50 text-yellow-800'
      default: return 'border-blue-500 bg-blue-50 text-blue-800'
    }
  }

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800'
      case 'warning': return 'bg-yellow-100 text-yellow-800'
      default: return 'bg-blue-100 text-blue-800'
    }
  }

  const getPatternTypeColor = (type: string) => {
    switch (type) {
      case 'vendor_overbilling': return 'bg-orange-100 text-orange-800'
      case 'department_overspend': return 'bg-red-100 text-red-800'
      case 'late_payment_pattern': return 'bg-yellow-100 text-yellow-800'
      case 'seasonal_spike': return 'bg-purple-100 text-purple-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading intelligence data...</div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Intelligence Hub</h2>
          <p className="text-gray-500 mt-1">Weak signals, decision fusion & episodic memory</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Refreshing...' : 'Refresh Patterns'}
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Weak Signal Clusters</CardTitle>
            <Zap className="w-4 h-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{weakSignals.length}</div>
            <p className="text-xs text-gray-500 mt-1">Active stress clusters</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Tactical Decisions</CardTitle>
            <Shield className="w-4 h-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{decisions.length}</div>
            <p className="text-xs text-gray-500 mt-1">Ranked action items</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Learned Patterns</CardTitle>
            <Brain className="w-4 h-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">{patterns.length}</div>
            <p className="text-xs text-gray-500 mt-1">Episodic memory entries</p>
          </CardContent>
        </Card>
      </div>

      {/* ============================================
          Section 1: Weak Signal Radar
          ============================================ */}
      <div>
        <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-orange-500" />
          Weak Signal Radar
        </h3>
        {weakSignals.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-gray-500">
              <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
              No active stress clusters detected. Financial health looks stable.
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {weakSignals.map((ws) => (
              <Card key={ws.id} className="border-l-4 border-orange-500">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">Stress Cluster</CardTitle>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-orange-600">Score: {ws.score}</span>
                      <div className="w-24 h-2 bg-gray-200 rounded-full">
                        <div
                          className="h-2 bg-orange-500 rounded-full"
                          style={{ width: `${Math.min(100, ws.score * 10)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                  <CardDescription>
                    Detected: {new Date(ws.detected_at).toLocaleString()}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {ws.signals.map((sig, i) => (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <span className="text-gray-700">
                          <span className="font-medium">{sig.subject}</span> — {sig.detail}
                        </span>
                        <span className="text-xs bg-orange-100 text-orange-800 px-2 py-0.5 rounded-full">
                          +{sig.weight}
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* ============================================
          Section 2: Decision Fusion
          ============================================ */}
      <div>
        <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5 text-blue-500" />
          Decision Fusion — Ranked Tactical Actions
        </h3>
        {decisions.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-gray-500">
              No urgent decisions detected. System is operating normally.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {decisions.slice(0, 10).map((dec, idx) => (
              <Card key={dec.id} className={`border-l-4 ${getSeverityStyle(dec.severity).split(' ')[0]}`}>
                <CardContent className="py-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1">
                      <span className="text-lg font-bold text-gray-400 w-6 mt-0.5">#{idx + 1}</span>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="font-semibold text-gray-900">{dec.title}</h4>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getSeverityBadge(dec.severity)}`}>
                            {dec.severity.toUpperCase()}
                          </span>
                          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                            {dec.source}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{dec.description}</p>
                        <p className="text-sm text-blue-700 mt-1 italic">
                          Action: {dec.recommended_action}
                        </p>
                        {dec.financial_impact_eur > 0 && (
                          <p className="text-xs text-gray-500 mt-1">
                            Financial impact: {dec.financial_impact_eur.toLocaleString()} EUR
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-center min-w-[60px]">
                      <span className="text-2xl font-bold text-gray-900">{dec.priority_score.toFixed(0)}</span>
                      <span className="text-xs text-gray-500">priority</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* ============================================
          Section 3: Episodic Memory Browser
          ============================================ */}
      <div>
        <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Brain className="w-5 h-5 text-purple-500" />
          Episodic Memory Browser
        </h3>
        {patterns.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-gray-500">
              <AlertTriangle className="w-8 h-8 text-yellow-400 mx-auto mb-2" />
              No patterns learned yet. Run the ingestion pipeline and click "Refresh Patterns".
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {patterns.map((p) => (
              <Card key={p.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getPatternTypeColor(p.type)}`}>
                        {p.type.replace(/_/g, ' ').toUpperCase()}
                      </span>
                      <CardTitle className="text-base mt-2">{p.subject}</CardTitle>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-bold text-purple-600">
                        {(p.confidence * 100).toFixed(0)}%
                      </div>
                      <div className="text-xs text-gray-500">confidence</div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-700">{p.description}</p>
                  <div className="flex items-center justify-between mt-3 text-xs text-gray-400">
                    <span>{p.evidence_count} evidence points</span>
                    {p.last_updated && (
                      <span>Updated: {new Date(p.last_updated).toLocaleDateString()}</span>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
