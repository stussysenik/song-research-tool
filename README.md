# Song Research Tool

A fully functional application for extracting song lists from various file formats (images, PDF, text, CSV) and assisting with finding/downloading them.

## Project Structure

```
.
├── backend/        # Python FastAPI backend
├── frontend/       # Next.js frontend
├── .env            # Root environment config (e.g., API keys)
├── .gitignore
├── LICENSE
└── README.md
```

## Features

- **Song Extraction** from multiple formats:
  - Images (JPG, PNG) using OCR powered by Google's Gemini Vision API
  - PDF documents 
  - Text files (TXT)
  - CSV files
- **Playlist Download** with real-time progress tracking
- **Multiple Download Strategies** for finding songs across different platforms
- **Metadata Enrichment** for downloaded files

## Setup

**Prerequisites:**
*   Python 3.8+ and `pip`
*   Node.js and `npm` (or `yarn`)

**1. Configure Environment:**

*   **Backend:** Create a `.env` file in the project root with necessary API keys:
    ```
    GOOGLE_AI_API_KEY=your_gemini_api_key
    # Add other backend environment variables if needed
    ```
*   **Frontend:** Create a `.env.local` file in the `frontend/` directory:
    ```
    NEXT_PUBLIC_API_URL=http://localhost:8000
    ```
    *(Adjust the URL if your backend runs on a different port)*

**2. Install Dependencies:**

*   **Backend:**
    ```bash
    # Create and activate a virtual environment (recommended)
    python3 -m venv backend/.venv
    source backend/.venv/bin/activate  # On Windows use `backend\.venv\Scripts\activate`
    
    # Install Python dependencies
    pip install -r backend/requirements.txt
    ```
*   **Frontend:**
    ```bash
    cd frontend
    npm install  # or yarn install
    cd ..
    ```

## Running the Application

**1. Start the Backend Server:**

*   Make sure your backend virtual environment is activated.
*   Run the FastAPI server:
    ```bash
    # (If venv is activated)
    python backend/run.py 
    
    # Or run directly using the venv python
    # backend/.venv/bin/python backend/run.py
    ```
    The backend API will typically be available at `http://localhost:8000`.

**2. Start the Frontend Development Server:**

*   Open a **new terminal**.
*   Navigate to the frontend directory and start the server:
    ```bash
    cd frontend
    npm run dev  # or yarn dev
    ```
    The frontend will typically be available at `http://localhost:3000`.

## Usage

1.  Open your browser and navigate to the frontend URL (e.g., `http://localhost:3000`).
2.  Use the interface to upload a playlist file (image, PDF, text, CSV).
3.  The application will extract the songs and display them for review.
4.  Click "Start Download" to begin downloading the songs.
5.  Track download progress in real-time through the UI.

Downloaded files are stored in the `playlist` directory at the project root. Each song is saved as an MP3 file named with the format `Title - Artist.mp3`.

## Testing

Run backend integration tests with:
```bash
# Ensure GOOGLE_AI_API_KEY is set in your environment
python backend/test_integration.py
```

Run frontend tests with:
```bash
cd frontend
npm test  # or yarn test
```
