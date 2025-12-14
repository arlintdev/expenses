# Setup Instructions

Before starting the application, you need to configure your Anthropic API key.

## Set Your API Key

Edit the file `backend/.env` and replace `your_api_key_here` with your actual Anthropic API key:

```bash
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
DATABASE_URL=sqlite:///./expenses.db
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

## Start the Application

Once you've set your API key, run:

```bash
npm run dev
```

This will start:
- Backend API at http://localhost:8000
- Frontend at http://localhost:5173

## API Documentation

Once running, visit http://localhost:8000/docs for the interactive API documentation.
