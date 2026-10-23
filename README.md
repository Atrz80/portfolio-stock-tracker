# 📈 Portfolio Stock Tracker

A lightweight, zero-dependency financial portfolio and asset performance dashboard built with **vanilla JavaScript**, **Chart.js**, and **SheetJS**.

Designed for mobile and desktop tracking with real-time multi-period performance metrics normalized to Euros (€).

---

## 🔒 Privacy & Architecture

This repository is strictly public for source code and user interface deployment via GitHub Pages.

**Your personal financial data is never exposed or uploaded to GitHub:**
* **Local Client-Side Processing:** Upload your local Excel file (`.xlsx`) directly in the browser interface.
* **No Backend / No Tracking:** Data is read in-memory by SheetJS and processed on your device.
* **Ignored Personal Assets:** Local spreadsheets and private configuration files are strictly excluded via `.gitignore`.

---

## 📊 Excel Template Structure

To feed the dashboard with your personal portfolio, construct an Excel sheet with the following header column names:

| Nombre | Titulos | PrecioActualEUR | InvertidoEUR | RetornoHoy | RetornoYTD | RetornoTotal | EfectivoEUR |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Vanguard FTSE All-World | 122 | 168.95 | 20900.00 | 0.05 | -0.80 | -1.38 | 23288.00 |
| iShares Semiconductors | 270 | 15.91 | 4568.00 | -0.20 | -5.10 | -5.97 | |

---

## 🚀 Features

* **Multi-period Metrics:** Filter performance seamlessly across `Hoy`, `7d`, `30d`, `3m`, `6m`, `MTD`, `YTD`, and `Desde compra`.
* **Dynamic Charts:** Area charts for trend evolution and bar charts for individual asset contribution.
* **Cash & Incurred Separation:** Pure yield calculations over invested capital without distortion from cash holdings.
* **Mobile Ready:** Fully responsive design styled after modern financial platforms.

---

## 🛠️ Usage

1. Open the public deployment link or run `index.html` locally.
2. Click on **"📊 Cargar Mi Excel Privado"**.
3. Select your local spreadsheet to visualize your updated metrics instantly.