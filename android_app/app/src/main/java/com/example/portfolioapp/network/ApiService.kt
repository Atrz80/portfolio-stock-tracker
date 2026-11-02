package com.example.portfolioapp.network

import com.example.portfolioapp.data.CatalogRefreshResponse
import com.example.portfolioapp.data.PortfolioHistory
import com.example.portfolioapp.data.Stock
import com.example.portfolioapp.data.TickerCatalog
import okhttp3.Credentials
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface PortfolioApiService {
    @GET("api/portfolio/realtime")
    suspend fun getRealtimePortfolio(@Query("provider") provider: String): List<Stock>

    @GET("api/catalog")
    suspend fun getCatalog(@Query("exchange") exchange: String): TickerCatalog

    @POST("api/catalog/refresh")
    suspend fun refreshCatalog(@Query("exchange") exchange: String): CatalogRefreshResponse

    @GET("api/portfolio/history")
    suspend fun getPortfolioHistory(
        @Query("period") period: String,
        @Query("isin") isin: String? = null
    ): PortfolioHistory

    companion object {
        // The emulator alias is only the default for local development.
        const val DEFAULT_BASE_URL = "http://10.0.2.2:8000/"

        fun create(
            baseUrl: String = DEFAULT_BASE_URL,
            username: String = "",
            password: String = ""
        ): PortfolioApiService {
            val client = OkHttpClient.Builder().addInterceptor { chain ->
                val request = chain.request().newBuilder()
                if (username.isNotBlank() && password.isNotEmpty()) {
                    request.header("Authorization", Credentials.basic(username, password))
                }
                chain.proceed(request.build())
            }.build()
            val retrofit = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
            return retrofit.create(PortfolioApiService::class.java)
        }
    }
}
