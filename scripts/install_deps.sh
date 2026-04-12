#!/bin/bash
echo "Installing dependencies via uv..."
uv add openai numpy sympy scipy pandas matplotlib
echo "Dependencies installed."
