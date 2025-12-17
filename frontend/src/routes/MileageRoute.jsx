import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import MileageLogList from '../components/mileage/MileageLogList';
import AddMileageModal from '../components/mileage/AddMileageModal';
import { MdAdd } from 'react-icons/md';

function MileageRoute({ apiUrl }) {
  const [searchParams] = useSearchParams();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const vehicleId = searchParams.get('vehicle_id') || null;
  const dateFrom = searchParams.get('date_from') || null;
  const dateTo = searchParams.get('date_to') || null;

  const handleMileageAdded = () => {
    setIsModalOpen(false);
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <>
      <MileageLogList
        apiUrl={apiUrl}
        initialVehicleId={vehicleId}
        initialDateFrom={dateFrom}
        initialDateTo={dateTo}
        refreshTrigger={refreshTrigger}
      />

      <button
        className="floating-mileage-button"
        onClick={() => setIsModalOpen(true)}
        title="Add Mileage"
      >
        <MdAdd size={24} />
      </button>

      <AddMileageModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onMileageAdded={handleMileageAdded}
        apiUrl={apiUrl}
      />

      <style>{`
        .floating-mileage-button {
          position: fixed;
          bottom: 24px;
          right: 24px;
          width: 60px;
          height: 60px;
          border-radius: 50%;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: transform 0.2s, box-shadow 0.2s;
          z-index: 100;
        }

        .floating-mileage-button:hover {
          transform: translateY(-4px);
          box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
        }

        @media (max-width: 768px) {
          .floating-mileage-button {
            bottom: 80px;
          }
        }
      `}</style>
    </>
  );
}

export default MileageRoute;
