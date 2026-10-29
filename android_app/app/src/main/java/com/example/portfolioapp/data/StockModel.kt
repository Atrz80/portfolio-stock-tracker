package com.example.portfolioapp.data

data class Stock(
    val symbol: String,
    val name: String,
    val price: Double,
    val change_percent: Double
)

data class GeminiAnalysisResponse(
    val analysis: String,
    val model_used: String
)
