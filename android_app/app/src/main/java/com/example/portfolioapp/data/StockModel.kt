package com.example.portfolioapp.data

import com.google.gson.annotations.SerializedName

data class Stock(
    @SerializedName("name") val name: String,
    @SerializedName("ticker") val ticker: String,
    @SerializedName("shares") val shares: Double,
    @SerializedName("price") val price: Double,
    @SerializedName("value") val value: Double,
    @SerializedName("gain") val gain: Double,
    @SerializedName("gainPct") val gainPct: Double,
    @SerializedName("allocation") val allocation: Double,
    @SerializedName("badge") val badge: String = "",
    @SerializedName("init") val init: String = "",
    @SerializedName("marketSymbol") val marketSymbol: String? = null,
    @SerializedName("marketPrice") val marketPrice: Double? = null,
    @SerializedName("marketCurrency") val marketCurrency: String? = null,
    @SerializedName("previousClose") val previousClose: Double? = null,
    @SerializedName("changePercent") val changePercent: Double? = null,
    @SerializedName("quoteTimestamp") val quoteTimestamp: String? = null,
    @SerializedName("dataSource") val dataSource: String? = null,
    @SerializedName("dataStatus") val dataStatus: String? = null
)

data class CatalogSymbol(
    @SerializedName("symbol") val symbol: String,
    @SerializedName("displaySymbol") val displaySymbol: String,
    @SerializedName("description") val description: String,
    @SerializedName("type") val type: String,
    @SerializedName("exchange") val exchange: String
)

data class TickerCatalog(
    @SerializedName("exchange") val exchange: String,
    @SerializedName("symbols") val symbols: List<CatalogSymbol> = emptyList(),
    @SerializedName("updated_at") val updatedAt: String? = null
)

data class CatalogRefreshResponse(
    @SerializedName("status") val status: String,
    @SerializedName("exchange") val exchange: String,
    @SerializedName("symbols") val symbols: List<CatalogSymbol> = emptyList(),
    @SerializedName("updated_at") val updatedAt: String? = null
) {
    fun toCatalog() = TickerCatalog(
        exchange = exchange,
        symbols = symbols,
        updatedAt = updatedAt
    )
}

data class HistoryPoint(
    @SerializedName("timestamp") val timestamp: Long,
    @SerializedName("value") val value: Double,
    @SerializedName("position_value") val positionValue: Double? = null,
    @SerializedName("estimated_cost_basis") val estimatedCostBasis: Double? = null,
    @SerializedName("shares") val shares: Double? = null
)

data class HistorySummary(
    @SerializedName("start_value") val startValue: Double,
    @SerializedName("end_value") val endValue: Double,
    @SerializedName("change") val change: Double,
    @SerializedName("change_pct") val changePct: Double,
    @SerializedName("high") val high: Double,
    @SerializedName("high_timestamp") val highTimestamp: Long,
    @SerializedName("low") val low: Double,
    @SerializedName("low_timestamp") val lowTimestamp: Long
)

data class InvestmentSummary(
    @SerializedName("start_value") val startValue: Double,
    @SerializedName("end_value") val endValue: Double,
    @SerializedName("estimated_contributions") val estimatedContributions: Double,
    @SerializedName("gain") val gain: Double,
    @SerializedName("gain_pct") val gainPct: Double
)

data class AssetHistory(
    @SerializedName("name") val name: String,
    @SerializedName("isin") val isin: String,
    @SerializedName("cost_basis") val costBasis: Double,
    @SerializedName("shares") val shares: Double,
    @SerializedName("last_price") val lastPrice: Double,
    @SerializedName("last_value") val lastValue: Double,
    @SerializedName("unrealized_gain") val unrealizedGain: Double,
    @SerializedName("unrealized_gain_pct") val unrealizedGainPct: Double,
    @SerializedName("period_gain") val periodGain: Double,
    @SerializedName("period_gain_pct") val periodGainPct: Double
)

data class PortfolioHistory(
    @SerializedName("period") val period: String,
    @SerializedName("available_from") val availableFrom: String,
    @SerializedName("asset") val asset: AssetHistory? = null,
    @SerializedName("summary") val summary: HistorySummary,
    @SerializedName("investment_summary") val investmentSummary: InvestmentSummary,
    @SerializedName("points") val points: List<HistoryPoint> = emptyList(),
    @SerializedName("investment_points") val investmentPoints: List<HistoryPoint>? = null,
    @SerializedName("note") val note: String
)
