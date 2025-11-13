# FinanceIQ Deployment Guide - Railway

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Repository**: Your code pushed to GitHub
3. **Qdrant Cloud Account**: Sign up at [cloud.qdrant.io](https://cloud.qdrant.io) (free tier available)
4. **OpenAI API Key**: Get from [platform.openai.com](https://platform.openai.com)

## Step 1: Set Up Qdrant Cloud

1. Go to [cloud.qdrant.io](https://cloud.qdrant.io) and create a free account
2. Create a new cluster (free tier: 1GB storage, 1M vectors)
3. Note down:
   - **Cluster URL** (e.g., `https://xyz-abc.qdrant.io`)
   - **API Key**

## Step 2: Deploy to Railway

### A. Create New Project

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway to access your GitHub
5. Select your `IBMProject` repository

### B. Configure Environment Variables

In Railway dashboard, go to your service → Variables, and add:

```bash
# Required
OPENAI_API_KEY=sk-proj-...
QDRANT_HOST=xyz-abc.qdrant.io
QDRANT_PORT=6334
QDRANT_API_KEY=your-qdrant-api-key

# Optional (with defaults)
USE_AGENTS=true
EMBEDDING_MODEL=text-embedding-3-small
PRIMARY_LLM=gpt-4-turbo-preview
FALLBACK_LLM=gpt-3.5-turbo
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_CHUNKS=5
MIN_RELEVANCE_SCORE=0.5
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=2000
```

### C. Deploy

1. Railway will automatically detect the `Dockerfile`
2. Click "Deploy"
3. Wait 3-5 minutes for build and deployment
4. Railway will provide a public URL (e.g., `financeiq-production.up.railway.app`)

## Step 3: Connect Qdrant Cloud

Update your Qdrant connection to use HTTPS and API key:

The `VectorStoreManager` needs to be updated to support Qdrant Cloud. Add this to your Railway environment variables:

```bash
QDRANT_USE_HTTPS=true
QDRANT_API_KEY=your-api-key-here
```

## Step 4: Custom Domain (Optional)

1. In Railway dashboard → Settings → Domains
2. Click "Custom Domain"
3. Enter your domain (e.g., `financeiq.yourdomain.com`)
4. Update your DNS with the CNAME provided by Railway

## Step 5: Verify Deployment

1. Visit your Railway URL
2. Upload a test document
3. Ask a test query
4. Check that multi-agent processing works (toggle on)
5. Open a new tab and verify session isolation

## Monitoring & Logs

- **Logs**: Railway dashboard → Deployments → View Logs
- **Metrics**: Railway dashboard → Metrics (CPU, RAM, Network)
- **Health Check**: Railway automatically monitors the `/health` endpoint

## Troubleshooting

### Build Fails
- Check Railway build logs for errors
- Verify `pyproject.toml` has all dependencies
- Ensure Docker builds locally first: `docker build -t financeiq .`

### App Won't Start
- Check environment variables are set correctly
- Verify Qdrant Cloud connection (host, port, API key)
- Check Railway deployment logs

### Qdrant Connection Issues
- Verify Qdrant Cloud cluster is running
- Check API key is correct
- Ensure `QDRANT_PORT=6334` (Qdrant Cloud uses 6334 for HTTPS)

### Out of Memory
- Upgrade Railway plan (Hobby: $5/month for 8GB RAM)
- Reduce `CHUNK_SIZE` and `TOP_K_CHUNKS` if needed

## Cost Estimate

- **Railway Hobby Plan**: $5/month (8GB RAM, always-on)
- **Qdrant Cloud Free Tier**: $0 (1GB storage)
- **OpenAI API**: Pay-per-use (~$0.01-0.10 per session)

**Total**: ~$5-10/month for production-ready deployment

## Security Notes

- ✅ Session isolation prevents data leakage between users
- ✅ Environment variables stored securely in Railway
- ✅ HTTPS enabled by default
- ⚠️ This is a demo app - don't upload highly confidential documents
- ⚠️ Add rate limiting for production use
- ⚠️ Consider adding authentication for sensitive deployments

## Updates & Redeployment

Railway automatically redeploys when you push to GitHub:

```bash
git add .
git commit -m "Update feature X"
git push origin main
```

Railway will detect the push and redeploy within 3-5 minutes.
