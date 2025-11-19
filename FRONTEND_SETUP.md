# 🚀 React Frontend Setup Instructions

## Quick Start

### 1. Navigate to frontend directory
```bash
cd e:\rag_agent\frontend
```

### 2. Install dependencies
```bash
npm install
```

This installs:
- React 18
- Tailwind CSS
- Lucide React icons
- Axios for API calls

### 3. Start the development server
```bash
npm start
```

The app will automatically open at **http://localhost:3000**

### 4. Ensure backend is running
In another terminal:
```bash
cd e:\rag_agent
python backend_api.py
```

Backend API will run on **http://localhost:8000**

---

## Full Setup (from scratch)

### Step 1: Create React App (Already done)
```bash
# Already created, files are in e:\rag_agent\frontend
```

### Step 2: Install Dependencies
```bash
cd e:\rag_agent\frontend
npm install
```

### Step 3: Install Tailwind CSS
```bash
npm install -D tailwindcss postcss autoprefixer
```

### Step 4: Build for Production
```bash
npm run build
```

Output will be in `frontend/build/`

---

## Development Workflow

### Start Frontend Dev Server
```bash
cd e:\rag_agent\frontend
npm start
```

### Start Backend API
```bash
cd e:\rag_agent
python backend_api.py
```

### Both running = Full application ready!

---

## Project Structure

```
e:\rag_agent\
├── frontend/                    # React Frontend
│   ├── public/
│   │   └── index.html          # HTML template
│   ├── src/
│   │   ├── RAGChatbot.jsx      # Main chat component
│   │   ├── App.jsx             # Root component
│   │   ├── index.js            # Entry point
│   │   └── index.css           # Global styles
│   ├── package.json            # Dependencies
│   ├── tailwind.config.js      # Tailwind config
│   ├── postcss.config.js       # PostCSS config
│   ├── .env                    # Environment variables
│   └── .gitignore              # Git ignore rules
│
├── backend_api.py              # FastAPI backend
├── dashboard.py                # Streamlit dashboard
└── ... (Python source files)
```

---

## Features

### 💬 Chat Interface
- Real-time conversation
- Auto-routing to agents
- Action buttons
- Message history

### 📥 Document Upload
- Drag-drop support
- File preview
- Ingestion pipeline
- Success tracking

### 🔍 Search
- Semantic search
- RBAC filtering
- Relevance ranking
- Results display

### ⚙️ Settings
- Role management
- Access level control
- API endpoint config
- Theme selection

### 📊 Analytics
- System statistics
- Performance metrics
- Activity logs
- Health indicators

---

## Environment Configuration

Edit `frontend/.env`:

```env
# API Endpoint
REACT_APP_API_URL=http://localhost:8000/api

# WebSocket (for real-time updates - optional)
REACT_APP_WS_URL=ws://localhost:8000/ws
```

For production:
```env
REACT_APP_API_URL=https://your-production-api.com/api
```

---

## Troubleshooting

### "npm: command not found"
- Install Node.js from https://nodejs.org
- Add to PATH
- Restart terminal

### Port 3000 already in use
```bash
# Find and kill process on port 3000
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Or use different port
PORT=3001 npm start
```

### Backend connection refused
1. Ensure `backend_api.py` is running
2. Check backend is on port 8000
3. Verify CORS is enabled
4. Check `.env` API URL

### File upload fails
1. Check file type is supported (.txt, .pdf, .csv, .json, .md)
2. Check file size (default limit 10MB)
3. Verify backend is processing requests
4. Check browser console for errors

### Styles not loading
```bash
# Rebuild Tailwind CSS
npm run build:css

# Or just restart dev server
npm start
```

---

## Build Commands

```bash
# Development (with hot reload)
npm start

# Production build
npm run build

# Run tests
npm test

# Eject from Create React App (⚠️ irreversible)
npm run eject
```

---

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Modern mobile browsers

---

## Performance Optimization

Production build will:
- Minify JavaScript
- Optimize images
- Bundle splitting
- Caching strategies

Delivered in `frontend/build/` folder

---

## API Documentation

See `backend_api.py` for full API documentation

Main endpoints:
- `POST /api/chat` - Chat with agents
- `POST /api/upload` - Upload documents
- `POST /api/search` - Search documents
- `POST /api/heal` - Optimize system
- `GET /api/stats` - Get statistics
- `GET /api/health` - Health check

---

## Next Steps

1. ✅ Install dependencies: `npm install`
2. ✅ Start frontend: `npm start`
3. ✅ Start backend: `python backend_api.py`
4. ✅ Open http://localhost:3000
5. 🎉 Start using RAG Agent System!

---

For more info, see `frontend/README.md`
