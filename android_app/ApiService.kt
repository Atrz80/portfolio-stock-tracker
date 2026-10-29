package com.example.portfolioapp.network

import com.example.portfolioapp.data.GeminiAnalysisResponse
import com.example.portfolioapp.data.Stock
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface PortfolioApiService {
    @GET("api/portfolio/realtime")
    suspend fun getRealtimePortfolio(): List<Stock>

    @POST("api/gemini/analyze")
    suspend fun analyzePortfolio(@Body stocks: Map<String, List<Stock>>): GeminiAnalysisResponse

    companion object {
        // En emulador Android, localhost del PC es 10.0.2.2
        private const val BASE_URL = "http://10.0.2.2:8000/"

        fun create(): PortfolioApiService {
            val retrofit = Retrofit.Builder()
                .baseUrl(BASE_URL)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
            return retrofit.create(PortfolioApiService::class.java)
        }
    }
}
