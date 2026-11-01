package com.example.portfolioapp.ui

import android.content.Context
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.example.portfolioapp.data.Stock
import com.example.portfolioapp.data.TickerCatalog
import com.example.portfolioapp.network.PortfolioApiService
import com.google.gson.Gson
import kotlinx.coroutines.launch

private const val PREFERENCES_NAME = "portfolio_preferences"
private const val PROVIDER_KEY = "market_data_provider"
private const val CATALOG_EXCHANGE = "US"
private const val CATALOG_KEY = "ticker_catalog_${CATALOG_EXCHANGE}_v2"
private val catalogGson = Gson()

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen() {
    val context = LocalContext.current
    val preferences = remember {
        context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
    }
    val apiService = remember { PortfolioApiService.create() }
    val scope = rememberCoroutineScope()

    var provider by remember {
        mutableStateOf(preferences.getString(PROVIDER_KEY, "yahoo") ?: "yahoo")
    }
    val cachedCatalogResult = remember {
        preferences.getString(CATALOG_KEY, null)?.let { json ->
            runCatching {
                requireNotNull(catalogGson.fromJson(json, TickerCatalog::class.java)) {
                    "La caché está vacía"
                }
            }
        }
    }
    var catalog by remember { mutableStateOf(cachedCatalogResult?.getOrNull()) }
    var stocks by remember { mutableStateOf<List<Stock>>(emptyList()) }
    var catalogSearch by remember { mutableStateOf("") }
    var providerMenuExpanded by remember { mutableStateOf(false) }
    var isLoadingPrices by remember { mutableStateOf(false) }
    var isLoadingCatalog by remember { mutableStateOf(false) }
    var priceError by remember { mutableStateOf<String?>(null) }
    var catalogError by remember {
        mutableStateOf(
            cachedCatalogResult?.exceptionOrNull()?.let {
                "No se pudo leer la caché local: ${it.localizedMessage ?: "datos no válidos"}. Actualízala para reemplazarla."
            }
        )
    }

    suspend fun refreshPrices() {
        isLoadingPrices = true
        priceError = null
        try {
            stocks = apiService.getRealtimePortfolio(provider)
        } catch (e: Exception) {
            priceError = "No se pudieron cargar los precios: ${e.localizedMessage ?: "error de conexión"}"
        } finally {
            isLoadingPrices = false
        }
    }

    fun saveCatalog(updatedCatalog: TickerCatalog) {
        catalog = updatedCatalog
        preferences.edit().putString(CATALOG_KEY, catalogGson.toJson(updatedCatalog)).apply()
    }

    LaunchedEffect(Unit) {
        refreshPrices()
    }

    val catalogEntries = catalog?.symbols.orEmpty().filter { entry ->
        catalogSearch.isBlank() ||
            entry.symbol.contains(catalogSearch, ignoreCase = true) ||
            entry.displaySymbol.contains(catalogSearch, ignoreCase = true) ||
            entry.description.contains(catalogSearch, ignoreCase = true) ||
            entry.type.contains(catalogSearch, ignoreCase = true) ||
            entry.exchange.contains(catalogSearch, ignoreCase = true)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Portfolio financiero") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(horizontal = 16.dp, vertical = 8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Box {
                    OutlinedButton(onClick = { providerMenuExpanded = true }) {
                        Text("Proveedor: ${provider.uppercase()}")
                    }
                    DropdownMenu(
                        expanded = providerMenuExpanded,
                        onDismissRequest = { providerMenuExpanded = false }
                    ) {
                        listOf("yahoo", "finnhub").forEach { option ->
                            DropdownMenuItem(
                                text = { Text(option.uppercase()) },
                                onClick = {
                                    provider = option
                                    preferences.edit().putString(PROVIDER_KEY, option).apply()
                                    providerMenuExpanded = false
                                }
                            )
                        }
                    }
                }
                Button(
                    onClick = { scope.launch { refreshPrices() } },
                    enabled = !isLoadingPrices
                ) {
                    if (isLoadingPrices) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(18.dp),
                            strokeWidth = 2.dp
                        )
                    } else {
                        Text("Refrescar precios")
                    }
                }
            }

            priceError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            Text("Portfolio en tiempo real", style = MaterialTheme.typography.titleMedium)
            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
            ) {
                items(stocks) { stock ->
                    StockCard(stock = stock)
                }
                if (stocks.isEmpty() && !isLoadingPrices) {
                    item { Text("No hay posiciones disponibles.") }
                }
            }

            Divider()
            Text("Catálogo local · $CATALOG_EXCHANGE", style = MaterialTheme.typography.titleMedium)
            Text(
                catalog?.updatedAt?.let { "Actualizado: $it" } ?: "Sin catálogo guardado",
                style = MaterialTheme.typography.bodySmall
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedButton(
                    onClick = {
                        scope.launch {
                            isLoadingCatalog = true
                            catalogError = null
                            try {
                                saveCatalog(apiService.getCatalog(CATALOG_EXCHANGE))
                            } catch (e: Exception) {
                                catalogError = "No se pudo cargar el catálogo: ${e.localizedMessage ?: "error de conexión"}"
                            } finally {
                                isLoadingCatalog = false
                            }
                        }
                    },
                    enabled = !isLoadingCatalog,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Cargar catálogo")
                }
                Button(
                    onClick = {
                        scope.launch {
                            isLoadingCatalog = true
                            catalogError = null
                            try {
                                val response = apiService.refreshCatalog(CATALOG_EXCHANGE)
                                check(response.status == "success") {
                                    "Respuesta inesperada: ${response.status}"
                                }
                                saveCatalog(response.toCatalog())
                            } catch (e: Exception) {
                                catalogError = "No se pudo actualizar el catálogo: ${e.localizedMessage ?: "error de conexión"}"
                            } finally {
                                isLoadingCatalog = false
                            }
                        }
                    },
                    enabled = !isLoadingCatalog,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Actualizar catálogo")
                }
            }
            catalogError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            OutlinedTextField(
                value = catalogSearch,
                onValueChange = { catalogSearch = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Buscar símbolo, nombre, tipo o exchange (caché local)") },
                singleLine = true
            )
            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 120.dp)
            ) {
                items(catalogEntries) { entry ->
                    Column(modifier = Modifier.padding(vertical = 4.dp)) {
                        Text(
                            text = "${entry.displaySymbol}  •  ${entry.symbol}",
                            style = MaterialTheme.typography.bodyMedium
                        )
                        Text(
                            text = "${entry.description}  •  ${entry.type}  •  ${entry.exchange}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                if (catalog != null && catalogEntries.isEmpty()) {
                    item { Text("No hay coincidencias en la caché.") }
                }
            }
            Text(
                "Análisis no disponible: el backend no expone /api/gemini/analyze.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
fun StockCard(stock: Stock) {
    val dailyChange = stock.changePercent
    val changeColor = if ((dailyChange ?: 0.0) >= 0) Color(0xFF2E7D32) else Color(0xFFC62828)

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
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(stock.name, style = MaterialTheme.typography.titleMedium)
                Text(
                    "${stock.ticker}  •  ${stock.marketSymbol ?: "sin símbolo"}",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.Gray
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text("${stock.price} €", style = MaterialTheme.typography.titleMedium)
                dailyChange?.let {
                    Text(
                        "${if (it >= 0) "+" else ""}$it%",
                        style = MaterialTheme.typography.bodyMedium,
                        color = changeColor
                    )
                }
            }
        }
    }
}
