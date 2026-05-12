#!/bin/bash

# AGIA Frontend - Quick Start Script

echo "=========================================="
echo "AGIA Frontend - Quick Start"
echo "=========================================="
echo ""

# Navigate to frontend directory
cd frontend

echo "1. Installing dependencies..."
npm install

echo ""
echo "2. Starting development server..."
echo "   Frontend will be available at: http://localhost:5173"
echo ""
echo "   Press Ctrl+C to stop the server"
echo ""

npm run dev
