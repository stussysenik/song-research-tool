import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DownloadManager from '../DownloadManager';
import * as api from '@/lib/api';
import '@testing-library/jest-dom';  // Add this import for toBeInTheDocument

// Mock the API functions
vi.mock('@/lib/api', () => ({
  downloadSongPlaylist: vi.fn(),
  getProgress: vi.fn(),
}));

// Mock toast notifications
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  }
}));

describe('DownloadManager', () => {
  const sampleSongList = "Song A,Artist X\nSong B,Artist Y";
  
  beforeEach(() => {
    vi.resetAllMocks();
  });
  
  afterEach(() => {
    vi.clearAllTimers();
  });
  
  it('should render nothing when no songList prop is provided', () => {
    const { container } = render(<DownloadManager />);
    expect(container.firstChild).toBeNull();
  });
  
  it('should render initial state with songList prop', async () => {
    render(<DownloadManager songList={sampleSongList} />);
    
    // Initial state should show song list and Start Download button
    expect(screen.getByText(/Ready to download 2 songs/i)).toBeInTheDocument();
    
    // Check that the song list is displayed
    expect(screen.getByText('Song A')).toBeInTheDocument();
    expect(screen.getByText('Artist X')).toBeInTheDocument();
    expect(screen.getByText('Song B')).toBeInTheDocument();
    expect(screen.getByText('Artist Y')).toBeInTheDocument();
    
    expect(screen.getByRole('button', { name: /Start Download/i })).toBeInTheDocument();
  });
  
  it('should call downloadSongPlaylist when Start Download is clicked', async () => {
    const user = userEvent.setup();
    
    // Mock successful API response
    const mockTaskId = 'test-task-123';
    vi.mocked(api.downloadSongPlaylist).mockResolvedValue({ 
      task_id: mockTaskId, 
      success: true 
    });
    
    render(<DownloadManager songList={sampleSongList} />);
    
    // Click Start Download button
    const startButton = screen.getByText('Start Download');
    await user.click(startButton);
    
    // Check if API was called with correct params
    expect(api.downloadSongPlaylist).toHaveBeenCalledTimes(1);
    expect(api.downloadSongPlaylist).toHaveBeenCalledWith([
      { title: 'Song A', artist: 'Artist X' },
      { title: 'Song B', artist: 'Artist Y' }
    ]);
    
    // Check state changes to downloading
    await waitFor(() => {
      expect(screen.getByText(/Downloading Songs/i)).toBeInTheDocument();
    });
  });
  
  it('should display progress updates from getProgress polling', async () => {
    const user = userEvent.setup();
    vi.useFakeTimers();
    
    // Mock successful API response
    const mockTaskId = 'test-task-123';
    vi.mocked(api.downloadSongPlaylist).mockResolvedValue({ 
      task_id: mockTaskId, 
      success: true 
    });
    
    // Mock progress updates
    const mockProgress: Record<string, api.DownloadProgress> = {
      'Artist X - Song A': {
        song: 'Artist X - Song A',
        status: 'downloading',
        progress: 0.5,
        current: 1,
        total: 2,
        message: 'Downloading...'
      },
      'Artist Y - Song B': {
        song: 'Artist Y - Song B',
        status: 'queued',
        progress: 0,
        current: 0,
        total: 2,
        message: 'Queued'
      }
    };
    
    vi.mocked(api.getProgress).mockResolvedValue(mockProgress);
    
    render(<DownloadManager songList={sampleSongList} />);
    
    // Click Start Download button
    const startButton = screen.getByText('Start Download');
    await user.click(startButton);
    
    // Fast-forward timers to trigger the polling
    vi.advanceTimersByTime(2100);
    
    // Check if the progress is displayed
    await waitFor(() => {
      expect(api.getProgress).toHaveBeenCalledWith(mockTaskId);
      expect(screen.getByText('Downloading')).toBeInTheDocument();
      expect(screen.getByText('Pending')).toBeInTheDocument();
      expect(screen.getByText('0 of 2 complete')).toBeInTheDocument();
    });
  });
  
  it('should display error if downloadSongPlaylist fails', async () => {
    const user = userEvent.setup();
    
    // Mock API error
    const errorMessage = 'Network error';
    vi.mocked(api.downloadSongPlaylist).mockRejectedValue(new Error(errorMessage));
    
    render(<DownloadManager songList={sampleSongList} />);
    
    // Click Start Download button
    const startButton = screen.getByText('Start Download');
    await user.click(startButton);
    
    // Check if error is displayed
    await waitFor(() => {
      expect(screen.getByText('Error')).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });
}); 