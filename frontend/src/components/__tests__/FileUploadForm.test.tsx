import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event'; // Use userEvent for more realistic interactions
import FileUploadForm from '../FileUploadForm';
import * as api from '@/lib/api'; // Import all exports from api module
import toast from 'react-hot-toast'; // We might need to mock this too

// Mock the entire api module
vi.mock('@/lib/api');
// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
  __esModule: true, // Important for mocking default exports
}));

describe('FileUploadForm', () => {
  let mockOnSongsExtracted: ReturnType<typeof vi.fn>;
  let mockExtractSongsFromFile: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks();
    
    // Setup specific mock implementation for extractSongsFromFile
    mockExtractSongsFromFile = vi.mocked(api.extractSongsFromFile);
    
    // Mock the callback prop
    mockOnSongsExtracted = vi.fn();
  });

  it('should render the form correctly', () => {
    render(<FileUploadForm onSongsExtracted={mockOnSongsExtracted} />);

    expect(screen.getByText(/Upload your playlist/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /browse/i })).toBeInTheDocument(); // Assuming input is styled like a button
    expect(screen.getByRole('button', { name: /upload file/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload file/i })).toBeDisabled(); // Initially disabled
  });

  it('should enable upload button when a file is selected', async () => {
    render(<FileUploadForm onSongsExtracted={mockOnSongsExtracted} />);
    const user = userEvent.setup();

    const fileInput = screen.getByLabelText(/browse/i, { selector: 'input[type="file"]' }); // Find the hidden input
    const file = new File(['song1\nsong2'], 'playlist.png', { type: 'image/png' });

    await user.upload(fileInput, file);

    expect(screen.getByRole('button', { name: /upload file/i })).toBeEnabled();
  });

  it('should call extractSongsFromFile and onSongsExtracted on successful upload', async () => {
    // Arrange: Mock API success response
    const mockSongs = [
      { id: '1', title: 'Song One', artist: 'Artist A' },
      { id: '2', title: 'Song Two', artist: 'Artist B' },
    ];
    mockExtractSongsFromFile.mockResolvedValue(mockSongs);
    
    render(<FileUploadForm onSongsExtracted={mockOnSongsExtracted} />);
    const user = userEvent.setup();

    // Act: Select file and click upload
    const fileInput = screen.getByLabelText(/browse/i, { selector: 'input[type="file"]' });
    const file = new File(['content'], 'image.jpg', { type: 'image/jpeg' });
    await user.upload(fileInput, file);
    const uploadButton = screen.getByRole('button', { name: /upload file/i });
    await user.click(uploadButton);

    // Assert
    // Check if API was called
    expect(mockExtractSongsFromFile).toHaveBeenCalledTimes(1);
    expect(mockExtractSongsFromFile).toHaveBeenCalledWith(file); 

    // Check if loading state was shown (button text changes)
    expect(screen.getByRole('button', { name: /processing/i })).toBeInTheDocument();

    // Wait for promises to resolve and check results
    await waitFor(() => {
      // Check if success toast was called
      expect(toast.success).toHaveBeenCalledWith(`Found ${mockSongs.length} songs in your file`);
    });
    await waitFor(() => {
       // Check if callback was called with formatted string
      const expectedString = mockSongs.map(s => `${s.title},${s.artist}`).join('\n');
      expect(mockOnSongsExtracted).toHaveBeenCalledTimes(1);
      expect(mockOnSongsExtracted).toHaveBeenCalledWith(expectedString);
    });
    
    // Check if button is enabled again and not showing error
    expect(screen.getByRole('button', { name: /upload file/i })).toBeEnabled();
    expect(screen.queryByText(/No songs could be extracted/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/failed to upload/i)).not.toBeInTheDocument();
  });

  it('should display error message if upload fails', async () => {
    // Arrange: Mock API failure
    const errorMessage = 'Backend Error: Extraction failed';
    mockExtractSongsFromFile.mockRejectedValue(new Error(errorMessage));

    render(<FileUploadForm onSongsExtracted={mockOnSongsExtracted} />);
    const user = userEvent.setup();

    // Act: Select file and click upload
    const fileInput = screen.getByLabelText(/browse/i, { selector: 'input[type="file"]' });
    const file = new File(['content'], 'image.pdf', { type: 'application/pdf' });
    await user.upload(fileInput, file);
    const uploadButton = screen.getByRole('button', { name: /upload file/i });
    await user.click(uploadButton);

    // Assert
    expect(mockExtractSongsFromFile).toHaveBeenCalledTimes(1);
    
    // Wait for error to be displayed
    await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    // Check callback was NOT called
    expect(mockOnSongsExtracted).not.toHaveBeenCalled();
    // Check button is enabled again
    expect(screen.getByRole('button', { name: /upload file/i })).toBeEnabled();
  });

   it('should display error message if no songs are extracted', async () => {
    // Arrange: Mock API success with empty array
    mockExtractSongsFromFile.mockResolvedValue([]); 
    
    render(<FileUploadForm onSongsExtracted={mockOnSongsExtracted} />);
    const user = userEvent.setup();

    // Act: Select file and click upload
    const fileInput = screen.getByLabelText(/browse/i, { selector: 'input[type="file"]' });
    const file = new File(['content'], 'empty.png', { type: 'image/png' });
    await user.upload(fileInput, file);
    const uploadButton = screen.getByRole('button', { name: /upload file/i });
    await user.click(uploadButton);

    // Assert
    expect(mockExtractSongsFromFile).toHaveBeenCalledTimes(1);
    
    // Wait for error to be displayed
    await waitFor(() => {
        expect(screen.getByText(/No songs could be extracted from the file/i)).toBeInTheDocument();
    });

    // Check callback was NOT called
    expect(mockOnSongsExtracted).not.toHaveBeenCalled();
    expect(toast.success).not.toHaveBeenCalled();
    // Check button is enabled again
    expect(screen.getByRole('button', { name: /upload file/i })).toBeEnabled();
  });

}); 