# Expense Tracker

A full-stack expense tracking application with voice input powered by Claude AI, Google OAuth authentication, and user-specific expense management.

## Features

- 🎤 **Voice Input**: Record expenses using speech recognition
- 🤖 **AI-Powered Parsing**: Claude AI automatically extracts expense details from voice input
- 🔐 **Google OAuth**: Secure authentication with 24-hour session management
- 📊 **Category Management**: Automatic category extraction from expenses
- 🏷️ **Editable Categories**: Click any expense to add or change its category
- 📱 **Mobile-First Design**: Responsive interface optimized for mobile devices
- 🔄 **Infinite Scroll**: Lazy loading for efficient expense browsing
- 📅 **Date Filtering**: Filter expenses by month and year
- 📤 **CSV Export**: Export your expenses to CSV format
- 👤 **User Isolation**: Each user's expenses are completely private

## Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: SQL toolkit and ORM
- **SQLite**: Lightweight database
- **Anthropic Claude**: AI-powered expense parsing
- **Google OAuth 2.0**: Authentication
- **JWT**: Token-based session management

### Frontend
- **React**: UI library
- **Vite**: Build tool and dev server
- **@react-oauth/google**: Google authentication
- **Web Speech API**: Voice recognition

## Prerequisites

- Python 3.9+
- Node.js 20+
- Google Cloud Project with OAuth credentials
- Anthropic API key

## Environment Variables

### Backend (.env)
```env
ANTHROPIC_API_KEY=your_anthropic_api_key
DATABASE_URL=sqlite:///./expenses.db
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
JWT_SECRET_KEY=your_jwt_secret_key
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=your_google_client_id
```

## Local Development

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Docker Deployment

### Build and Run
```bash
docker build -t expense-tracker .
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your_key \
  -e GOOGLE_CLIENT_ID=your_client_id \
  -e GOOGLE_CLIENT_SECRET=your_client_secret \
  -e JWT_SECRET_KEY=your_jwt_secret \
  -v $(pwd)/data:/app/data \
  expense-tracker
```

### Using GitHub Container Registry
```bash
docker pull ghcr.io/your-username/expense-tracker:latest
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your_key \
  -e GOOGLE_CLIENT_ID=your_client_id \
  -e GOOGLE_CLIENT_SECRET=your_client_secret \
  -e JWT_SECRET_KEY=your_jwt_secret \
  -v $(pwd)/data:/app/data \
  ghcr.io/your-username/expense-tracker:latest
```

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized JavaScript origins:
   - `http://localhost:5173` (development)
   - Your production domain
6. Add authorized redirect URIs:
   - `http://localhost:5173` (development)
   - Your production domain

## API Endpoints

### Authentication
- `POST /api/auth/google` - Authenticate with Google OAuth token
- `GET /api/auth/me` - Get current user information

### Expenses
- `GET /api/expenses` - List expenses (with pagination and filters)
- `POST /api/expenses` - Create expense
- `GET /api/expenses/{id}` - Get expense by ID
- `PATCH /api/expenses/{id}/category` - Update expense category
- `DELETE /api/expenses/{id}` - Delete expense

### Voice Processing
- `POST /api/transcribe` - Process voice transcription and parse expense data

## Architecture

```
expense-tracker/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # Authentication logic
│   ├── claude_service.py    # AI expense parsing
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── context/         # React context (auth)
│   │   ├── App.jsx          # Main app component
│   │   └── main.jsx         # Entry point
│   └── package.json         # Node dependencies
├── Dockerfile               # Multi-stage Docker build
└── .github/
    └── workflows/
        └── docker-publish.yml  # CI/CD pipeline
```

## CI/CD Pipeline

The project includes a GitHub Actions workflow that automatically:
- Builds a Docker image on push to main/master
- Publishes to GitHub Container Registry
- Tags images with branch names, SHAs, and semantic versions
- Supports multi-platform builds (linux/amd64, linux/arm64)

To enable:
1. Push your code to GitHub
2. Ensure GitHub Actions has write permissions to packages
3. Images will be available at `ghcr.io/your-username/expense-tracker`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Security

- Never commit `.env` files
- Keep API keys and secrets secure
- Use HTTPS in production
- Regular security updates for dependencies
- JWT tokens expire after 24 hours

## Support

For issues and questions, please open a GitHub issue.
