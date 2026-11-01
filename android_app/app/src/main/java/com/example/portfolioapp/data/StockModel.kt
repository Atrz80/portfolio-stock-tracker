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
