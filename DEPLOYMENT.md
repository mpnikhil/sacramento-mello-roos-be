# Deployment Guide - Sacramento Mello Roos Tax API

This guide covers deploying the Playwright-based property tax scraper to **Render.com** using their free tier.

## 🎯 Render.com Deployment (FREE)

### Why Render?
- ✅ **750 hours/month free** (enough for 24/7 service)
- ✅ Supports Docker & Playwright
- ✅ Auto-sleep after 15 min inactivity (wakes in ~30 seconds)
- ✅ Easy deployment from GitHub
- ✅ Auto-deploy on git push

### Deployment Steps

**Option 1: Deploy via GitHub (Recommended)**
```bash
# 1. Push your code to GitHub
git add .
git commit -m "Deploy Mello Roos API to Render"
git push origin master

# 2. Go to https://render.com
# 3. Sign up (use GitHub)
# 4. Click "New +" → "Web Service"
# 5. Connect your GitHub repo: sacramento-mello-roos-be
# 6. Render will auto-detect the render.yaml config
# 7. Click "Create Web Service"
# 8. Wait 5-10 minutes for deployment
```

**Option 2: Deploy via Render MCP (from this project)**
- Already configured with Render MCP server
- Can deploy directly using MCP commands

**Your API will be at:** `https://sacramento-tax-api.onrender.com`

---

## 🚀 Quick Start (Local Testing)

### Using Docker (Recommended)
```bash
# Build the image
docker build -t sacramento-tax-api .

# Run the container
docker run -p 8080:8080 \
  -e BROWSER_HEADLESS=true \
  -e CACHE_MAX_AGE_DAYS=30 \
  sacramento-tax-api

# Test it
curl "http://localhost:8080/get-tax-details?street_number=932&street_name=farmhouse%20way&city=Folsom"
```

### Using Python Directly
```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run the app
gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 app:app

# Or for development
python -c "from app import app; app.run(host='0.0.0.0', port=8080, debug=True)"
```

---

## 📡 API Endpoints

### Get Tax Details
```bash
GET /get-tax-details?street_number=932&street_name=farmhouse%20way&city=Folsom
```

**Query Parameters:**
- `street_number` (required): Street number
- `street_name` (required): Street name
- `city` (optional): City name (default: "Folsom")
- `force_refresh` (optional): Force fresh scrape (default: "false")

**Response:**
```json
{
  "success": true,
  "source": "cache",
  "property_info": {
    "objectID": "...",
    "account_number": "...",
    "address": "932 Farmhouse Way",
    "city": "Folsom",
    "zip": "95630"
  },
  "tax_details": {
    "bills": [...],
    "payment_history": [...]
  },
  "cache_info": {
    "cached_at": "2024-10-21T10:30:00",
    "cache_age_days": 2
  }
}
```

### Cache Stats
```bash
GET /cache-stats
```

### Health Check
```bash
GET /health
```

---

## 🎛️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BROWSER_HEADLESS` | `true` | Run browser in headless mode |
| `CACHE_MAX_AGE_DAYS` | `30` | Maximum cache age before re-scraping |
| `PORT` | `8080` | Server port |
| `PYTHONUNBUFFERED` | `1` | Disable Python output buffering |

---

## 💾 Database & Caching

- **Database:** SQLite (stored in `/app/data/` or `/tmp/` for serverless)
- **Cache Duration:** 30 days (configurable)
- **Cache Logic:**
  1. Check cache first
  2. If cache miss or expired → scrape with Playwright
  3. Save to cache
  4. Return data

**Note:** On free tiers, the filesystem may reset after inactivity. This means cache will be lost but will rebuild automatically on next request.

---

## 📊 Performance

- **Scrape Time:** ~3-8 seconds per request
- **Browser Memory:** ~150-300MB per scrape
- **Recommended:** 512MB RAM minimum
- **Cold Start:** ~30-60 seconds (after 15 min inactivity)

---

## 🔍 Monitoring & Debugging

### View Logs
```bash
# In Render dashboard:
# 1. Go to your service
# 2. Click "Logs" tab
# 3. View real-time logs
```

### Test Locally Without Headless
```python
# In scraper.py
scraper = PropertyTaxScraper(headless=False)
```

### Test Locally with Docker
```bash
docker build -t sacramento-tax-api .
docker run -p 8080:8080 -e BROWSER_HEADLESS=true sacramento-tax-api
curl "http://localhost:8080/get-mello-roos?street_number=932&street_name=farmhouse%20way&city=Folsom"
```

---

## 🆘 Troubleshooting

### Issue: "Browser not found"
```bash
# Install Playwright browsers locally
playwright install chromium
playwright install-deps chromium
```

### Issue: "Out of memory"
- Free tier has 512MB RAM (should be sufficient)
- If issues persist, reduce worker count to 1 in Dockerfile
- Consider upgrading to Starter plan ($7/month) for 512MB RAM

### Issue: "Timeout"
- Default timeout is 120 seconds (set in Dockerfile)
- If needed, increase in render.yaml or Dockerfile
- Check if Sacramento County website is down

### Issue: "Service sleeping"
- Normal behavior on free tier
- Service auto-wakes on request (30-60 seconds)
- Upgrade to Starter plan for 24/7 uptime

---

## 🎁 Render Free Tier

- **750 hours/month** (enough for 24/7 operation)
- **512MB RAM**
- **Auto-sleep after 15 min inactivity**
- **Free custom domains**
- **Free SSL certificates**

**Perfect for this use case!**

---

## 🚀 Next Steps

1. Choose a platform (I recommend **Render.com**)
2. Deploy following the steps above
3. Test your API
4. Update your frontend to use the new endpoint
5. (Optional) Add custom domain

---

## 📝 Notes

- First request after sleep may take 30-60 seconds (cold start)
- Subsequent requests are fast
- Cache reduces scraping frequency and improves response time
- For production with high traffic, consider paid tier ($7-20/month)

