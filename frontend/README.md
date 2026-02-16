# TrustWise Frontend

A modern, responsive web interface for the TrustWise Data Orchestration Engine.

## Features

✨ **Modern UI** - Clean, gradient-based design with smooth animations
📊 **Real-time Updates** - Auto-refresh job lists and details
🎯 **Job Management** - Create jobs, start extractions, and monitor progress
📈 **Data Visualization** - View extracted data with trust scores
🔍 **Filtering & Search** - Filter jobs by status and source
📱 **Responsive Design** - Works on desktop and mobile devices

## Quick Start

### Option 1: Using Python HTTP Server (Recommended)

1. **Start the Backend** (in a terminal):

   ```bash
   cd c:\Anushk\Codes\TrustWise_Group\TrustWise
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the Frontend Server** (in another terminal):

   ```bash
   cd c:\Anushk\Codes\TrustWise_Group\TrustWise\frontend
   python serve.py
   ```

3. **Open Your Browser**:
   Navigate to: http://localhost:3000

### Option 2: Open HTML Directly

Simply open `index.html` in your web browser. Update the API URL in the interface if needed.

## Usage Guide

### 1. Create a Job

1. Enter a **Source Name** in the "Create New Job" section
2. Click **Create Job**
3. The job ID will be auto-filled in the extraction form

### 2. Start Data Extraction

1. Select or enter a **Job ID**
2. (Optional) Enter a **Query** for targeted extraction
3. Choose an **Extractor Type**:
   - **All Extractors** (default) - Runs all extractors in parallel
   - **Web Scraping** - Extracts data from web sources
   - **Research API** - Queries research databases (ArXiv, IEEE)
   - **Vector Database** - Semantic search in vector stores
4. Click **Start Extraction**

### 3. Monitor Jobs

- View all jobs in the **Jobs List** panel
- Filter by **Status** (pending, running, success, failed)
- Filter by **Source name**
- Click **Refresh** to update the list manually
- Jobs auto-refresh every 10 seconds

### 4. View Job Details

1. Click on any job in the list to select it
2. View complete job information in the **Job Details** panel:
   - Job metadata (ID, source, status, timestamps)
   - Extracted data with trust scores
   - Error messages (if any)
3. Click **🔄 Refresh Details** to update manually
4. Click **⏱️ Auto-refresh (5s)** to enable/disable auto-refresh

### 5. View Extracted Data

Each data item shows:

- **Source** - Where the data came from
- **Trust Score** - Confidence level (0-100%)
- **Timestamp** - When it was extracted
- **Raw Data** - JSON formatted data content

## API Configuration

The default API URL is `http://localhost:8000`. You can change it:

1. Update the **API Base URL** field at the top of the page
2. The setting persists for your current session

## Status Badges

- 🟡 **PENDING** - Job created, waiting to start
- 🔵 **RUNNING** - Extraction in progress
- 🟢 **SUCCESS** - Completed successfully
- 🔴 **FAILED** - Extraction failed (check error message)

## Keyboard Shortcuts

- `Ctrl+R` / `F5` - Refresh page
- Click any job card to view details

## Troubleshooting

### Cannot connect to backend

**Problem**: "Error loading jobs" or connection errors

**Solutions**:

1. Verify backend is running: http://localhost:8000
2. Check the API URL setting in the frontend
3. Ensure CORS is enabled in the backend (should be automatic)
4. Check browser console for detailed errors

### No jobs appearing

**Problem**: Jobs list is empty

**Solutions**:

1. Create a new job using the "Create New Job" form
2. Check if filters are hiding jobs (reset Status and Source filters)
3. Verify database is properly initialized

### Extraction not starting

**Problem**: "Extraction failed" error

**Solutions**:

1. Verify the Job ID is correct (copy from job list)
2. Check that the job exists and is in a valid state
3. Review backend logs for detailed error messages
4. Ensure extraction services (web scraper, APIs) are accessible

### Data not appearing after extraction

**Problem**: Job shows "Success" but no data

**Solutions**:

1. Wait a few seconds and click "Refresh Details"
2. Enable auto-refresh to monitor in real-time
3. Check backend logs for extraction status
4. Verify the source has available data to extract

## Architecture

### Frontend Stack

- **HTML5** - Semantic markup
- **CSS3** - Modern styling with gradients and animations
- **Vanilla JavaScript** - No frameworks, lightweight and fast
- **Fetch API** - RESTful communication with backend

### Backend Integration

- **FastAPI REST API** - All communication via HTTP/JSON
- **CORS Enabled** - Cross-origin requests supported
- **Rate Limited** - Respects backend rate limits

## Browser Support

Tested and working on:

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Edge 90+
- ✅ Safari 14+

## Development

### Files Structure

```
frontend/
├── index.html          # Main application file
├── serve.py           # Python HTTP server script
└── README.md          # This file
```

### Customization

**Change Colors**: Edit the CSS gradients in the `<style>` section:

```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

**Change Auto-refresh Interval**: Edit the JavaScript at the bottom:

```javascript
setInterval(loadJobs, 10000); // 10 seconds
```

**API Timeout**: Add timeout to fetch calls:

```javascript
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 5000);
fetch(url, { signal: controller.signal });
```

## Production Deployment

For production use:

1. **Update CORS Settings** in backend (`app/main.py`):

   ```python
   allow_origins=["https://your-domain.com"],
   ```

2. **Use a proper web server**:
   - Nginx
   - Apache
   - AWS S3 + CloudFront
   - Netlify / Vercel

3. **Add Authentication**:
   - JWT tokens
   - OAuth2
   - API keys

4. **Enable HTTPS**:
   - SSL/TLS certificates
   - Secure cookies

## Support

For issues or questions:

1. Check backend logs: Look for errors in the FastAPI console
2. Check browser console: Press F12 and look for JavaScript errors
3. Review the [main project README](../README.md)

## License

Part of the TrustWise project - see main project for license details.
