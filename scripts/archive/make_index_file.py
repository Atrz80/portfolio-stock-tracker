import os

html_part1 = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portfolio Stock Tracker - Google Profile & Live Data</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        .phone-frame { width: 380px; height: 780px; background: #111827; border: 12px solid #1f2937; border-radius: 40px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7); overflow: hidden; display: flex; flex-direction: column; position: relative; margin: 0 auto; }
        .phone-screen { flex: 1; overflow-y: auto; background: #0b0f19; color: #f3f4f6; padding: 16px; }
        .phone-notch { position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 140px; height: 22px; background: #1f2937; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; z-index: 50; }
    </style>
</head>
<body class="bg-gray-950 text-gray-100 min-h-screen flex flex-col font-sans">
    <header class="bg-gray-900 border-b border-gray-800 p-4 shadow-md flex flex-wrap justify-between items-center gap-4">
        <div class="flex items-center space-x-3">
            <div class="bg-indigo-600 p-2.5 rounded-xl text-white font-bold text-xl shadow-lg"><i class="fa-solid fa-chart-pie"></i></div>
            <div>
                <h1 class="text-xl font-bold tracking-tight">Portfolio Stock Tracker</h1>
                <p class="text-xs text-gray-400">Google Profile Sync | Real-time JSON Portfolio</p>
            </div>
        </div>
        <div class="flex items-center space-x-3">
            <div id="google-auth-container">
                <button onclick="loginWithGoogle()" id="google-login-btn" class="px-4 py-2 bg-white text-gray-900 hover:bg-gray-100 text-sm font-semibold rounded-lg transition shadow flex items-center gap-2">
                    <i class="fa-brands fa-google text-red-500"></i> Sign in with Google
                </button>
            </div>
            <button onclick="setViewMode('desktop')" id="btn-desktop" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-sm font-semibold rounded-lg transition shadow"><i class="fa-solid fa-desktop mr-2"></i> Desktop</button>
            <button onclick="setViewMode('mobile')" id="btn-mobile" class="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-sm font-semibold rounded-lg transition border border-gray-700"><i class="fa-solid fa-mobile-screen mr-2"></i> Mobile APK</button>
        </div>
    </header>
"""
