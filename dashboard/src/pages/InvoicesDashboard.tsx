import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { fetchAPI } from '../lib/utils'
import { Receipt, AlertTriangle, Clock, DollarSign } from 'lucide-react'

interface Invoice {
  invoice_id: string
  date: string
  vendor: string
  amount: number
  status: string
  days_overdue: number
}

export function InvoicesDashboard() {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterDays, setFilterDays] = useState(0)

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
  const criticalInvoices = invoices.filter(inv => inv.days_overdue > 60)
  const averageOverdue = invoices.length > 0
    ? invoices.reduce((sum, inv) => sum + inv.days_overdue, 0) / invoices.length
    : 0

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
            <CardTitle className="text-sm font-medium text-gray-600">Critical ({'>'}60 days)</CardTitle>
            <AlertTriangle className="w-4 h-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{criticalInvoices.length}</div>
            <p className="text-xs text-gray-500 mt-1">Severely overdue</p>
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

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            <button
              onClick={() => setFilterDays(0)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filterDays === 0
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All Overdue
            </button>
            <button
              onClick={() => setFilterDays(30)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filterDays === 30
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              30+ Days
            </button>
            <button
              onClick={() => setFilterDays(60)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filterDays === 60
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              60+ Days
            </button>
            <button
              onClick={() => setFilterDays(90)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filterDays === 90
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              90+ Days
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Invoices Table */}
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
                    const urgency = invoice.days_overdue > 90 ? 'critical' :
                                   invoice.days_overdue > 60 ? 'high' :
                                   invoice.days_overdue > 30 ? 'medium' : 'low'

                    return (
                      <tr key={invoice.invoice_id} className="border-b hover:bg-gray-50">
                        <td className="py-3 px-4 font-medium">{invoice.invoice_id}</td>
                        <td className="py-3 px-4">{invoice.vendor}</td>
                        <td className="py-3 px-4">{new Date(invoice.date).toLocaleDateString()}</td>
                        <td className="text-right py-3 px-4 font-semibold">
                          ${(invoice.amount / 1000).toFixed(2)}K
                        </td>
                        <td className="text-right py-3 px-4 font-bold text-red-600">
                          {invoice.days_overdue} days
                        </td>
                        <td className="text-right py-3 px-4">
                          {urgency === 'critical' && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                              Critical
                            </span>
                          )}
                          {urgency === 'high' && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                              High
                            </span>
                          )}
                          {urgency === 'medium' && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                              Medium
                            </span>
                          )}
                          {urgency === 'low' && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                              Low
                            </span>
                          )}
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
    </div>
  )
}
