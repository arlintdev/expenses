import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { MdDirectionsCar, MdEdit, MdDelete, MdAdd } from 'react-icons/md';
import './VehicleManager.css';

function VehicleManager({ apiUrl }) {
  const { getAuthHeader } = useAuth();
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInactive, setShowInactive] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [showAddForm, setShowAddForm] = useState(false);
  const [newVehicle, setNewVehicle] = useState({
    name: '',
    make: '',
    model: '',
    year: '',
    license_plate: ''
  });

  useEffect(() => {
    fetchVehicles();
  }, [showInactive]);

  const fetchVehicles = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/vehicles?active_only=${!showInactive}`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        setVehicles(data);
      }
    } catch (error) {
      console.error('Error fetching vehicles:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddVehicle = async (e) => {
    e.preventDefault();
    if (!newVehicle.name.trim()) return;

    try {
      const response = await fetch(`${apiUrl}/api/vehicles`, {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: newVehicle.name,
          make: newVehicle.make || null,
          model: newVehicle.model || null,
          year: newVehicle.year ? parseInt(newVehicle.year) : null,
          license_plate: newVehicle.license_plate || null
        })
      });

      if (response.ok) {
        setNewVehicle({ name: '', make: '', model: '', year: '', license_plate: '' });
        setShowAddForm(false);
        fetchVehicles();
      }
    } catch (error) {
      console.error('Error adding vehicle:', error);
    }
  };

  const handleStartEdit = (vehicle) => {
    setEditingId(vehicle.id);
    setEditForm({
      name: vehicle.name,
      make: vehicle.make || '',
      model: vehicle.model || '',
      year: vehicle.year || '',
      license_plate: vehicle.license_plate || ''
    });
  };

  const handleSaveEdit = async (vehicleId) => {
    try {
      const response = await fetch(`${apiUrl}/api/vehicles/${vehicleId}`, {
        method: 'PATCH',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: editForm.name,
          make: editForm.make || null,
          model: editForm.model || null,
          year: editForm.year ? parseInt(editForm.year) : null,
          license_plate: editForm.license_plate || null
        })
      });

      if (response.ok) {
        setEditingId(null);
        fetchVehicles();
      }
    } catch (error) {
      console.error('Error updating vehicle:', error);
    }
  };

  const handleDelete = async (vehicleId) => {
    if (!confirm('Are you sure you want to archive this vehicle?')) return;

    try {
      const response = await fetch(`${apiUrl}/api/vehicles/${vehicleId}`, {
        method: 'DELETE',
        headers: getAuthHeader()
      });

      if (response.ok) {
        fetchVehicles();
      }
    } catch (error) {
      console.error('Error deleting vehicle:', error);
    }
  };

  if (loading) {
    return <div className="loading">Loading vehicles...</div>;
  }

  return (
    <div className="vehicle-manager">
      <div className="vehicle-header">
        <h2>Vehicles</h2>
        <div className="header-actions">
          <label className="toggle-inactive">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
            />
            <span>Show archived</span>
          </label>
          <button
            className="add-vehicle-button"
            onClick={() => setShowAddForm(!showAddForm)}
          >
            <MdAdd size={20} />
            Add Vehicle
          </button>
        </div>
      </div>

      {showAddForm && (
        <form className="vehicle-form add-form" onSubmit={handleAddVehicle}>
          <h3>Add New Vehicle</h3>
          <div className="form-row">
            <input
              type="text"
              placeholder="Vehicle Name (required) *"
              value={newVehicle.name}
              onChange={(e) => setNewVehicle({ ...newVehicle, name: e.target.value })}
              required
            />
          </div>
          <div className="form-row">
            <input
              type="text"
              placeholder="Make"
              value={newVehicle.make}
              onChange={(e) => setNewVehicle({ ...newVehicle, make: e.target.value })}
            />
            <input
              type="text"
              placeholder="Model"
              value={newVehicle.model}
              onChange={(e) => setNewVehicle({ ...newVehicle, model: e.target.value })}
            />
          </div>
          <div className="form-row">
            <input
              type="number"
              placeholder="Year"
              value={newVehicle.year}
              onChange={(e) => setNewVehicle({ ...newVehicle, year: e.target.value })}
              min="1900"
              max="2100"
            />
            <input
              type="text"
              placeholder="License Plate"
              value={newVehicle.license_plate}
              onChange={(e) => setNewVehicle({ ...newVehicle, license_plate: e.target.value })}
            />
          </div>
          <div className="form-actions">
            <button type="submit" className="save-button">Add Vehicle</button>
            <button type="button" className="cancel-button" onClick={() => setShowAddForm(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="vehicles-grid">
        {vehicles.length === 0 ? (
          <div className="empty-state">
            <MdDirectionsCar size={64} />
            <p>No vehicles yet. Add your first vehicle to start tracking mileage.</p>
          </div>
        ) : (
          vehicles.map((vehicle) => (
            <div
              key={vehicle.id}
              className={`vehicle-card ${!vehicle.is_active ? 'inactive' : ''}`}
            >
              {editingId === vehicle.id ? (
                <div className="vehicle-edit-form">
                  <input
                    type="text"
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    placeholder="Name *"
                  />
                  <input
                    type="text"
                    value={editForm.make}
                    onChange={(e) => setEditForm({ ...editForm, make: e.target.value })}
                    placeholder="Make"
                  />
                  <input
                    type="text"
                    value={editForm.model}
                    onChange={(e) => setEditForm({ ...editForm, model: e.target.value })}
                    placeholder="Model"
                  />
                  <input
                    type="number"
                    value={editForm.year}
                    onChange={(e) => setEditForm({ ...editForm, year: e.target.value })}
                    placeholder="Year"
                    min="1900"
                    max="2100"
                  />
                  <input
                    type="text"
                    value={editForm.license_plate}
                    onChange={(e) => setEditForm({ ...editForm, license_plate: e.target.value })}
                    placeholder="License Plate"
                  />
                  <div className="edit-actions">
                    <button onClick={() => handleSaveEdit(vehicle.id)} className="save-button">
                      Save
                    </button>
                    <button onClick={() => setEditingId(null)} className="cancel-button">
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="vehicle-icon">
                    <MdDirectionsCar size={32} />
                  </div>
                  <div className="vehicle-info">
                    <h3 className="vehicle-name">{vehicle.name}</h3>
                    {(vehicle.make || vehicle.model) && (
                      <p className="vehicle-details">
                        {[vehicle.year, vehicle.make, vehicle.model].filter(Boolean).join(' ')}
                      </p>
                    )}
                    {vehicle.license_plate && (
                      <p className="vehicle-license">{vehicle.license_plate}</p>
                    )}
                    {vehicle.last_odometer_reading && (
                      <p className="vehicle-odometer">
                        Last odometer: {vehicle.last_odometer_reading.toLocaleString()} mi
                      </p>
                    )}
                    {!vehicle.is_active && (
                      <span className="archived-badge">Archived</span>
                    )}
                  </div>
                  <div className="vehicle-actions">
                    <button
                      className="icon-button"
                      onClick={() => handleStartEdit(vehicle)}
                      title="Edit vehicle"
                    >
                      <MdEdit size={18} />
                    </button>
                    <button
                      className="icon-button delete-button"
                      onClick={() => handleDelete(vehicle.id)}
                      title="Archive vehicle"
                    >
                      <MdDelete size={18} />
                    </button>
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default VehicleManager;
