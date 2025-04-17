// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PlaylistWorkflow from '../PlaylistWorkflow';
import * as reactHotToast from 'react-hot-toast';
import '@testing-library/jest-dom';

// Mock fetch
global.fetch = vi.fn();

// Mock toast
vi.mock('react-hot-toast', () => ({
  success: vi.fn(),
  error: vi.fn()
}));

describe('PlaylistWorkflow - Image Upload', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    // Reset fetch mock
    fetch.mockReset();
    // Mock successful health check
    fetch.mockImplementationOnce(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'ok' })
      })
    );
  });

  it('should handle image upload successfully', async () => {
    // Create a realistic response based on the actual songs extracted from IMG_5334.jpg
    const mockSongs = [
      { title: 'Golden Oldies', artist: 'R.A. the Rugged Man feat. Atmosphere & ...' },
      { title: 'No Delay', artist: 'Ohmega Watts feat. Surreal' },
      { title: 'No Delay (Instrumental)', artist: 'Ohmega Watts' },
      { title: 'Saywhayusay', artist: 'Ohmega Watts' },
      { title: 'The Find (PPP Remix)', artist: 'Ohmega Watts' },
      { title: 'The Find (PPP Instrumental Remix)', artist: 'Ohmega Watts' },
      { title: 'Intro', artist: 'Specifics' },
      { title: 'My Tunes', artist: 'Specifics' },
      { title: 'Life\'s Work', artist: 'Specifics' }
    ];
    
    // Mock successful API response
    fetch.mockImplementationOnce(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          songs: mockSongs
        })
      })
    );

    render(<PlaylistWorkflow />);

    // Create a mock file that simulates IMG_5334.jpg
    const testFile = new File(['test image content'], 'IMG_5334.jpg', { type: 'image/jpeg' });
    
    // Get the file input
    const fileInput = document.getElementById('file-upload');
    expect(fileInput).toBeTruthy();

    // Simulate file selection
    fireEvent.change(fileInput, { target: { files: [testFile] } });

    // Check loading state is shown
    expect(screen.getByText('Processing your file')).toBeInTheDocument();
    
    // Wait for processing to complete
    await waitFor(() => {
      // Verify success toast was shown
      expect(reactHotToast.success).toHaveBeenCalledWith(`Successfully extracted ${mockSongs.length} songs`);
    });

    // Verify API was called correctly
    expect(fetch).toHaveBeenCalledTimes(2); // Health check + extract API
    
    // Check the second call (extract API)
    const [url, options] = fetch.mock.calls[1];
    expect(url).toContain('/api/extract');
    expect(options.method).toBe('POST');
    
    // Verify the FormData contains the file with the correct name
    const formData = options.body;
    expect(formData instanceof FormData).toBe(true);
    
    // Verify download manager is shown
    expect(screen.getByText('← Back to Upload')).toBeInTheDocument();
  });

  it('should handle API errors gracefully', async () => {
    // Mock error API response
    fetch.mockImplementationOnce(() => 
      Promise.resolve({
        ok: false,
        json: () => Promise.resolve({
          detail: 'Failed to extract songs from image'
        })
      })
    );

    render(<PlaylistWorkflow />);

    // Create a test file with the same name as the real image
    const testFile = new File(['test image content'], 'IMG_5334.jpg', { type: 'image/jpeg' });
    
    // Get the file input
    const fileInput = document.getElementById('file-upload');
    
    // Simulate file selection
    fireEvent.change(fileInput, { target: { files: [testFile] } });
    
    // Wait for error message to appear
    await waitFor(() => {
      // Verify error toast was shown
      expect(reactHotToast.error).toHaveBeenCalledWith('Failed to extract songs from image');
    });
    
    // Check if error message is displayed
    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('Failed to extract songs from image')).toBeInTheDocument();
  });

  it('should handle no songs found gracefully', async () => {
    // Mock API response with no songs
    fetch.mockImplementationOnce(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          songs: []
        })
      })
    );

    render(<PlaylistWorkflow />);

    // Create a test file with the same name as the real image
    const testFile = new File(['test image content'], 'IMG_5334.jpg', { type: 'image/jpeg' });
    
    // Get the file input
    const fileInput = document.getElementById('file-upload');
    
    // Simulate file selection
    fireEvent.change(fileInput, { target: { files: [testFile] } });
    
    // Wait for error message to appear
    await waitFor(() => {
      // Verify error toast was shown
      expect(reactHotToast.error).toHaveBeenCalledWith('No songs could be extracted from the provided file');
    });
    
    // Check if error message is displayed
    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('No songs could be extracted from the provided file')).toBeInTheDocument();
  });
}); 