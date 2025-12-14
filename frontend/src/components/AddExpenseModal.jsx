import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import './AddExpenseModal.css';

function AddExpenseModal({ isOpen, onClose, onExpenseAdded, apiUrl }) {
  const { getAuthHeader } = useAuth();
  const [mode, setMode] = useState(null); // null | 'voice' | 'screenshot' | 'photo'
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcription, setTranscription] = useState('');
  const [imagePreview, setImagePreview] = useState(null);
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [useSpeechRecognition, setUseSpeechRecognition] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [bulkProgress, setBulkProgress] = useState({ current: 0, total: 0, successes: 0, failures: 0 });
  const [processedFiles, setProcessedFiles] = useState([]);
  const recognitionRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const finalTranscriptRef = useRef('');
  const fileInputRef = useRef(null);
  const bulkFileInputRef = useRef(null);

  // Reset when modal closes
  useEffect(() => {
    if (!isOpen) {
      cleanup();
      setMode(null);
    }
  }, [isOpen]);

  // Auto-start actions when modes are selected
  useEffect(() => {
    if (mode === 'voice' && !isRecording && !isProcessing) {
      startRecording();
    } else if (mode === 'screenshot' && !imagePreview && !isProcessing) {
      captureScreenshot();
    } else if (mode === 'photo' && !imagePreview && !isProcessing) {
      // Trigger file picker
      setTimeout(() => {
        fileInputRef.current?.click();
      }, 100);
    } else if (mode === 'bulk' && selectedFiles.length === 0 && !isProcessing) {
      // Trigger bulk file picker
      setTimeout(() => {
        bulkFileInputRef.current?.click();
      }, 100);
    }
  }, [mode]);

  // Paste from clipboard listener
  useEffect(() => {
    if (!isOpen) return;

    const handlePaste = async (e) => {
      const items = e.clipboardData?.items;
      if (!items) return;

      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          e.preventDefault();
          const file = items[i].getAsFile();
          if (file) {
            // Switch to photo mode if in mode selection
            if (mode === null) {
              setMode('photo');
            }
            setImagePreview(URL.createObjectURL(file));
            await processImage(file);
          }
          break;
        }
      }
    };

    document.addEventListener('paste', handlePaste);
    return () => document.removeEventListener('paste', handlePaste);
  }, [isOpen, mode]);

  const cleanup = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }
    audioChunksRef.current = [];
    setIsRecording(false);
    setIsProcessing(false);
    setTranscription('');
    setImagePreview(null);
    setError(null);
    finalTranscriptRef.current = '';
    setSelectedFiles([]);
    setBulkProgress({ current: 0, total: 0, successes: 0, failures: 0 });
    setProcessedFiles([]);
  };

  // ==================== VOICE RECORDING ====================

  const startRecording = async () => {
    try {
      setError(null);
      setTranscription('');
      finalTranscriptRef.current = '';

      // Check if Web Speech Recognition is available (Chrome, Edge)
      if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        setUseSpeechRecognition(true);
        await startSpeechRecognition();
      } else {
        // Fallback to MediaRecorder for Safari and other browsers
        setUseSpeechRecognition(false);
        await startMediaRecorder();
      }
    } catch (err) {
      setError(`Failed to start recording: ${err.message}`);
      console.error('Error starting recording:', err);
    }
  };

  const startSpeechRecognition = async () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = finalTranscriptRef.current;

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }

      finalTranscriptRef.current = finalTranscript;
      setTranscription(finalTranscript + interimTranscript);
    };

    recognition.onerror = (event) => {
      if (event.error !== 'no-speech') {
        console.error('Speech recognition error:', event.error);
        setError(`Speech recognition error: ${event.error}`);
      }
    };

    recognition.onend = () => {
      if (isRecording && recognitionRef.current) {
        recognitionRef.current.start();
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsRecording(true);
  };

  const startMediaRecorder = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        stream.getTracks().forEach(track => track.stop());
        await transcribeAudio(audioBlob);
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setIsRecording(true);
      setTranscription('Recording...');
    } catch (err) {
      setError(`Microphone access denied: ${err.message}`);
      throw err;
    }
  };

  const stopRecording = async () => {
    setIsRecording(false);

    if (useSpeechRecognition && recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;

      const finalText = finalTranscriptRef.current.trim();
      if (finalText) {
        await processTranscription(finalText);
      }
    } else if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  };

  const transcribeAudio = async (audioBlob) => {
    try {
      setIsProcessing(true);
      setError(null);
      setTranscription('Transcribing audio...');

      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      const response = await fetch(`${apiUrl}/api/transcribe-audio`, {
        method: 'POST',
        headers: getAuthHeader(),
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to transcribe audio');
      }

      const data = await response.json();

      if (data.transcription) {
        setTranscription(data.transcription);
        await processTranscription(data.transcription);
      } else {
        throw new Error('No transcription received');
      }
    } catch (err) {
      setError(err.message);
      console.error('Error transcribing audio:', err);
      setIsProcessing(false);
    }
  };

  const processTranscription = async (text) => {
    try {
      setIsProcessing(true);
      setError(null);

      const response = await fetch(`${apiUrl}/api/transcribe?transcription=${encodeURIComponent(text)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to process transcription');
      }

      const data = await response.json();

      // Display warning if token limit exceeded
      if (data.warning) {
        console.warn('Token limit warning:', data.warning);
        setError(`Warning: ${data.warning}. Consider shortening your custom context in Settings.`);
      }

      if (data.parsed_expense) {
        await createExpense(data.parsed_expense);
      } else {
        throw new Error('Could not parse expense from transcription');
      }
    } catch (err) {
      setError(err.message);
      console.error('Error processing transcription:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  // ==================== DRAG AND DROP ====================

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget === e.target) {
      setIsDragging(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];

      // Validate file type
      if (!file.type.startsWith('image/')) {
        setError('Please drop an image file');
        return;
      }

      // Validate file size (max 15MB)
      if (file.size > 15 * 1024 * 1024) {
        setError('Image too large. Please use an image under 15MB');
        return;
      }

      // If not in a specific mode, switch to photo mode
      if (mode === null) {
        setMode('photo');
      }

      setImagePreview(URL.createObjectURL(file));
      await processImage(file);
    }
  };

  // ==================== IMAGE PROCESSING ====================

  const captureScreenshot = async () => {
    try {
      setIsProcessing(true);
      setError(null);

      // Request screen capture permission
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { mediaSource: 'screen' }
      });

      // Create video element to capture frame
      const video = document.createElement('video');
      video.srcObject = stream;
      video.onloadedmetadata = () => {
        video.play();

        // Wait for first frame
        setTimeout(() => {
          // Capture frame to canvas
          const canvas = document.createElement('canvas');
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(video, 0, 0);

          // Stop the stream
          stream.getTracks().forEach(track => track.stop());

          // Convert to blob
          canvas.toBlob(async (blob) => {
            setImagePreview(URL.createObjectURL(blob));
            setIsProcessing(false);
            await processImage(blob);
          }, 'image/png');
        }, 100);
      };
    } catch (error) {
      console.error('Screenshot capture failed:', error);
      if (error.name === 'NotAllowedError') {
        setError('Screen capture permission denied');
      } else {
        setError('Failed to capture screenshot');
      }
      setIsProcessing(false);
    }
  };

  const handlePhotoUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select an image file');
      return;
    }

    // Validate file size (max 15MB)
    if (file.size > 15 * 1024 * 1024) {
      setError('Image too large. Please select an image under 15MB');
      return;
    }

    setImagePreview(URL.createObjectURL(file));
    await processImage(file);
  };

  const processImage = async (imageBlob) => {
    try {
      setIsProcessing(true);
      setError(null);

      // Upload image to backend
      const formData = new FormData();
      formData.append('image', imageBlob, 'expense-image.png');

      const response = await fetch(`${apiUrl}/api/process-image`, {
        method: 'POST',
        headers: getAuthHeader(),
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to process image');
      }

      const data = await response.json();

      // Display warning if token limit exceeded
      if (data.warning) {
        console.warn('Token limit warning:', data.warning);
        setError(`Warning: ${data.warning}`);
      }

      if (data.parsed_expense) {
        await createExpense(data.parsed_expense);
      } else {
        throw new Error('Could not extract expense from image');
      }
    } catch (err) {
      setError(err.message);
      console.error('Error processing image:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  // ==================== BULK UPLOAD ====================

  const handleBulkFileSelect = async (event) => {
    const files = Array.from(event.target.files || []);

    // Filter and validate
    const imageFiles = files.filter(file => file.type.startsWith('image/'));
    const validFiles = imageFiles.filter(file => file.size <= 15 * 1024 * 1024);

    if (validFiles.length === 0) {
      setError('No valid images selected. Please select image files under 15MB each.');
      return;
    }

    if (validFiles.length < files.length) {
      setError(`${files.length - validFiles.length} files skipped (not images or too large)`);
    } else {
      setError(null);
    }

    setSelectedFiles(validFiles);
    await processBulkUpload(validFiles);
  };

  const processBulkUpload = async (files) => {
    setIsProcessing(true);
    setBulkProgress({ current: 0, total: files.length, successes: 0, failures: 0 });
    setProcessedFiles([]);

    const results = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setBulkProgress(prev => ({ ...prev, current: i + 1 }));

      try {
        // Process single image
        const formData = new FormData();
        formData.append('image', file, file.name);

        const response = await fetch(`${apiUrl}/api/process-image`, {
          method: 'POST',
          headers: getAuthHeader(),
          body: formData
        });

        if (!response.ok) {
          throw new Error('Failed to process image');
        }

        const data = await response.json();

        if (data.parsed_expense) {
          // Create expense
          const expenseResponse = await fetch(`${apiUrl}/api/expenses`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...getAuthHeader(),
            },
            body: JSON.stringify(data.parsed_expense),
          });

          if (expenseResponse.ok) {
            const newExpense = await expenseResponse.json();
            results.push({ file: file.name, success: true, expense: newExpense });
            setBulkProgress(prev => ({ ...prev, successes: prev.successes + 1 }));
          } else {
            throw new Error('Failed to create expense');
          }
        } else {
          throw new Error('No expense data extracted');
        }
      } catch (error) {
        console.error(`Failed to process ${file.name}:`, error);
        results.push({ file: file.name, success: false, error: error.message });
        setBulkProgress(prev => ({ ...prev, failures: prev.failures + 1 }));
      }

      setProcessedFiles([...results]);
    }

    setIsProcessing(false);

    // Notify parent to refresh expense list
    if (results.some(r => r.success)) {
      onExpenseAdded();
    }
  };

  // ==================== COMMON ====================

  const createExpense = async (expenseData) => {
    try {
      const response = await fetch(`${apiUrl}/api/expenses`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify(expenseData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create expense');
      }

      const newExpense = await response.json();
      onExpenseAdded(newExpense);
      onClose();
    } catch (err) {
      setError(err.message);
      console.error('Error creating expense:', err);
    }
  };

  const handleBack = () => {
    cleanup();
    setMode(null);
  };

  if (!isOpen) return null;

  // ==================== MODE SELECTION SCREEN ====================

  if (mode === null) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div
          className={`modal-content mode-selection ${isDragging ? 'dragging' : ''}`}
          onClick={(e) => e.stopPropagation()}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          <button className="modal-close" onClick={onClose}>&times;</button>
          <h2>Add Expense</h2>
          <p className="modal-subtitle">{isDragging ? 'Drop image here' : 'Choose how to add your expense'}</p>

          {isDragging && (
            <div className="drag-overlay">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                <circle cx="12" cy="13" r="4"></circle>
              </svg>
              <p>Drop receipt image</p>
            </div>
          )}

          <div className="mode-buttons" style={{ opacity: isDragging ? 0.3 : 1 }}>
            <button onClick={() => setMode('voice')} className="mode-button">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
              </svg>
              <span>Voice</span>
              <p className="mode-description">Speak your expense</p>
            </button>

            <button onClick={() => setMode('screenshot')} className="mode-button">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                <polyline points="21 15 16 10 5 21"></polyline>
              </svg>
              <span>Screenshot</span>
              <p className="mode-description">Capture screen</p>
            </button>

            <button onClick={() => setMode('photo')} className="mode-button">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                <circle cx="12" cy="13" r="4"></circle>
              </svg>
              <span>Photo</span>
              <p className="mode-description">Upload receipt</p>
            </button>

            <button onClick={() => setMode('bulk')} className="mode-button mode-button-wide">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <path d="M12 18v-6"></path>
                <path d="M9 15l3 3 3-3"></path>
              </svg>
              <span>Bulk Upload</span>
              <p className="mode-description">Multiple receipts</p>
            </button>
          </div>

          <div className="quick-actions-hint">
            <p>💡 Quick tips:</p>
            <ul>
              <li>Drag & drop an image anywhere on this window</li>
              <li>Press <kbd>Ctrl</kbd>+<kbd>V</kbd> (or <kbd>⌘</kbd>+<kbd>V</kbd>) to paste from clipboard</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  // ==================== VOICE MODE ====================

  if (mode === 'voice') {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <button className="modal-close" onClick={onClose}>&times;</button>
          <button className="modal-back" onClick={handleBack}>← Back</button>

          <h2>Voice Recording</h2>
          <p className="modal-subtitle">Describe your expense</p>

          <div className="modal-recording-section">
            <div className={`recording-visualizer ${isRecording ? 'active' : ''}`}>
              <div className="pulse-ring"></div>
              <div className="pulse-ring delay-1"></div>
              <div className="pulse-ring delay-2"></div>
            </div>

            {transcription && (
              <div className="modal-transcription">
                <p>{transcription}</p>
              </div>
            )}

            {error && (
              <div className="modal-error">
                {error}
              </div>
            )}

            <div className="modal-actions">
              {isProcessing ? (
                <div className="processing-indicator">Processing...</div>
              ) : isRecording ? (
                <button className="stop-button" onClick={stopRecording}>
                  Stop Recording
                </button>
              ) : (
                <button className="start-button" onClick={startRecording}>
                  Start Recording
                </button>
              )}
            </div>
          </div>

          <div className="modal-hint">
            Example: "Lunch at Joe's for $25"
          </div>
        </div>
      </div>
    );
  }

  // ==================== SCREENSHOT MODE ====================

  if (mode === 'screenshot') {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div
          className={`modal-content ${isDragging ? 'dragging' : ''}`}
          onClick={(e) => e.stopPropagation()}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          <button className="modal-close" onClick={onClose}>&times;</button>
          <button className="modal-back" onClick={handleBack}>← Back</button>

          <h2>Screenshot Capture</h2>
          <p className="modal-subtitle">{isDragging ? 'Drop image here' : 'Capture a receipt or invoice'}</p>

          {isDragging && (
            <div className="drag-overlay">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                <polyline points="21 15 16 10 5 21"></polyline>
              </svg>
              <p>Drop screenshot</p>
            </div>
          )}

          <div className="modal-image-section" style={{ opacity: isDragging ? 0.3 : 1 }}>
            {imagePreview && (
              <div className="image-preview-container">
                <img src={imagePreview} alt="Captured screenshot" className="image-preview" />
              </div>
            )}

            {error && (
              <div className="modal-error">
                {error}
              </div>
            )}

            <div className="modal-actions">
              {isProcessing ? (
                <div className="processing-indicator">
                  <div className="spinner"></div>
                  <p>Processing image...</p>
                </div>
              ) : imagePreview ? (
                <button className="retry-button" onClick={() => { setImagePreview(null); captureScreenshot(); }}>
                  Capture Again
                </button>
              ) : (
                <button className="capture-button" onClick={captureScreenshot}>
                  Capture Screenshot
                </button>
              )}
            </div>
          </div>

          <div className="modal-hint">
            Select screen/window to capture, or paste an existing screenshot
          </div>
        </div>
      </div>
    );
  }

  // ==================== PHOTO MODE ====================

  if (mode === 'photo') {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div
          className={`modal-content ${isDragging ? 'dragging' : ''}`}
          onClick={(e) => e.stopPropagation()}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          <button className="modal-close" onClick={onClose}>&times;</button>
          <button className="modal-back" onClick={handleBack}>← Back</button>

          <h2>Upload Photo</h2>
          <p className="modal-subtitle">{isDragging ? 'Drop image here' : 'Upload a receipt or invoice'}</p>

          {isDragging && (
            <div className="drag-overlay">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                <circle cx="12" cy="13" r="4"></circle>
              </svg>
              <p>Drop receipt image</p>
            </div>
          )}

          <div className="modal-image-section" style={{ opacity: isDragging ? 0.3 : 1 }}>
            {imagePreview && (
              <div className="image-preview-container">
                <img src={imagePreview} alt="Uploaded photo" className="image-preview" />
              </div>
            )}

            {error && (
              <div className="modal-error">
                {error}
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handlePhotoUpload}
              style={{ display: 'none' }}
            />

            <div className="modal-actions">
              {isProcessing ? (
                <div className="processing-indicator">
                  <div className="spinner"></div>
                  <p>Processing image...</p>
                </div>
              ) : imagePreview ? (
                <button className="retry-button" onClick={() => { setImagePreview(null); fileInputRef.current.click(); }}>
                  Choose Different Photo
                </button>
              ) : (
                <button className="upload-button" onClick={() => fileInputRef.current.click()}>
                  Choose Photo
                </button>
              )}
            </div>
          </div>

          <div className="modal-hint">
            Select a photo, drag & drop, or paste from clipboard
          </div>
        </div>
      </div>
    );
  }

  // ==================== BULK UPLOAD MODE ====================

  if (mode === 'bulk') {
    return (
      <div className="modal-overlay" onClick={(e) => { if (!isProcessing) onClose(); }}>
        <div className="modal-content bulk-upload" onClick={(e) => e.stopPropagation()}>
          <button className="modal-close" onClick={onClose}>&times;</button>
          <button className="modal-back" onClick={handleBack}>← Back</button>

          <h2>Bulk Upload</h2>
          <p className="modal-subtitle">Upload multiple receipts at once</p>

          <div className="bulk-upload-section">
            {selectedFiles.length === 0 ? (
              <div className="bulk-empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
                <p>No files selected</p>
                <button onClick={() => bulkFileInputRef.current?.click()}>
                  Choose Images
                </button>
              </div>
            ) : (
              <div className="bulk-processing">
                <div className="bulk-stats">
                  <p>Processing {bulkProgress.current} of {bulkProgress.total}</p>
                  <div className="stats-row">
                    <span className="success">✓ {bulkProgress.successes} created</span>
                    {bulkProgress.failures > 0 && (
                      <span className="failure">✗ {bulkProgress.failures} failed</span>
                    )}
                  </div>
                </div>

                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${(bulkProgress.current / bulkProgress.total) * 100}%` }}
                  ></div>
                </div>

                <div className="file-list">
                  {processedFiles.map((result, idx) => (
                    <div key={idx} className={`file-item ${result.success ? 'success' : 'failure'}`}>
                      <span className="file-name">{result.file}</span>
                      <span className="file-status">
                        {result.success ? '✓' : '✗'}
                      </span>
                    </div>
                  ))}
                  {selectedFiles.slice(processedFiles.length).map((file, idx) => (
                    <div key={idx + processedFiles.length} className="file-item pending">
                      <span className="file-name">{file.name}</span>
                      <span className="file-status">...</span>
                    </div>
                  ))}
                </div>

                {!isProcessing && (
                  <div className="bulk-actions">
                    <button onClick={() => { setSelectedFiles([]); setProcessedFiles([]); bulkFileInputRef.current?.click(); }}>
                      Upload More
                    </button>
                    <button onClick={onClose} className="done-button">
                      Done
                    </button>
                  </div>
                )}
              </div>
            )}

            <input
              ref={bulkFileInputRef}
              type="file"
              accept="image/*"
              multiple
              onChange={handleBulkFileSelect}
              style={{ display: 'none' }}
            />
          </div>

          <div className="modal-hint">
            Select multiple images to process them all at once
          </div>
        </div>
      </div>
    );
  }

  return null;
}

export default AddExpenseModal;
