# Sacramento Mello Roos API - Deployment Guide

## 🚀 Deploy to Vercel

### Prerequisites
- [Vercel CLI](https://vercel.com/docs/cli) installed: `npm install -g vercel`
- Git repository initialized
- Vercel account

### Quick Deployment Steps

1. **Install Vercel CLI (if not already installed)**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Deploy from your project directory**
   ```bash
   cd /Users/nikhilpujari/sacramento-mello-roos-be
   vercel
   ```

4. **Follow the prompts:**
   - Set up and deploy? **Y**
   - Which scope? Select your account
   - Link to existing project? **N**
   - Project name? **sacramento-mello-roos-api** (or your choice)
   - Directory? **./** (current directory)
   - Override settings? **N**

5. **Deploy to production**
   ```bash
   vercel --prod
   ```

### Alternative: Deploy via Vercel Dashboard

1. Go to [vercel.com](https://vercel.com)
2. Click "Add New Project"
3. Import your Git repository
4. Vercel will auto-detect the Flask app
5. Click "Deploy"

## 📡 API Endpoints

Once deployed, your API will be available at: `https://your-project.vercel.app`

### 1. **Root / Health Check**
```bash
GET /
GET /health
```

### 2. **Search Property**
```bash
GET /search?query=932 farmhouse way folsom
GET /search?apn=071-2040-013-0000
```

**Response:**
```json
{
  "success": true,
  "property": {
    "apn": "071-2040-013-0000",
    "address": "932 FARMHOUSE WAY FOLSOM 95630"
  },
  "bills": [
    {
      "bill_number": "20250150210",
      "display_name": "2025 Secured Annual Bill #20250150210",
      "custom_parameters": {...}
    }
  ],
  "total_bills": 10
}
```

### 3. **Get Bill Details (Mello Roos Breakdown)**
```bash
GET /bill-details?parent_id=<parent_id>&bill_id=<bill_id>
```

**Response:**
```json
{
  "success": true,
  "ad_valorem_taxes": [
    {
      "name": "Countywide Tax (Secured)",
      "rate": "1.00000000%",
      "taxable_value": "$681,139.00",
      "tax_amount": "$6,811.39"
    }
  ],
  "total_ad_valorem": 7429.18,
  "mello_roos": {
    "has_mello_roos": true,
    "charges": [
      {
        "name": "CFD NO 16 IA2 ISLANDS AT PARKSHORE",
        "code": "0112",
        "phone": "(888) 892-2480",
        "amount": "$2,243.70"
      }
    ],
    "total_mello_roos": 2260.34
  },
  "grand_total": 9689.52
}
```

### 4. **Legacy Endpoint (Backwards Compatible)**
```bash
GET /get-mello-roos?street_number=932&street_name=farmhouse way&city=Folsom
```

## 🧪 Testing the Deployed API

```bash
# Test search
curl "https://your-project.vercel.app/search?query=932%20farmhouse%20way%20folsom"

# Test bill details
curl "https://your-project.vercel.app/bill-details?parent_id=c2FjcmFtZW50by1jYTpnc2d4X3Byb3BlcnR5X3RheDpwYXJlbnRzOmE0ZjRkNWVhLThiNWYtMTFmMC04Zjg5LWYxMjRjNWEyMDM0Yw==&bill_id=A4FAABB4-8B5F-11F0-A666-A9B7592EE820"
```

## 📝 Environment Variables

No environment variables required! The API uses public data sources.

## 🔧 Local Development

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Test locally
curl http://localhost:8080/
```

## 🚨 Troubleshooting

### Build Fails
- Make sure `requirements.txt` is in the root directory
- Verify `vercel.json` configuration is correct

### API Returns Errors
- Check that Sacramento County website is accessible
- Verify the search query format

### CORS Issues
- CORS is enabled for all origins by default
- Modify `CORS(app, resources={...})` in `app.py` if needed

## 📊 Performance Notes

- **Fast:** No browser automation, pure API calls
- **Reliable:** Direct API access to Sacramento County data
- **Scalable:** Serverless deployment handles traffic automatically

## 🔄 Updating the Deployment

```bash
# Make changes to your code
git add .
git commit -m "Update API"
git push

# Redeploy
vercel --prod
```

## 📚 API Features

✅ **Property Search** - Search by address or APN  
✅ **Bill History** - Get all tax bills for a property  
✅ **Detailed Breakdown** - Ad Valorem taxes and Mello Roos charges  
✅ **No Browser** - Fast API-based scraping  
✅ **CORS Enabled** - Use from any frontend  
✅ **Backwards Compatible** - Legacy endpoints still work

---

**Questions?** Check the code comments in `app.py` and `sacramento_tax_api.py`
