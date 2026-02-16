# TrustWise Frontend - Quick Demo Guide

This guide will walk you through testing the frontend in 5 minutes!

## Step 1: Start the Application (30 seconds)

### Option A: Using the Startup Scripts

```bash
# Windows Command Prompt
start.bat

# OR Windows PowerShell
.\start.ps1
```

### Option B: Manual Start

**Terminal 1 - Backend:**

```bash
cd c:\Anushk\Codes\TrustWise_Group\TrustWise
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**

```bash
cd c:\Anushk\Codes\TrustWise_Group\TrustWise\frontend
python serve.py
```

**Open Browser:**
Navigate to http://localhost:3000

---

## Step 2: Create Your First Job (1 minute)

1. In the **"Create New Job"** section on the left, enter a source name:

   ```
   test-source
   ```

2. Click **"Create Job"**

3. You'll see:
   - ✅ Success message with Job ID
   - The Job ID auto-filled in the extraction form
   - New job appears in the "Jobs List"

---

## Step 3: View Job List (30 seconds)

Look at the **"Jobs List"** panel:

- You should see your newly created job
- Status badge: 🟡 **PENDING**
- Shows creation timestamp
- Click **"Refresh"** button to update the list

**Try the filters:**

- Filter by Status: Select "pending"
- Filter by Source: Type part of your source name

---

## Step 4: View Job Details (30 seconds)

1. Click on your job in the list (it will highlight in purple)
2. The **"Job Details"** panel below shows:
   - ✅ Job ID
   - ✅ Source name
   - ✅ Status
   - ✅ Create/Start/Complete timestamps
   - ⚠️ "No data extracted yet" (because we haven't run extraction)

---

## Step 5: Start Data Extraction (2 minutes)

1. In the **"Start Extraction"** form (should have your Job ID filled):
   - **Job ID**: ✅ Already filled
   - **Query**: Enter `machine learning` (or leave empty)
   - **Extractor Type**: Select **"All Extractors (Parallel)"**

2. Click **"Start Extraction"**

3. Wait 5-10 seconds, then click **"🔄 Refresh Details"**

4. You should now see:
   - Status changed to 🔵 **RUNNING** or 🟢 **SUCCESS**
   - **Extracted Data** section with items showing:
     - Source (web, research, vector, db)
     - Trust Score (e.g., "Trust: 85.0%")
     - Timestamp
     - Raw JSON data

---

## Step 6: Test Auto-Refresh (1 minute)

1. Click **"⏱️ Auto-refresh (5s)"** button
2. Watch as the job details update automatically every 5 seconds
3. Click the button again to stop auto-refresh

---

## Step 7: Create Multiple Jobs (1 minute)

Create more jobs with different sources:

1. **"research-papers"**
2. **"tech-news"**
3. **"financial-data"**

Then:

- Filter by different statuses
- Compare trust scores across different sources
- View each job's extracted data

---

## Expected Output Examples

### Example 1: Web Scraping Result

```json
{
  "source": "web",
  "data": {
    "title": "Machine Learning Tutorial",
    "url": "https://example.com/ml",
    "content": "Introduction to ML..."
  },
  "trust_score": 0.85,
  "extracted_at": "2026-02-16T10:30:00"
}
```

### Example 2: Research API Result

```json
{
  "source": "research",
  "data": {
    "title": "Deep Learning Advances",
    "authors": ["Smith, J.", "Doe, A."],
    "abstract": "Recent advances in...",
    "arxiv_id": "2401.12345"
  },
  "trust_score": 0.92,
  "extracted_at": "2026-02-16T10:30:05"
}
```

### Example 3: Vector Database Result

```json
{
  "source": "vector",
  "data": {
    "document": "ML research document",
    "similarity": 0.89,
    "metadata": { "category": "AI" }
  },
  "trust_score": 0.88,
  "extracted_at": "2026-02-16T10:30:10"
}
```

---

## Troubleshooting the Demo

### Issue: "Error loading jobs"

**Solution**:

- Check backend is running: http://localhost:8000
- Try visiting http://localhost:8000/health in browser
- Should see: `{"status":"running","service":"TrustWise Orchestrator"...}`

### Issue: "Job not found"

**Solution**:

- Click "Refresh" in the jobs list
- Copy the exact Job ID from the job list
- Make sure you're using a UUID format (e.g., `123e4567-e89b-12d3-a456-426614174000`)

### Issue: "Extraction failed"

**Solution**:

- This might be expected if external services aren't configured
- Check backend terminal for detailed error messages
- Try with a different extractor type (e.g., "Web Scraping" only)

### Issue: No data appears after extraction

**Solution**:

- Wait 10-15 seconds (extraction takes time)
- Click "Refresh Details" button
- Check if job status changed to "success" or "failed"
- Review error_message field if status is "failed"

---

## Advanced Testing

### Test 1: Parallel Extraction

```
1. Create job with source: "parallel-test"
2. Start extraction with "All Extractors"
3. Watch status change from PENDING → RUNNING → SUCCESS
4. See data from multiple sources appear simultaneously
```

### Test 2: Specific Extractor

```
1. Create job with source: "web-only-test"
2. Start extraction with extractor type: "Web Scraping"
3. Should only see data from web source
```

### Test 3: Job Filtering

```
1. Create 5+ jobs with different sources
2. Run extraction on some (not all)
3. Filter by status: "success" - should show only completed jobs
4. Filter by source: "test" - should show only matching sources
```

### Test 4: High-Volume Jobs

```
1. Rapidly create 10-20 jobs
2. Start extractions on multiple jobs
3. Test that list updates correctly
4. Verify pagination works (should show 50 jobs max)
```

---

## What to Look For (Quality Check)

✅ **UI/UX:**

- Clean, modern interface
- Smooth animations when hovering
- Responsive design (try resizing browser)
- Status badges colored correctly

✅ **Functionality:**

- Jobs appear in list after creation
- Filters work correctly
- Details update when clicking jobs
- Extraction starts without errors

✅ **Data Display:**

- Trust scores shown as percentages
- Timestamps formatted correctly
- JSON data readable and formatted
- Multiple data items displayed properly

✅ **Performance:**

- Page loads quickly
- No lag when switching jobs
- Auto-refresh works smoothly
- List handles 50+ jobs well

---

## Screenshots Guide

If sharing this project, capture these screens:

1. **Main Dashboard** - Full view with all panels
2. **Job List** - With multiple jobs and various statuses
3. **Job Details** - With extracted data visible
4. **Extraction Form** - Filled out and ready to submit
5. **Data Item** - Close-up of extracted data with trust score

---

## Next Steps After Demo

1. **Customize the UI:**
   - Edit colors in `index.html` CSS section
   - Add your company logo
   - Modify text and labels

2. **Add Authentication:**
   - Implement login/logout
   - Add API key support
   - User role management

3. **Enhance Features:**
   - Export data to CSV/JSON
   - Job comparison view
   - Trust score analytics/charts
   - Email notifications

4. **Deploy to Production:**
   - See [frontend/README.md](README.md) for deployment guides
   - Configure CORS for your domain
   - Set up HTTPS/SSL

---

## Demo Checklist

Use this checklist when demoing to others:

- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000
- [ ] Browser opened to http://localhost:3000
- [ ] Created at least one job
- [ ] Started extraction successfully
- [ ] Viewed extracted data
- [ ] Tested filtering
- [ ] Demonstrated auto-refresh
- [ ] Showed multiple job statuses
- [ ] Highlighted trust scores

---

## Support

Questions or issues during the demo?

1. Check browser console (F12) for JavaScript errors
2. Check backend terminal for API errors
3. Review [frontend/README.md](README.md) for detailed troubleshooting
4. Check [PROJECT_SUMMARY.md](../PROJECT_SUMMARY.md) for system architecture

---

**Enjoy exploring TrustWise! 🛡️**
