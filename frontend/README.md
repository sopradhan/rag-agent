# 🤖 RAG Agent System - React Frontend

Modern interactive UI for the RAG (Retrieval-Augmented Generation) Agent System with RBAC, LangChain DeepAgents, and intelligent document processing.

## Features

✨ **Interactive Chat Interface**
- Real-time conversation with RAG agents
- Intent detection and automatic routing
- Multi-session support

📥 **Document Ingestion**
- Drag-and-drop file upload
- Support for .txt, .pdf, .csv, .json, .md
- Automatic metadata extraction and RBAC classification
- Real-time ingestion pipeline feedback

🔍 **Intelligent Retrieval**
- Semantic search with vector embeddings
- RBAC-aware filtering by user role
- Chain-of-thought reasoning display
- Relevance scoring

⚙️ **System Management**
- Vector store optimization
- Embedding regeneration
- Namespace cleanup
- Real-time healing operations

📊 **Analytics Dashboard**
- Document statistics
- Query metrics
- Performance monitoring
- System health indicators

🔐 **Role-Based Access Control**
- 5-level access hierarchy (Intern → Admin)
- Department-based filtering
- Real-time permission enforcement

## Tech Stack

- **Frontend**: React 18, Tailwind CSS, Lucide Icons
- **Backend**: FastAPI, Python
- **State Management**: React Hooks
- **HTTP Client**: Axios
- **Build Tool**: Create React App

## Installation

### Prerequisites
- Node.js 16+ and npm
- Python 3.9+
- RAG Agent backend running

### Setup

1. **Clone the repository**
```bash
cd rag-agent
```

2. **Install frontend dependencies**
```bash
cd frontend
npm install
```

3. **Install backend dependencies**
```bash
pip install -r requirements.txt
```

## Running

### Start Backend API
```bash
python backend_api.py
```
Backend will run on `http://localhost:8000`

### Start Frontend
```bash
cd frontend
npm start
```
Frontend will open at `http://localhost:3000`

### Access the Application
Visit **http://localhost:3000** in your browser

## Usage

### Chat Interface
1. Type your request (e.g., "Search for database procedures")
2. System automatically detects intent:
   - **Search** → Retrieval Agent
   - **Ingest/Upload** → Ingestion Agent
   - **Optimize/Heal** → Healing Agent
3. Click action buttons for quick operations
4. View detailed results with reasoning trace

### Upload Documents
1. Click **Upload** button
2. Select document (txt, pdf, csv, json, md)
3. System processes:
   - Document chunking
   - Metadata extraction
   - RBAC classification
   - Embedding generation
   - Vector storage

### Manage Role/Access
Use the role selector in the header:
- **Intern** (Level 1) - Limited access
- **Junior** (Level 2) - Basic access
- **Engineer** (Level 3) - Full technical access
- **Lead** (Level 4) - Supervisory access
- **Admin** (Level 5) - Complete access

### View Analytics
Switch to **Analytics** tab to see:
- Total documents in system
- Queries processed (24h)
- Average response time
- Success rate
- Recent activity log

### System Healing
1. Click **Analytics** → Select "Optimize"
2. Choose healing mode:
   - **Full** - Complete optimization (20 min)
   - **Quick** - Fast cleanup (5 min)
   - **Embedding** - Regenerate vectors (10 min)

## API Endpoints

### Chat
```
POST /api/chat
{
  "message": "string",
  "user_role": "engineer",
  "session": "Session 1"
}
```

### Upload
```
POST /api/upload
(multipart/form-data with file)
```

### Search
```
POST /api/search
{
  "query": "string",
  "user_role": "engineer"
}
```

### Heal
```
POST /api/heal
{
  "mode": "full|namespace|embedding"
}
```

### Stats
```
GET /api/stats
```

### Health
```
GET /api/health
```

## Directory Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── RAGChatbot.jsx      # Main chat component
│   ├── App.jsx             # Root component
│   ├── index.js            # Entry point
│   └── index.css           # Global styles
├── package.json
├── tailwind.config.js
├── postcss.config.js
└── .env
```

## Environment Variables

Create `.env` file in frontend directory:

```
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_WS_URL=ws://localhost:8000/ws
```

## Build for Production

```bash
npm run build
```

Production build will be created in `frontend/build/`

## Customization

### Modify API Endpoint
Edit `.env`:
```
REACT_APP_API_URL=https://your-api-domain.com/api
```

### Change Theme
Edit `src/index.css` or `tailwind.config.js` for color scheme customization

### Add New Intent
In `RAGChatbot.jsx`, update `detectIntent()` function:
```javascript
if (lower.includes('your_keyword')) {
  return 'your_intent';
}
```

## Troubleshooting

### Backend connection fails
- Ensure backend API is running on port 8000
- Check `REACT_APP_API_URL` in `.env`
- Verify CORS is enabled in backend

### File upload not working
- Check file size limits in backend
- Verify supported file types
- Check browser console for errors

### Commands not recognized
- Update `detectIntent()` with new keywords
- Check backend routing logic
- Review recent activity logs

## Performance Tips

- Clear chat periodically to reduce memory
- Use specific search queries for faster results
- Run system healing during off-peak hours
- Monitor analytics for bottlenecks

## Contributing

1. Create feature branch
2. Make your changes
3. Test thoroughly
4. Submit pull request

## License

Proprietary - RAG Agent System

## Support

For issues or questions:
- Check logs in browser console
- Review backend API documentation
- Contact system administrator

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-19
