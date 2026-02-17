import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { fetchAPI } from '../lib/utils'
import { FileText, Calendar, DollarSign, AlertCircle, Search } from 'lucide-react'

interface Contract {
  contract_id: string
  vendor: string
  end_date: string
  annual_value: number
  auto_renewal: boolean
  days_until_expiry: number
}

export function ContractsDashboard() {
  const [contracts, setContracts] = useState<Contract[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [daysFilter, setDaysFilter] = useState<number | 'all'>(90)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    const endpoint = daysFilter === 'all'
      ? '/contracts'
      : `/contracts/expiring?days=${daysFilter}`
    fetchAPI<Contract[]>(endpoint)
      .then(data => {
        setContracts(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [daysFilter])

  const filteredContracts = contracts.filter(contract =>
    contract.vendor.toLowerCase().includes(searchQuery.toLowerCase()) ||
    contract.contract_id.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const criticalContracts = filteredContracts.filter(c => c.days_until_expiry <= 30)
  const warningContracts = filteredContracts.filter(c => c.days_until_expiry > 30 && c.days_until_expiry <= 60)
  const totalValue = filteredContracts.reduce((sum, c) => sum + c.annual_value, 0)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-gray-500">Loading contracts...</div>
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

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Contracts & Clause Management</h2>
        <p className="text-gray-500 mt-1">Track contract expirations and manage clauses</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Expiring Soon</CardTitle>
            <FileText className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{filteredContracts.length}</div>
            <p className="text-xs text-gray-500 mt-1">{daysFilter === 'all' ? 'All contracts' : `Next ${daysFilter} days`}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Critical (≤30 days)</CardTitle>
            <AlertCircle className="w-4 h-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{criticalContracts.length}</div>
            <p className="text-xs text-gray-500 mt-1">Immediate action required</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Warning (31-60 days)</CardTitle>
            <Calendar className="w-4 h-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{warningContracts.length}</div>
            <p className="text-xs text-gray-500 mt-1">Review needed</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Total Value at Risk</CardTitle>
            <DollarSign className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${(totalValue / 1000000).toFixed(2)}M</div>
            <p className="text-xs text-gray-500 mt-1">Annual contract value</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search by vendor or contract ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
            <div className="flex gap-2 flex-wrap">
              {([30, 60, 90, 180] as number[]).map(days => (
                <button
                  key={days}
                  onClick={() => setDaysFilter(days)}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    daysFilter === days
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {days} Days
                </button>
              ))}
              <button
                onClick={() => setDaysFilter('all')}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  daysFilter === 'all'
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                All
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Contracts List */}
      <Card>
        <CardHeader>
          <CardTitle>Expiring Contracts</CardTitle>
          <CardDescription>
            {filteredContracts.length} contracts {daysFilter === 'all' ? '(all)' : `expiring in the next ${daysFilter} days`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {filteredContracts.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No contracts found matching your criteria</p>
            ) : (
              filteredContracts.map((contract) => {
                const urgencyLevel = contract.days_until_expiry <= 30 ? 'critical' :
                                     contract.days_until_expiry <= 60 ? 'warning' : 'normal'

                return (
                  <div
                    key={contract.contract_id}
                    className={`p-4 rounded-lg border-l-4 ${
                      urgencyLevel === 'critical'
                        ? 'border-red-500 bg-red-50'
                        : urgencyLevel === 'warning'
                        ? 'border-yellow-500 bg-yellow-50'
                        : 'border-gray-300 bg-white'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <h3 className="text-lg font-semibold text-gray-900">{contract.vendor}</h3>
                          <span className="text-sm text-gray-500">#{contract.contract_id}</span>
                        </div>
                        <div className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-4">
                          <div>
                            <p className="text-xs text-gray-500">Expiration Date</p>
                            <p className="text-sm font-medium text-gray-900">
                              {new Date(contract.end_date).toLocaleDateString()}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Annual Value</p>
                            <p className="text-sm font-medium text-gray-900">
                              ${(contract.annual_value / 1000000).toFixed(2)}M
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Auto Renewal</p>
                            <p className="text-sm font-medium text-gray-900">
                              {contract.auto_renewal ? 'Yes' : 'No'}
                            </p>
                          </div>
                        </div>
                      </div>
                      <div className="text-right ml-4">
                        <div className={`text-2xl font-bold ${
                          urgencyLevel === 'critical'
                            ? 'text-red-600'
                            : urgencyLevel === 'warning'
                            ? 'text-yellow-600'
                            : 'text-gray-600'
                        }`}>
                          {contract.days_until_expiry}
                        </div>
                        <p className="text-xs text-gray-500">days left</p>
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
