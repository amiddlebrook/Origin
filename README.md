# Origin

A platform for discovering the origins and stories behind names, with support for oral histories and multimedia content.

## Features

### Bulk Operations

Efficiently manage large datasets with our comprehensive bulk operations:

- **Bulk Create/Update/Delete**: Perform batch operations on research items, stories, and oral histories
- **Workspace Management**: Add or remove multiple resources from workspaces in a single request
- **Error Handling**: Detailed error reporting for failed operations
- **Duplicate Handling**: Optional duplicate detection and skipping

### Rate Limiting

Protect your API with configurable rate limiting:

- **Flexible Rate Limits**: Different limits for different endpoints
- **User & IP Based**: Rate limiting by user account or IP address
- **Detailed Headers**: Real-time rate limit information in response headers
- **Configurable Windows**: Adjustable time windows for rate limits

### Analytics & Insights

Gain valuable insights into user behavior and content performance with our comprehensive analytics:

- **User Activity Tracking**: Monitor user actions and system events
- **Search Analytics**: Understand what users are searching for and how they interact with search results
- **Content Engagement**: Track views, interactions, and time spent on content
- **Custom Reporting**: Generate reports on various metrics with flexible filtering
- **Real-time Dashboards**: Monitor key metrics in real-time

### Oral Histories

Origin allows users to upload, manage, and process oral history recordings. The system supports:

- **Audio File Upload**: Upload audio recordings in various formats (MP3, WAV, etc.)
- **Background Processing**: Automatic processing of audio files to extract metadata and generate transcripts
- **Story Association**: Link oral histories with name stories for richer narratives
- **Search & Filter**: Find oral histories by title, date, or associated story

#### API Endpoints

- `POST /oral-histories/upload` - Upload a new oral history recording
  - **Content-Type**: `multipart/form-data`
  - **Parameters**:
    - `file`: The audio file to upload (required)
    - `title`: Title for the oral history (required)
    - `story_id`: Optional ID of a story to associate with this recording

- `GET /oral-histories/` - List all oral histories for the current user
  - **Query Parameters**:
    - `story_id`: Filter by associated story ID

- `GET /oral-histories/{oral_id}` - Get details of a specific oral history

- `PUT /oral-histories/{oral_id}` - Update an oral history (e.g., change title or story association)

- `DELETE /oral-histories/{oral_id}` - Delete an oral history and its associated audio file

### Name Stories

- Create and manage name stories with rich text and media
- Associate stories with research data
- Share and explore community-contributed stories
- Bulk import/export capabilities

### Research Tools

- Automated name research using multiple data sources
- Background processing for long-running research tasks
- Structured results with source attribution
- Bulk research operations for large datasets

### Collaboration Features

- Shared workspaces for team collaboration
- Comments and annotations on resources
- Version history and change tracking
- Fine-grained access control

### Webhook Support

- Real-time event notifications
- Configurable webhook endpoints
- Retry mechanisms for failed deliveries
- HMAC signature verification

### Analytics

- User activity tracking
- Usage statistics
- Performance metrics
- Custom reporting

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+ (or SQLite for development)
- Redis (for background tasks and rate limiting)
- FFmpeg (for media processing)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/origin.git
   cd origin
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Initialize the database:
   ```bash
   alembic upgrade head
   ```

6. Start the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Documentation

Once the server is running, you can access:

- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Configuration

Key configuration options (set in `.env` or environment variables):

```ini
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/origin

# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours

# CORS (comma-separated origins)
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# File Storage
MEDIA_UPLOAD_DIR=./media
MAX_UPLOAD_SIZE=104857600  # 100MB

# Rate Limiting
RATE_LIMIT_ENABLED=true
DEFAULT_RATE_LIMIT=60/1m  # 60 requests per minute

# Webhooks
WEBHOOK_TIMEOUT=5  # seconds
WEBHOOK_MAX_RETRIES=3

# Analytics
ANALYTICS_ENABLED=true
```

## Development

### Running Tests

```bash
pytest
```

### Code Style

We use `black` for code formatting and `isort` for import sorting:

```bash
black .
isort .
```

### Database Migrations

To create a new migration:

```bash
alembic revision --autogenerate -m "Your migration message"
```

To apply migrations:

```bash
alembic upgrade head
```

## Deployment

### Docker

Build and run with Docker Compose:

```bash
docker-compose up --build
```

### Production

For production deployment, consider using:

- **ASGI Server**: Uvicorn with Gunicorn
- **Process Manager**: Systemd or Supervisor
- **Reverse Proxy**: Nginx or Traefik
- **Database**: PostgreSQL with connection pooling
- **Caching**: Redis
- **Background Tasks**: Celery with Redis/RabbitMQ

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT

## Support

For support, please open an issue in the GitHub repository.
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables (copy `.env.example` to `.env` and update values)
4. Run database migrations:
   ```bash
   alembic upgrade head
   ```
5. Start the development server:
   ```bash
   uvicorn app.main:create_app --reload
   ```

## Testing

Run the test suite with:

```bash
pytest
```

## Background Processing

Long-running tasks like audio processing and name research are handled by background workers. Make sure to start the worker processes:

```bash
celery -A app.tasks.worker worker --loglevel=info
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.