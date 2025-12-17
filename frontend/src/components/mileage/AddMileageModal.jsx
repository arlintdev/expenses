import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import TagInput from '../TagInput';
import './AddMileageModal.css';

function AddMileageModal({ isOpen, onClose, onMileageAdded, apiUrl }) {
  const { getAuthHeader } = useAuth();
  const [mode, setMode] = useState(null); // null | 'voice' | 'photo' | 'manual'
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcription, setTranscription] = useState('');
  const [imagePreview, setImagePreview] = useState(null);
  const [error, setError] = useState(null);
  const [useSpeechRecognition, setUseSpeechRecognition] = useState(false);
  const [confirmationData, setConfirmationData] = useState(null);
  const [vehicles, setVehicles] = useState([]);
  const [availableTags, setAvailableTags] = useState([]);
  const [currentIRSRate, setCurrentIRSRate] = useState(0.67);

  const recognitionRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const finalTranscriptRef = useRef('');
  const fileInputRef = useRef(null);

  // Manual form state
  const [formData, setFormData] = useState({
    vehicle_id: '',
    date: new Date().toISOString().split('T')[0],
    purpose: '',
    odometer_start: '',
    odometer_end: '',
    personal_miles: '0',
    tags: []
  });

  // Reset when modal closes
  useEffect(() => {
    if (!isOpen) {
      cleanup();
      setMode(null);
    }
  }, [isOpen]);

  // Fetch vehicles and IRS rate when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchVehicles();
      fetchAvailableTags();
      fetchCurrentIRSRate();
    }
  }, [isOpen]);

  // Auto-start actions when modes are selected
  useEffect(() => {
    if (mode === 'voice' && !isRecording && !isProcessing) {
      startRecording();
    } else if (mode === 'photo' && !imagePreview && !isProcessing) {
      setTimeout(() => {
        fileInputRef.current?.click();
      }, 100);
    }
  }, [mode]);

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
    setConfirmationData(null);
    setFormData({
      vehicle_id: '',
      date: new Date().toISOString().split('T')[0],
      purpose: '',
      odometer_start: '',
      odometer_end: '',
      personal_miles: '0',
      tags: []
    });
  };

  const fetchVehicles = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/vehicles`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        setVehicles(data);
        if (data.length > 0 && !formData.vehicle_id) {
          const firstVehicle = data[0];
          setFormData(prev => ({
            ...prev,
            vehicle_id: firstVehicle.id,
            odometer_start: firstVehicle.last_odometer_reading || ''
          }));
        }
      }
    } catch (err) {
      console.error('Error fetching vehicles:', err);
    }
  };

  // Auto-populate odometer_start when vehicle changes
  const handleVehicleChange = (vehicleId) => {
    const selectedVehicle = vehicles.find(v => v.id === vehicleId);
    handleFormChange('vehicle_id', vehicleId);
    if (selectedVehicle && selectedVehicle.last_odometer_reading) {
      handleFormChange('odometer_start', selectedVehicle.last_odometer_reading.toString());
    }
  };

  const fetchAvailableTags = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/user-tags`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        setAvailableTags(data.map(tag => tag.name).sort());
      }
    } catch (err) {
      console.error('Error fetching tags:', err);
    }
  };

  const fetchCurrentIRSRate = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/irs-rates/current`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        setCurrentIRSRate(data.rate);
      }
    } catch (err) {
      console.error('Error fetching IRS rate:', err);
    }
  };

  // ==================== VOICE RECORDING ====================

  const startRecording = async () => {
    try {
      setError(null);
      setTranscription('');
      finalTranscriptRef.current = '';

      if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        setUseSpeechRecognition(true);
        await startSpeechRecognition();
      } else {
        setError('Voice recording is only supported on Chrome and Edge browsers. Please use Photo upload or Manual entry instead.');
        setIsRecording(false);
        return;
      }
    } catch (err) {
      console.error('Error starting recording:', err);
      setError(err.message);
      setIsRecording(false);
    }
  };

  const startSpeechRecognition = async () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsRecording(true);
      setError(null);
    };

    recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }

      if (finalTranscript) {
        finalTranscriptRef.current += finalTranscript;
      }

      setTranscription(finalTranscriptRef.current + interimTranscript);
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      setError(`Recording error: ${event.error}`);
      setIsRecording(false);
    };

    recognition.onend = () => {
      setIsRecording(false);
      if (finalTranscriptRef.current.trim()) {
        processTranscription(finalTranscriptRef.current.trim());
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  };

  const processTranscription = async (text) => {
    setIsProcessing(true);
    setError(null);

    try {
      // For now, just set the text in the purpose field and show confirmation
      // In a full implementation, you'd call a backend endpoint to parse the mileage data
      setConfirmationData({
        purpose: text,
        vehicle_id: formData.vehicle_id,
        date: formData.date,
        odometer_start: '',
        odometer_end: '',
        personal_miles: 0,
        tags: []
      });
    } catch (err) {
      setError(err.message || 'Failed to process voice input');
    } finally {
      setIsProcessing(false);
    }
  };

  // ==================== IMAGE PROCESSING ====================

  const processImage = async (file) => {
    setIsProcessing(true);
    setError(null);

    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64Data = e.target.result.split(',')[1];

        // For now, just show confirmation with empty data
        // In a full implementation, you'd call backend to OCR the image
        setConfirmationData({
          purpose: 'Image uploaded - enter details',
          vehicle_id: formData.vehicle_id,
          date: formData.date,
          odometer_start: '',
          odometer_end: '',
          personal_miles: 0,
          tags: []
        });
        setIsProcessing(false);
      };
      reader.readAsDataURL(file);
    } catch (err) {
      setError(err.message || 'Failed to process image');
      setIsProcessing(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImagePreview(URL.createObjectURL(file));
      processImage(file);
    }
  };

  // ==================== FORM SUBMISSION ====================

  const calculateBusinessMiles = () => {
    const start = parseInt(formData.odometer_start) || 0;
    const end = parseInt(formData.odometer_end) || 0;
    const personal = parseInt(formData.personal_miles) || 0;
    return Math.max(0, end - start - personal);
  };

  const calculateDeduction = () => {
    return calculateBusinessMiles() * currentIRSRate;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const dataToSubmit = confirmationData || formData;

    if (!dataToSubmit.vehicle_id) {
      setError('Please select a vehicle');
      return;
    }

    if (!dataToSubmit.purpose.trim()) {
      setError('Please enter a purpose');
      return;
    }

    const start = parseInt(dataToSubmit.odometer_start);
    const end = parseInt(dataToSubmit.odometer_end);
    const personal = parseInt(dataToSubmit.personal_miles) || 0;

    if (isNaN(start) || isNaN(end)) {
      setError('Please enter valid odometer readings');
      return;
    }

    if (end <= start) {
      setError('Ending odometer must be greater than starting odometer');
      return;
    }

    if (personal > (end - start)) {
      setError('Personal miles cannot exceed total trip miles');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/api/mileage-logs`, {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          vehicle_id: dataToSubmit.vehicle_id,
          date: new Date(dataToSubmit.date).toISOString(),
          purpose: dataToSubmit.purpose,
          odometer_start: start,
          odometer_end: end,
          personal_miles: personal,
          tags: dataToSubmit.tags || []
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create mileage log');
      }

      const newLog = await response.json();
      onMileageAdded(newLog);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFormChange = (field, value) => {
    if (confirmationData) {
      setConfirmationData({ ...confirmationData, [field]: value });
    } else {
      setFormData({ ...formData, [field]: value });
    }
  };

  if (!isOpen) return null;

  const businessMiles = calculateBusinessMiles();
  const deduction = calculateDeduction();
  const currentData = confirmationData || formData;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content mileage-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add Mileage Log</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        {!mode ? (
          <div className="mode-selection">
            <button className="mode-button" onClick={() => setMode('voice')}>
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
              </svg>
              <span>Voice</span>
            </button>

            <button className="mode-button" onClick={() => setMode('photo')}>
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/>
              </svg>
              <span>Photo</span>
            </button>

            <button className="mode-button" onClick={() => setMode('manual')}>
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
              </svg>
              <span>Manual</span>
            </button>
          </div>
        ) : mode === 'voice' && !confirmationData ? (
          <div className="recording-mode">
            {isRecording && (
              <div className="recording-indicator">
                <div className="pulse-circle"></div>
                <p>Listening... Speak your mileage details</p>
                <p className="hint">Example: "Material pickup at Lowes for roofing job. Odometer start 15,500, end 15,600. Personal use 10 miles."</p>
              </div>
            )}

            {transcription && (
              <div className="transcription-box">
                <h3>Transcription:</h3>
                <p>{transcription}</p>
              </div>
            )}

            {error && <div className="error-message">{error}</div>}

            <div className="modal-actions">
              {isRecording ? (
                <button className="stop-button" onClick={stopRecording}>
                  Stop Recording
                </button>
              ) : (
                <button className="back-button" onClick={() => setMode(null)}>
                  Back to Options
                </button>
              )}
            </div>
          </div>
        ) : mode === 'photo' && !confirmationData ? (
          <div className="photo-mode">
            <input
              type="file"
              ref={fileInputRef}
              accept="image/*"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />

            {isProcessing && <p>Processing image...</p>}

            {imagePreview && (
              <div className="image-preview">
                <img src={imagePreview} alt="Preview" />
              </div>
            )}

            {error && <div className="error-message">{error}</div>}

            <div className="modal-actions">
              <button className="back-button" onClick={() => {
                setMode(null);
                setImagePreview(null);
              }}>
                Back to Options
              </button>
            </div>
          </div>
        ) : (
          <form className="mileage-form" onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Vehicle *</label>
              <select
                value={currentData.vehicle_id}
                onChange={(e) => handleVehicleChange(e.target.value)}
                required
              >
                <option value="">Select a vehicle</option>
                {vehicles.map(vehicle => (
                  <option key={vehicle.id} value={vehicle.id}>
                    {vehicle.name}
                    {vehicle.last_odometer_reading ? ` (Last: ${vehicle.last_odometer_reading.toLocaleString()} mi)` : ''}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Date *</label>
              <input
                type="date"
                value={currentData.date}
                onChange={(e) => handleFormChange('date', e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Purpose *</label>
              <textarea
                value={currentData.purpose}
                onChange={(e) => handleFormChange('purpose', e.target.value)}
                placeholder="e.g., Material pickup at Lowes for roofing job"
                required
                rows="3"
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Odometer Start *</label>
                <input
                  type="number"
                  value={currentData.odometer_start}
                  onChange={(e) => handleFormChange('odometer_start', e.target.value)}
                  placeholder="15500"
                  required
                  min="0"
                />
              </div>

              <div className="form-group">
                <label>Odometer End *</label>
                <input
                  type="number"
                  value={currentData.odometer_end}
                  onChange={(e) => handleFormChange('odometer_end', e.target.value)}
                  placeholder="15600"
                  required
                  min="0"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Personal Miles</label>
              <input
                type="number"
                value={currentData.personal_miles}
                onChange={(e) => handleFormChange('personal_miles', e.target.value)}
                placeholder="0"
                min="0"
              />
              <small>Leave as 0 if all miles were for business</small>
            </div>

            <div className="form-group">
              <label>Tags</label>
              <TagInput
                tags={currentData.tags || []}
                onChange={(tags) => handleFormChange('tags', tags)}
                availableTags={availableTags}
              />
            </div>

            <div className="calculation-summary">
              <div className="calc-item">
                <span>Business Miles:</span>
                <strong>{businessMiles} mi</strong>
              </div>
              <div className="calc-item">
                <span>IRS Rate:</span>
                <strong>${currentIRSRate}/mi</strong>
              </div>
              <div className="calc-item highlight">
                <span>Deduction:</span>
                <strong>${deduction.toFixed(2)}</strong>
              </div>
            </div>

            {error && <div className="error-message">{error}</div>}

            <div className="modal-actions">
              <button type="button" className="back-button" onClick={() => {
                if (confirmationData) {
                  setConfirmationData(null);
                  setMode(null);
                } else {
                  setMode(null);
                }
              }}>
                Back
              </button>
              <button
                type="submit"
                className="submit-button"
                disabled={isProcessing}
              >
                {isProcessing ? 'Creating...' : 'Create Mileage Log'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default AddMileageModal;
