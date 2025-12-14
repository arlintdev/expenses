import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import './RecordingModal.css';

function RecordingModal({ isOpen, onClose, onExpenseAdded, apiUrl }) {
  const { getAuthHeader } = useAuth();
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcription, setTranscription] = useState('');
  const [error, setError] = useState(null);
  const recognitionRef = useRef(null);
  const finalTranscriptRef = useRef('');

  useEffect(() => {
    if (isOpen) {
      startRecording();
    } else {
      cleanup();
    }
  }, [isOpen]);

  const cleanup = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsRecording(false);
    setIsProcessing(false);
    setTranscription('');
    setError(null);
    finalTranscriptRef.current = '';
  };

  const startRecording = async () => {
    try {
      setError(null);
      setTranscription('');
      finalTranscriptRef.current = '';

      if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
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
      } else {
        setError('Speech recognition is not supported in this browser.');
      }
    } catch (err) {
      setError(`Failed to start recording: ${err.message}`);
      console.error('Error starting recording:', err);
    }
  };

  const stopRecording = async () => {
    setIsRecording(false);
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;

      const finalText = finalTranscriptRef.current.trim();
      if (finalText) {
        await processTranscription(finalText);
      }
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

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>&times;</button>

        <h2>Add Expense</h2>
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

export default RecordingModal;
