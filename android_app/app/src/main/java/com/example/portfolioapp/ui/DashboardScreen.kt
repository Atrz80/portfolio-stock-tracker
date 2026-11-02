package com.example.portfolioapp.ui

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.example.portfolioapp.data.CatalogSymbol
import com.example.portfolioapp.data.HistoryPoint
import com.example.portfolioapp.data.PortfolioHistory
import com.example.portfolioapp.data.Stock
import com.example.portfolioapp.data.TickerCatalog
import com.example.portfolioapp.network.PortfolioApiService
import com.google.gson.Gson
import kotlinx.coroutines.launch
import java.net.URI
import java.text.NumberFormat
import java.text.SimpleDateFormat
import java.util.Currency
import java.util.Date
import java.util.Locale
import kotlin.math.abs

private const val PREFERENCES_NAME = "portfolio_preferences"
private const val PROVIDER_KEY = "market_data_provider"
private const val SERVER_URL_KEY = "market_data_server_url"
private const val CATALOG_EXCHANGE = "US"
private const val CATALOG_KEY = "ticker_catalog_${CATALOG_EXCHANGE}_v2"
private val catalogGson = Gson()
private val historyPeriods = listOf("1d", "1w", "1m", "1y", "ytd", "max")

private fun euro(value: Double): String =
    NumberFormat.getCurrencyInstance(Locale.UK).apply {
        currency = Currency.getInstance("EUR")
        maximumFractionDigits = 2
    }.format(value)

private fun percent(value: Double): String =
    "${if (value > 0) "+" else ""}${"%.2f".format(Locale.UK, value)}%"

private fun periodLabel(period: String): String = when (period) {
    "1d" -> "1D"
    "1w" -> "1W"
    "1m" -> "1M"
    "1y" -> "1Y"
    "ytd" -> "YTD"
    else -> "ALL"
}

private fun dateLabel(timestamp: Long, includeTime: Boolean = false): String {
    val pattern = if (includeTime) "dd MMM, HH:mm" else "dd MMM yyyy"
    return SimpleDateFormat(pattern, Locale.UK).format(Date(timestamp * 1000))
}

private fun normalizeServerUrl(rawValue: String): String {
    val value = rawValue.trim().let { if (it.endsWith("/")) it else "$it/" }
    val uri = URI(value)
    require(uri.scheme == "http" || uri.scheme == "https") {
        "Use an address beginning with http:// or https://."
    }
    require(!uri.host.isNullOrBlank() && uri.userInfo == null &&
        (uri.path.isNullOrEmpty() || uri.path == "/") &&
        uri.query == null && uri.fragment == null
    ) {
        "Enter only the server address, for example http://192.168.1.20:8000."
    }
    return value
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen() {
    val context = LocalContext.current
    val preferences = remember {
        context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
    }
    val scope = rememberCoroutineScope()
    var serverUrl by remember {
        mutableStateOf(
            preferences.getString(SERVER_URL_KEY, PortfolioApiService.DEFAULT_BASE_URL)
                ?: PortfolioApiService.DEFAULT_BASE_URL
        )
    }
    var apiService by remember(serverUrl) { mutableStateOf(PortfolioApiService.create(serverUrl)) }
    var provider by remember {
        mutableStateOf(preferences.getString(PROVIDER_KEY, "yahoo") ?: "yahoo")
    }
    val cachedCatalogResult = remember {
        preferences.getString(CATALOG_KEY, null)?.let { json ->
            runCatching {
                requireNotNull(catalogGson.fromJson(json, TickerCatalog::class.java)) {
                    "The saved catalog is empty."
                }
            }
        }
    }
    var catalog by remember { mutableStateOf(cachedCatalogResult?.getOrNull()) }
    var stocks by remember { mutableStateOf<List<Stock>>(emptyList()) }
    var selectedPeriod by remember { mutableStateOf("1d") }
    var selectedAsset by remember { mutableStateOf<Stock?>(null) }
    var isSettingsOpen by remember { mutableStateOf(false) }
    var isLoadingPrices by remember { mutableStateOf(false) }
    var isLoadingCatalog by remember { mutableStateOf(false) }
    var priceError by remember { mutableStateOf<String?>(null) }
    var catalogError by remember {
        mutableStateOf(
            cachedCatalogResult?.exceptionOrNull()?.let {
                "Could not read the local catalog: ${it.localizedMessage ?: "invalid data"}. Refresh it to replace it."
            }
        )
    }

    suspend fun refreshPrices() {
        isLoadingPrices = true
        priceError = null
        try {
            stocks = apiService.getRealtimePortfolio(provider)
        } catch (error: Exception) {
            priceError = "Could not load prices: ${error.localizedMessage ?: "connection error"}"
        } finally {
            isLoadingPrices = false
        }
    }

    fun saveCatalog(updatedCatalog: TickerCatalog) {
        catalog = updatedCatalog
        preferences.edit().putString(CATALOG_KEY, catalogGson.toJson(updatedCatalog)).apply()
    }

    LaunchedEffect(apiService) {
        refreshPrices()
    }

    val portfolioValue = stocks.sumOf { it.value }
    val portfolioGain = stocks.sumOf { it.gain }
    val investedValue = portfolioValue - portfolioGain
    val portfolioGainPct = if (investedValue != 0.0) portfolioGain / investedValue * 100 else 0.0
    val catalogEntries = catalog?.symbols.orEmpty()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Portfolio Tracker", fontWeight = FontWeight.Bold)
                        Text(
                            "${stocks.size} positions · ${provider.uppercase(Locale.UK)}",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                },
                actions = {
                    TextButton(onClick = { scope.launch { refreshPrices() } }, enabled = !isLoadingPrices) {
                        Text(if (isLoadingPrices) "Loading…" else "Refresh")
                    }
                    TextButton(onClick = { isSettingsOpen = true }) {
                        Text("☰  Settings")
                    }
                }
            )
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                PortfolioSummaryCard(
                    value = portfolioValue,
                    gain = portfolioGain,
                    gainPct = portfolioGainPct,
                    assetCount = stocks.size
                )
            }
            item {
                HistorySection(
                    apiService = apiService,
                    period = selectedPeriod,
                    onPeriodSelected = { selectedPeriod = it }
                )
            }
            item {
                Text("Live positions", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            }
            priceError?.let { message ->
                item { ErrorCard(message) }
            }
            if (isLoadingPrices && stocks.isEmpty()) {
                item {
                    Box(Modifier.fillMaxWidth().padding(24.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                }
            } else if (stocks.isEmpty()) {
                item { Text("No portfolio positions are available.", color = MaterialTheme.colorScheme.onSurfaceVariant) }
            } else {
                items(stocks, key = { it.ticker }) { stock ->
                    StockCard(stock = stock, onClick = { selectedAsset = stock })
                }
            }
        }
    }

    if (isSettingsOpen) {
        SettingsDialog(
            context = context,
            serverUrl = serverUrl,
            provider = provider,
            catalog = catalog,
            catalogError = catalogError,
            isLoadingCatalog = isLoadingCatalog,
            onDismiss = { isSettingsOpen = false },
            onSaveServerUrl = { input ->
                val normalized = normalizeServerUrl(input)
                serverUrl = normalized
                preferences.edit().putString(SERVER_URL_KEY, normalized).apply()
            },
            onProviderSelected = { selected ->
                provider = selected
                preferences.edit().putString(PROVIDER_KEY, selected).apply()
                scope.launch { refreshPrices() }
            },
            onLoadCatalog = {
                scope.launch {
                    isLoadingCatalog = true
                    catalogError = null
                    try {
                        saveCatalog(apiService.getCatalog(CATALOG_EXCHANGE))
                    } catch (error: Exception) {
                        catalogError = "Could not load the catalog: ${error.localizedMessage ?: "connection error"}"
                    } finally {
                        isLoadingCatalog = false
                    }
                }
            },
            onRefreshCatalog = {
                scope.launch {
                    isLoadingCatalog = true
                    catalogError = null
                    try {
                        val response = apiService.refreshCatalog(CATALOG_EXCHANGE)
                        check(response.status == "success") {
                            "Unexpected catalog response: ${response.status}"
                        }
                        saveCatalog(response.toCatalog())
                    } catch (error: Exception) {
                        catalogError = "Could not refresh the catalog: ${error.localizedMessage ?: "connection error"}"
                    } finally {
                        isLoadingCatalog = false
                    }
                }
            },
            onClearCatalog = {
                catalog = null
                preferences.edit().remove(CATALOG_KEY).apply()
            }
        )
    }

    selectedAsset?.let { stock ->
        AssetHistorySheet(
            stock = stock,
            apiService = apiService,
            onDismiss = { selectedAsset = null }
        )
    }
}

@Composable
private fun PortfolioSummaryCard(value: Double, gain: Double, gainPct: Double, assetCount: Int) {
    Card(shape = RoundedCornerShape(20.dp)) {
        Column(Modifier.fillMaxWidth().padding(18.dp)) {
            Text("Portfolio value", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(euro(value), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column {
                    Text("All-time gain / loss", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    GainText(gain, percent(gainPct))
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text("Positions", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(assetCount.toString(), fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}

@Composable
private fun HistorySection(
    apiService: PortfolioApiService,
    period: String,
    onPeriodSelected: (String) -> Unit
) {
    var history by remember(apiService, period) { mutableStateOf<PortfolioHistory?>(null) }
    var isLoading by remember(apiService, period) { mutableStateOf(true) }
    var errorMessage by remember(apiService, period) { mutableStateOf<String?>(null) }

    LaunchedEffect(apiService, period) {
        isLoading = true
        errorMessage = null
        try {
            history = apiService.getPortfolioHistory(period)
        } catch (error: Exception) {
            history = null
            errorMessage = error.localizedMessage ?: "Historical data is unavailable."
        } finally {
            isLoading = false
        }
    }

    Card(shape = RoundedCornerShape(20.dp)) {
        Column(Modifier.fillMaxWidth().padding(16.dp)) {
            Text("Portfolio history", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(
                "Market performance and estimated investment gain",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            PeriodSelector(period, onPeriodSelected)
            when {
                isLoading -> Box(Modifier.fillMaxWidth().height(170.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
                history != null -> {
                    val loaded = history!!
                    ChartSummary(
                        title = "Market value · ${periodLabel(period)}",
                        primaryValue = euro(loaded.summary.endValue),
                        change = loaded.summary.change,
                        changePct = loaded.summary.changePct
                    )
                    InteractiveHistoryChart(loaded.points, Modifier.fillMaxWidth().height(180.dp))
                    Text(
                        "${dateLabel(loaded.points.first().timestamp)} — ${dateLabel(loaded.points.last().timestamp)}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Divider(Modifier.padding(vertical = 10.dp))
                    SummaryLine(
                        "Period start",
                        euro(loaded.summary.startValue),
                        "Period end ${euro(loaded.summary.endValue)}"
                    )
                    SummaryLine("Estimated investment gain", loaded.investmentSummary.gain, percent(loaded.investmentSummary.gainPct))
                    SummaryLine(
                        "Period high / low",
                        loaded.summary.high,
                        "${dateLabel(loaded.summary.highTimestamp)} | ${euro(loaded.summary.low)} · ${dateLabel(loaded.summary.lowTimestamp)}"
                    )
                    Text(
                        loaded.note,
                        modifier = Modifier.padding(top = 8.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                else -> Text(
                    "Could not load history: ${errorMessage ?: "Unknown error"}",
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }
    }
}

@Composable
private fun PeriodSelector(period: String, onSelected: (String) -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        historyPeriods.chunked(3).forEach { rowPeriods ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                rowPeriods.forEach { option ->
                    FilterChip(
                        selected = period == option,
                        onClick = { onSelected(option) },
                        label = { Text(periodLabel(option)) }
                    )
                }
            }
        }
    }
}

@Composable
private fun ChartSummary(title: String, primaryValue: String, change: Double, changePct: Double) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Bottom) {
        Column {
            Text(title, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(primaryValue, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        }
        GainText(change, percent(changePct))
    }
}

@Composable
private fun InteractiveHistoryChart(
    points: List<HistoryPoint>,
    modifier: Modifier = Modifier,
    includeZero: Boolean = false
) {
    var selectedIndex by remember(points) { mutableStateOf<Int?>(null) }
    val lineColor = MaterialTheme.colorScheme.primary
    val dotColor = MaterialTheme.colorScheme.tertiary

    if (points.size < 2) {
        Box(modifier, contentAlignment = Alignment.Center) {
            Text("Not enough historical points to draw a chart.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        return
    }

    Canvas(
        modifier = modifier
            .padding(vertical = 10.dp)
            .pointerInput(points) {
                detectTapGestures { position ->
                    val normalized = (position.x / size.width).coerceIn(0f, 1f)
                    selectedIndex = (normalized * (points.size - 1)).toInt()
                }
            }
            .pointerInput(points) {
                detectDragGestures(
                    onDragStart = { position ->
                        val normalized = (position.x / size.width).coerceIn(0f, 1f)
                        selectedIndex = (normalized * (points.size - 1)).toInt()
                    },
                    onDrag = { change, _ ->
                        val normalized = (change.position.x / size.width).coerceIn(0f, 1f)
                        selectedIndex = (normalized * (points.size - 1)).toInt()
                        change.consume()
                    }
                )
            }
    ) {
        val padding = 12.dp.toPx()
        val values = points.map { it.value }
        val minValue = (values.minOrNull() ?: 0.0).let { if (includeZero) minOf(it, 0.0) else it }
        val maxValue = (values.maxOrNull() ?: 0.0).let { if (includeZero) maxOf(it, 0.0) else it }
        val range = (maxValue - minValue).takeIf { it > 0.0 } ?: 1.0
        val graphWidth = size.width - padding * 2
        val graphHeight = size.height - padding * 2
        val baselineY = if (maxValue == minValue) {
            size.height / 2f
        } else if (includeZero) {
            size.height - padding - ((0.0 - minValue) / range * graphHeight).toFloat()
        } else {
            size.height - padding
        }
        val coordinates = points.mapIndexed { index, point ->
            Offset(
                x = padding + graphWidth * index / (points.size - 1),
                y = if (maxValue == minValue) size.height / 2f
                else size.height - padding - ((point.value - minValue) / range * graphHeight).toFloat()
            )
        }

        val area = Path().apply {
            moveTo(coordinates.first().x, baselineY)
            coordinates.forEach { lineTo(it.x, it.y) }
            lineTo(coordinates.last().x, baselineY)
            close()
        }
        drawPath(area, color = lineColor.copy(alpha = 0.14f))
        if (includeZero) {
            drawLine(
                color = lineColor.copy(alpha = 0.35f),
                start = Offset(padding, baselineY),
                end = Offset(size.width - padding, baselineY),
                strokeWidth = 1.dp.toPx()
            )
        }
        val line = Path().apply {
            coordinates.forEachIndexed { index, coordinate ->
                if (index == 0) moveTo(coordinate.x, coordinate.y) else lineTo(coordinate.x, coordinate.y)
            }
        }
        drawPath(line, color = lineColor, style = Stroke(width = 3.dp.toPx()))

        selectedIndex?.let { index ->
            val point = coordinates[index.coerceIn(coordinates.indices)]
            drawLine(
                color = dotColor.copy(alpha = 0.65f),
                start = Offset(point.x, 0f),
                end = Offset(point.x, size.height),
                strokeWidth = 1.dp.toPx()
            )
            drawCircle(color = dotColor, radius = 5.dp.toPx(), center = point)
        }
    }

    Text(
        "Tap or drag across the chart to inspect a value.",
        modifier = Modifier.fillMaxWidth(),
        style = MaterialTheme.typography.labelSmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )
    selectedIndex?.let { index ->
        val point = points[index.coerceIn(points.indices)]
        Text(
            "${dateLabel(point.timestamp, includeTime = true)}  ·  ${euro(point.value)}",
            modifier = Modifier.fillMaxWidth(),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun StockCard(stock: Stock, onClick: () -> Unit) {
    val colors = listOf(
        Color(0xFF22D3EE), Color(0xFFA78BFA), Color(0xFFF472B6), Color(0xFFFBBF24),
        Color(0xFF34D399), Color(0xFFFB7185), Color(0xFF60A5FA), Color(0xFFC084FC)
    )
    val accentIndex = ((stock.marketSymbol ?: stock.ticker).hashCode() % colors.size + colors.size) % colors.size
    val accent = colors[accentIndex]
    val tickerParts = stock.ticker.split("•")
    val isin = tickerParts.first().trim()
    val label = tickerParts.getOrNull(1)?.trim().orEmpty()
    val dailyChange = stock.changePercent ?: 0.0

    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = RoundedCornerShape(18.dp)
    ) {
        Column(Modifier.fillMaxWidth().padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(
                    modifier = Modifier.size(42.dp).background(accent.copy(alpha = 0.14f), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        stock.init.ifBlank { stock.name.split(Regex("\\s+")).take(2).joinToString("") { it.take(1) } }
                            .take(3).uppercase(Locale.UK),
                        color = accent,
                        fontWeight = FontWeight.Bold
                    )
                }
                Column(Modifier.weight(1f)) {
                    Text(stock.name, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(
                        "${stock.badge.ifBlank { "Asset" }} · ${stock.marketSymbol ?: isin}${if (label.isNotBlank()) " · $label" else ""}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(euro(stock.value), fontWeight = FontWeight.Bold)
                    Text(
                        "${stock.shares.toDisplayNumber()} shares · ${stock.price.toDisplayNumber()} EUR",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            Divider(Modifier.padding(vertical = 10.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text("Unrealized gain / loss", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    GainText(stock.gain, percent(stock.gainPct))
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        "↗ ${percent(dailyChange)}",
                        color = if (dailyChange >= 0) Color(0xFF34D399) else Color(0xFFFB7185),
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        "${stock.dataSource ?: "Yahoo Finance"} · ${if (stock.dataStatus == "realtime_push") "push" else "snapshot"}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AssetHistorySheet(
    stock: Stock,
    apiService: PortfolioApiService,
    onDismiss: () -> Unit
) {
    var period by remember(stock.ticker) { mutableStateOf("1d") }
    var investmentView by remember(stock.ticker) { mutableStateOf(false) }
    var history by remember(apiService, stock.ticker, period) { mutableStateOf<PortfolioHistory?>(null) }
    var loading by remember(apiService, stock.ticker, period) { mutableStateOf(true) }
    var errorMessage by remember(apiService, stock.ticker, period) { mutableStateOf<String?>(null) }
    val isin = stock.ticker.substringBefore("•").trim()

    LaunchedEffect(apiService, isin, period) {
        loading = true
        errorMessage = null
        try {
            history = apiService.getPortfolioHistory(period, isin)
        } catch (error: Exception) {
            history = null
            errorMessage = error.localizedMessage ?: "Asset history is unavailable."
        } finally {
            loading = false
        }
    }

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            Modifier.fillMaxWidth().fillMaxHeight(0.88f)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp)
        ) {
            Text(stock.name, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text(
                "${stock.marketSymbol ?: isin} · ${stock.shares.toDisplayNumber()} shares",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            PeriodSelector(period, onSelected = { period = it })
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(selected = !investmentView, onClick = { investmentView = false }, label = { Text("Product price") })
                FilterChip(selected = investmentView, onClick = { investmentView = true }, label = { Text("My investment") })
            }
            when {
                loading -> Box(Modifier.fillMaxWidth().height(220.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
                history != null -> {
                    val loaded = history!!
                    val points = if (investmentView) loaded.investmentPoints.orEmpty() else loaded.points
                    val finalPoint = points.lastOrNull()
                    if (finalPoint == null) {
                        Text("No history is available for this chart.", color = MaterialTheme.colorScheme.error)
                    } else {
                        val change = if (investmentView && points.size > 1) {
                            finalPoint.value - points.first().value
                        } else loaded.summary.change
                        val changePct = if (investmentView) {
                            loaded.asset?.periodGainPct ?: 0.0
                        } else loaded.summary.changePct
                        ChartSummary(
                            title = if (investmentView) "Estimated investment P/L" else "Price per share · EUR",
                            primaryValue = euro(if (investmentView) finalPoint.value else loaded.summary.endValue),
                            change = change,
                            changePct = changePct
                        )
                        InteractiveHistoryChart(
                            points,
                            Modifier.fillMaxWidth().height(190.dp),
                            includeZero = investmentView
                        )
                        loaded.asset?.let { asset ->
                            SummaryLine("Position value", euro(asset.lastValue), "${asset.shares.toDisplayNumber()} shares")
                            SummaryLine("Cost basis", euro(asset.costBasis), "Estimated from recorded purchases")
                            SummaryLine("Unrealized gain / loss", asset.unrealizedGain, percent(asset.unrealizedGainPct))
                        }
                        Text(
                            "Investment history estimates each share's cost from your recorded purchases and average cost basis; exact per-purchase prices may not be available.",
                            modifier = Modifier.padding(top = 12.dp, bottom = 24.dp),
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                else -> Text(
                    "Could not load asset history: ${errorMessage ?: "Unknown error"}",
                    color = MaterialTheme.colorScheme.error
                )
            }
        }
    }
}

@Composable
private fun SettingsDialog(
    context: Context,
    serverUrl: String,
    provider: String,
    catalog: TickerCatalog?,
    catalogError: String?,
    isLoadingCatalog: Boolean,
    onDismiss: () -> Unit,
    onSaveServerUrl: (String) -> Unit,
    onProviderSelected: (String) -> Unit,
    onLoadCatalog: () -> Unit,
    onRefreshCatalog: () -> Unit,
    onClearCatalog: () -> Unit
) {
    var serverInput by remember(serverUrl) { mutableStateOf(serverUrl) }
    var search by remember { mutableStateOf("") }
    var dashboardError by remember { mutableStateOf<String?>(null) }
    var serverAddressStatus by remember { mutableStateOf<String?>(null) }
    val matchingEntries = catalog?.symbols.orEmpty().filter {
        search.isBlank() || it.matches(search)
    }.take(100)

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Settings") },
        text = {
            Column(
                Modifier.fillMaxWidth().heightIn(max = 560.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text("Market data", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("yahoo", "finnhub").forEach { option ->
                        FilterChip(
                            selected = provider == option,
                            onClick = { onProviderSelected(option) },
                            label = { Text(option.replaceFirstChar { it.uppercase(Locale.UK) }) }
                        )
                    }
                }
                Text(
                    "Yahoo sends push updates when market ticks arrive. Finnhub updates when you refresh prices. Neither provider uses a fixed polling interval.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Divider()
                Text("Backend address", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                OutlinedTextField(
                    value = serverInput,
                    onValueChange = { serverInput = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Server URL") },
                    supportingText = { Text("On your phone, use the PC's Wi-Fi address, e.g. http://192.168.1.20:8000/") },
                    singleLine = true
                )
                OutlinedButton(
                    onClick = {
                        try {
                            onSaveServerUrl(serverInput)
                            serverAddressStatus = "Server address saved. Reconnecting…"
                        } catch (error: Exception) {
                            serverAddressStatus = error.message ?: "Invalid server address."
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Save server address")
                }
                serverAddressStatus?.let {
                    Text(
                        it,
                        color = if (it.startsWith("Server address saved")) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
                Divider()
                Text("Ticker catalog · $CATALOG_EXCHANGE", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                Text(
                    catalog?.updatedAt?.let { "Last updated: $it" } ?: "No catalog saved on this device.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = onLoadCatalog, enabled = !isLoadingCatalog, modifier = Modifier.weight(1f)) {
                        Text("Load saved")
                    }
                    Button(onClick = onRefreshCatalog, enabled = !isLoadingCatalog, modifier = Modifier.weight(1f)) {
                        Text(if (isLoadingCatalog) "Loading…" else "Refresh")
                    }
                }
                catalogError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
                catalog?.let {
                    OutlinedTextField(
                        value = search,
                        onValueChange = { search = it },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("Search cached catalog") },
                        singleLine = true
                    )
                    matchingEntries.forEach { entry -> CatalogEntryRow(entry) }
                    if (matchingEntries.isEmpty()) {
                        Text("No matching symbols in the saved catalog.", style = MaterialTheme.typography.bodySmall)
                    }
                    TextButton(onClick = onClearCatalog) { Text("Clear local catalog cache") }
                }
                Divider()
                Text(
                    "Connection note: on a real phone, keep the PC dashboard server running and connect both devices to the same trusted Wi-Fi. The local API has no login; do not expose it on public Wi-Fi.",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                OutlinedButton(
                    onClick = {
                        try {
                            context.startActivity(
                                Intent(Intent.ACTION_VIEW, Uri.parse("${serverUrl.trimEnd('/')}/dashboard"))
                            )
                            dashboardError = null
                        } catch (error: Exception) {
                            dashboardError = "Could not open the web dashboard: ${error.localizedMessage ?: "no browser is available"}"
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Open full web dashboard")
                }
                dashboardError?.let {
                    Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Done") } }
    )
}

@Composable
private fun CatalogEntryRow(entry: CatalogSymbol) {
    Column(Modifier.fillMaxWidth().padding(vertical = 3.dp)) {
        Text("${entry.displaySymbol} · ${entry.symbol}", fontWeight = FontWeight.SemiBold)
        Text(
            "${entry.description} · ${entry.type} · ${entry.exchange}",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

private fun CatalogSymbol.matches(query: String): Boolean =
    symbol.contains(query, ignoreCase = true) ||
        displaySymbol.contains(query, ignoreCase = true) ||
        description.contains(query, ignoreCase = true) ||
        type.contains(query, ignoreCase = true) ||
        exchange.contains(query, ignoreCase = true)

@Composable
private fun SummaryLine(label: String, value: Double, detail: String) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Column(horizontalAlignment = Alignment.End) {
            Text(euro(value), fontWeight = FontWeight.SemiBold)
            Text(detail, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun SummaryLine(label: String, value: String, detail: String) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Column(horizontalAlignment = Alignment.End) {
            Text(value, fontWeight = FontWeight.SemiBold)
            Text(detail, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun GainText(value: Double, detail: String) {
    Text(
        "${if (value >= 0) "+" else "−"}${euro(abs(value))} · $detail",
        color = if (value >= 0) Color(0xFF34D399) else Color(0xFFFB7185),
        fontWeight = FontWeight.SemiBold
    )
}

@Composable
private fun ErrorCard(message: String) {
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
        shape = RoundedCornerShape(14.dp)
    ) {
        Text(
            message,
            Modifier.fillMaxWidth().padding(12.dp),
            color = MaterialTheme.colorScheme.onErrorContainer,
            style = MaterialTheme.typography.bodySmall
        )
    }
}

private fun Double.toDisplayNumber(): String =
    NumberFormat.getNumberInstance(Locale.UK).apply { maximumFractionDigits = 4 }.format(this)
