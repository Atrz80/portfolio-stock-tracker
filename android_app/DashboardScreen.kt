package com.example.portfolioapp.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.example.portfolioapp.data.Stock
import com.example.portfolioapp.network.PortfolioApiService
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen() {
    val apiService = remember { PortfolioApiService.create() }
    val scope = rememberCoroutineScope()
    
    var stocks by remember { mutableStateOf<List<Stock>>(emptyList()) }
    var analysisResult by remember { mutableStateOf<String?>(null) }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    // Load data on startup.
    LaunchedEffect(Unit) {
        try {
            stocks = apiService.getRealtimePortfolio()
        } catch (e: Exception) {
            errorMessage = "Could not connect to the backend: ${e.localizedMessage}"
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Financial Portfolio & Gemini") },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp)
        ) {
            Text("Your assets in real time", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))

            if (errorMessage != null) {
                Text(errorMessage!, color = Color.Red)
            }

            // Stock list.
            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
            ) {
                items(stocks) { stock ->
                    StockCard(stock = stock)
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Gemini AI analysis button.
            Button(
                onClick = {
                    scope.launch {
                        isLoading = true
                        errorMessage = null
                        try {
                            val response = apiService.analyzePortfolio(mapOf("stocks" to stocks))
                            analysisResult = response.analysis
                        } catch (e: Exception) {
                            errorMessage = "Gemini analysis error: ${e.localizedMessage}"
                        } finally {
                            isLoading = false
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isLoading && stocks.isNotEmpty()
            ) {
                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(24.dp), color = Color.White)
                } else {
                    Text("🤖 Analyze portfolio with Gemini AI")
                }
            }

            // Gemini result.
            if (analysisResult != null) {
                Spacer(modifier = Modifier.height(16.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Gemini analysis:", style = MaterialTheme.typography.titleSmall)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(analysisResult!, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }
    }
}

@Composable
fun StockCard(stock: Stock) {
    val isPositive = stock.change_percent >= 0
    val changeColor = if (isPositive) Color(0xFF2E7D32) else Color(0xFFC62828)

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            alignment = Alignment.CenterVertically
        ) {
            Column {
                Text(text = stock.symbol, style = MaterialTheme.typography.titleMedium)
                Text(text = stock.name, style = MaterialTheme.typography.bodySmall, color = Color.Gray)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(text = "$${stock.price}", style = MaterialTheme.typography.titleMedium)
                Text(
                    text = "${if (isPositive) "+" else ""}${stock.change_percent}%",
                    style = MaterialTheme.typography.bodyMedium,
                    color = changeColor
                )
            }
        }
    }
}
