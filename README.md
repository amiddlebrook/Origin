# Origin

A platform for discovering the origins and stories behind names, with support for oral histories and multimedia content.

## Features

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

### Research Tools

- Automated name research using multiple data sources
- Background processing for long-running research tasks
- Structured results with source attribution

## Setup

1. Clone the repository
2. Install dependencies:
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