package com.example.portfolioapp.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp

@Composable
fun PriceChartCard(stockSymbol: String, historicalPrices: List<Float>) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .height(180.dp)
            .padding(vertical = 8.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp)
        ) {
            Text(
                text = "Evolución en Tiempo Real: $stockSymbol",
                style = MaterialTheme.typography.titleSmall
            )
            Spacer(modifier = Modifier.height(8.dp))

            if (historicalPrices.size < 2) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = androidx.compose.ui.Alignment.Center
                ) {
                    Text("Cargando datos de gráfico...", color = Color.Gray)
                }
            } else {
                SimpleLineChart(prices = historicalPrices)
            }
        }
    }
}

@Composable
fun SimpleLineChart(prices: List<Float>) {
    val lineColor = MaterialTheme.colorScheme.primary
    val primaryContainer = MaterialTheme.colorScheme.primaryContainer

    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(100.dp)
    ) {
        val width = size.width
        val height = size.height

        val maxPrice = prices.maxOrNull() ?: 1f
        val minPrice = prices.minOrNull() ?: 0f
        val priceRange = if (maxPrice - minPrice == 0f) 1f else maxPrice - minPrice

        val stepX = width / (prices.size - 1)

        val path = Path()
        val fillPath = Path()

        fillPath.moveTo(0f, height)

        prices.forEachIndexed { index, price ->
            val x = index * stepX
            val y = height - ((price - minPrice) / priceRange) * (height - 20f) - 10f

            if (index == 0) {
                path.moveTo(x, y)
                fillPath.lineTo(x, y)
            } else {
                path.lineTo(x, y)
                fillPath.lineTo(x, y)
            }
        }

        fillPath.lineTo(width, height)
        fillPath.close()

        // Dibujar área sombreada bajo la línea
        drawPath(
            path = fillPath,
            brush = Brush.verticalGradient(
                colors = listOf(primaryContainer.copy(alpha = 0.5f), Color.Transparent),
                startY = 0f,
                endY = height
            )
        )

        // Dibujar línea del gráfico
        drawPath(
            path = path,
            color = lineColor,
            style = Stroke(width = 3.dp.toPx())
        )
    }
}
