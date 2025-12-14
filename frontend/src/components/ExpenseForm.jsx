import { useState, useRef } from 'react';
import './ExpenseForm.css';

function ExpenseForm({ onExpenseAdded, apiUrl }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcription, setTranscription] = useState('');
  const [error, setError] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recognitionRef = useRef(null);
  const finalTranscriptRef = useRef('');

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
        setError('Speech recognition is not supported in this browser. Please use Chrome or Edge.');
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
        },
        body: JSON.stringify(expenseData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create expense');
      }

      const newExpense = await response.json();
      onExpenseAdded(newExpense);
      setTranscription('');
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error creating expense:', err);
    }
  };

  return (
    <div className="expense-form">
      <div className="form-header">
        <h2>Add Expense</h2>
        <p>Click the microphone and describe your expense</p>
      </div>

      <div className="recording-section">
        <button
          className={`mic-button ${isRecording ? 'recording' : ''} ${isProcessing ? 'processing' : ''}`}
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isProcessing}
        >
          {isProcessing ? (
            <span className="processing-spinner">⏳</span>
          ) : isRecording ? (
            <span className="mic-icon recording-icon">⏹</span>
          ) : (
            <span className="mic-icon">🎤</span>
          )}
        </button>

        <div className="recording-status">
          {isRecording && <span className="status-badge recording">Recording...</span>}
          {isProcessing && <span className="status-badge processing">Processing...</span>}
        </div>
      </div>

      {transcription && (
        <div className="transcription-display">
          <h3>Transcription:</h3>
          <p>{transcription}</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>&times;</button>
        </div>
      )}

      <div className="instructions">
        <h3>Example:</h3>
        <p>"Lunch at Joe's Diner for $25 on December 10th"</p>
        <p>"Office supplies for Marketing team, $150"</p>
      </div>
    </div>
  );
}

export default ExpenseForm;
