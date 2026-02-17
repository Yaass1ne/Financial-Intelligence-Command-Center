import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { fetchAPI } from '../lib/utils'
import { Receipt, AlertTriangle, Clock, DollarSign, Users, List } from 'lucide-react'

interface Invoice {
  invoice_id: string
  date: string
  vendor: string
  amount: number
  status: string
  days_overdue: number
}

interface VendorGroup {
  vendor: string
  count: number
  total_amount: number
  max_days: number
  avg_days: number
}

export function InvoicesDashboard() {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterDays, setFilterDays] = useState(0)
  const [viewMode, setViewMode] = useState<'list' | 'vendor'>('vendor')

  useEffect(() => {
    fetchAPI<Invoice[]>(`/invoices/overdue?days=${filterDays}`)
      .then(data => {
        setInvoices(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [filterDays])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-gray-500">Loading invoices...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-red-500">Error: {error}</div>
      </div>
    )
  }

  const totalOverdue = invoices.reduce((sum, inv) => sum + inv.amount, 0)
  const criticalInvoices = invoices.filter(inv => inv.days_overdue > 365)
  const averageOverdue = invoices.length > 0
    ? invoices.reduce((sum, inv) => sum + inv.days_overdue, 0) / invoices.length
    : 0

  // Group by vendor
  const vendorMap = new Map<string, VendorGroup>()
  for (const inv of invoices) {
    const key = inv.vendor || 'Unknown'
    if (!vendorMap.has(key)) {
      vendorMap.set(key, { vendor: key, count: 0, total_amount: 0, max_days: 0, avg_days: 0 })
    }
    const g = vendorMap.get(key)!
    g.count += 1
    g.total_amount += inv.amount
    g.max_days = Math.max(g.max_days, inv.days_overdue)
    g.avg_days = g.avg_days + inv.days_overdue
  }
  const vendorGroups: VendorGroup[] = Array.from(vendorMap.values())
    .map(g => ({ ...g, avg_days: Math.round(g.avg_days / g.count) }))
    .sort((a, b) => b.total_amount - a.total_amount)

  const getUrgency = (days: number) => {
    if (days > 365) return 'critical'
    if (days > 180) return 'high'
    if (days > 60) return 'medium'
    return 'low'
  }

  const urgencyStyle: Record<string, string> = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-blue-100 text-blue-800',
  }

  const urgencyLabel: Record<string, string> = {
    critical: 'Critical',
    high: 'High',
    medium: 'Medium',
    low: 'Low',
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Invoices & Treasury Management</h2>
        <p className="text-gray-500 mt-1">Track overdue payments and cash flow</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Total Overdue</CardTitle>
            <Receipt className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{invoices.length}</div>
            <p className="text-xs text-gray-500 mt-1">Unpaid invoices</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Overdue Amount</CardTitle>
            <DollarSign className="w-4 h-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">${(totalOverdue / 1000000).toFixed(2)}M</div>
            <p className="text-xs text-gray-500 mt-1">Outstanding balance</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Critical ({'>'} 1yr)</CardTitle>
            <AlertTriangle className="w-4 h-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{criticalInvoices.length}</div>
            <p className="text-xs text-gray-500 mt-1">Over 365 days late</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Avg Days Overdue</CardTitle>
            <Clock className="w-4 h-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{Math.round(averageOverdue)}</div>
            <p className="text-xs text-gray-500 mt-1">Average delay</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters + View Toggle */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex gap-2">
              {[
                { label: 'All Overdue', value: 0 },
                { label: '30+ Days', value: 30 },
                { label: '60+ Days', value: 60 },
                { label: '90+ Days', value: 90 },
                { label: '365+ Days', value: 365 },
              ].map(f => (
                <button
                  key={f.value}
                  onClick={() => setFilterDays(f.value)}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    filterDays === f.value
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setViewMode('vendor')}
                className={`flex items-center gap-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                  viewMode === 'vendor'
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <Users className="w-4 h-4" />
                By Vendor
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`flex items-center gap-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                  viewMode === 'list'
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <List className="w-4 h-4" />
                All Invoices
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Vendor Grouping View */}
      {viewMode === 'vendor' && (
        <Card>
          <CardHeader>
            <CardTitle>Overdue by Vendor</CardTitle>
            <CardDescription>
              {vendorGroups.length} vendors — {invoices.length} total invoices
            </CardDescription>
          </CardHeader>
          <CardContent>
            {vendorGroups.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No overdue invoices found</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-3 px-4 font-semibold text-gray-900">Vendor</th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-900"># Invoices</th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-900">Total Amount</th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-900">Max Days Late</th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-900">Avg Days Late</th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-900">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {vendorGroups.map((vg) => {
                      const urgency = getUrgency(vg.max_days)
                      return (
                        <tr key={vg.vendor} className="border-b hover:bg-gray-50">
                          <td className="py-3 px-4 font-medium">{vg.vendor}</td>
                          <td className="text-right py-3 px-4">{vg.count}</td>
                          <td className="text-right py-3 px-4 font-semibold text-red-600">
                            ${(vg.total_amount / 1000).toFixed(1)}K
                          </td>
                          <td className="text-right py-3 px-4 font-bold text-red-600">
                            {vg.max_days.toLocaleString()} days
                          </td>
                          <td className="text-right py-3 px-4 text-gray-600">
                            {vg.avg_days.toLocaleString()} days
                          </td>
                          <td className="text-right py-3 px-4">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${urgencyStyle[urgency]}`}>
                              {urgencyLabel[urgency]}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Individual Invoice List View */}
      {viewMode === 'list' && (
        <Card>
          <CardHeader>
            <CardTitle>Overdue Invoices</CardTitle>
            <CardDescription>
              {invoices.length} invoices requiring attention
            </CardDescription>
          </CardHeader>
          <CardContent>
            {invoices.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No overdue invoices found</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-3 px-4 font-semibold text-gray-900">Invoice ID</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-900">Vendor</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-900">Date</th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-900">Amount</th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-900">Days Overdue</th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-900">Urgency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map((invoice) => {
                      const urgency = getUrgency(invoice.days_overdue)
                      return (
                        <tr key={invoice.invoice_id} className="border-b hover:bg-gray-50">
                          <td className="py-3 px-4 font-medium">{invoice.invoice_id}</td>
                          <td className="py-3 px-4">{invoice.vendor}</td>
                          <td className="py-3 px-4">{new Date(invoice.date).toLocaleDateString()}</td>
                          <td className="text-right py-3 px-4 font-semibold">
                            ${(invoice.amount / 1000).toFixed(2)}K
                          </td>
                          <td className="text-right py-3 px-4 font-bold text-red-600">
                            {invoice.days_overdue.toLocaleString()} days
                          </td>
                          <td className="text-right py-3 px-4">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${urgencyStyle[urgency]}`}>
                              {urgencyLabel[urgency]}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
